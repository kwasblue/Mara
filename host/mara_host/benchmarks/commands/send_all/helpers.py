# mara_host/benchmarks/commands/send_all/helpers.py
"""Helper functions for send_all benchmark."""
from __future__ import annotations

import ast
import importlib
import inspect
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .types import Payload, PayloadSpec, PayloadMap
from .commands import (
    DISRUPTIVE_COMMANDS,
    MOTION_COMMANDS,
    NO_PAYLOAD_OK,
    REQUIRES_PAYLOAD,
)


def parse_hostport(s: str) -> Tuple[str, int]:
    """Parse HOST:PORT string."""
    if ":" not in s:
        raise ValueError("Expected HOST:PORT")
    host, port_s = s.rsplit(":", 1)
    return host, int(port_s)


def load_payloads(path: Optional[str]) -> PayloadMap:
    """Load payloads from JSON file."""
    if not path:
        return {}
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("payloads file must be a JSON object mapping CMD_* -> payload")
    out: PayloadMap = {}
    for k, v in data.items():
        if isinstance(v, dict):
            out[k] = v
        elif isinstance(v, list) and all(isinstance(x, dict) for x in v):
            out[k] = v
    return out


def ensure_artifacts_dir() -> Path:
    """Ensure the artifacts directory exists."""
    out_dir = Path("logs/artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _import_class(dotted: str):
    """Import a class from a dotted path."""
    if ":" in dotted:
        mod_path, cls_name = dotted.split(":", 1)
    else:
        mod_path, cls_name = dotted.rsplit(".", 1)
    mod = importlib.import_module(mod_path)
    obj = getattr(mod, cls_name)
    if not inspect.isclass(obj):
        raise TypeError(f"{dotted} did not resolve to a class")
    return obj


def _module_name_from_file(pkg_root: Path, py_file: Path, pkg_name: str) -> str:
    """Get module name from file path."""
    rel = py_file.relative_to(pkg_root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join([pkg_name, *parts])


def _discover_transport_via_ast(
    pkg_name: str,
    token_sets: List[Tuple[str, ...]],
    exclude_dirs: Optional[set[str]] = None,
) -> Tuple[str, type]:
    """Discover transport class by scanning source files."""
    import mara_host
    pkg_root = Path(mara_host.__file__).resolve().parent

    if exclude_dirs is None:
        exclude_dirs = {"runners", "tests", "ui", "gui", "scripts", "__pycache__", "modules"}

    candidates: List[Tuple[int, int, str, str, Path]] = []
    for py_file in pkg_root.rglob("*.py"):
        if any(part in exclude_dirs for part in py_file.parts):
            continue
        try:
            src = py_file.read_text(encoding="utf-8")
            tree = ast.parse(src, filename=str(py_file))
        except Exception:
            continue

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            clsname = node.name
            for tokens in token_sets:
                if all(t in clsname for t in tokens):
                    modname = _module_name_from_file(pkg_root, py_file, pkg_name)
                    async_pref = 0 if "Async" in clsname else 1
                    candidates.append((async_pref, len(tokens), modname, clsname, py_file))
                    break

    if not candidates:
        wanted = " OR ".join(["+".join(ts) for ts in token_sets])
        raise RuntimeError(
            f"Could not discover a transport class via AST scan (wanted {wanted}).\n"
            f"Fix: pass --transport with the exact class path (module:Class)."
        )

    candidates.sort(key=lambda t: (t[0], -t[1], len(t[3]), t[3]))
    _, _, modname, clsname, _py = candidates[0]

    mod = importlib.import_module(modname)
    TransportCls = getattr(mod, clsname)
    if not inspect.isclass(TransportCls):
        raise RuntimeError(f"Discovered {modname}.{clsname} but it is not a class")
    return f"{modname}:{clsname}", TransportCls


def _resolve_transport_class(explicit: Optional[str], mode: str) -> Tuple[str, type]:
    """Resolve transport class from explicit path or by discovery."""
    if explicit:
        cls = _import_class(explicit)
        return explicit, cls
    if mode == "serial":
        token_sets = [("Async", "Serial", "Transport"), ("Serial", "Transport")]
        return _discover_transport_via_ast("mara_host", token_sets=token_sets)
    if mode == "tcp":
        token_sets = [("Async", "Tcp", "Transport"), ("Tcp", "Transport"), ("Async", "TCP", "Transport"), ("TCP", "Transport")]
        return _discover_transport_via_ast("mara_host", token_sets=token_sets)
    raise ValueError(f"Unknown mode: {mode}")


def _construct_transport(
    TransportCls,
    *,
    serial: Optional[str],
    baud: int,
    io_timeout: float,
    tcp: Optional[str],
) -> Any:
    """Construct transport instance with appropriate parameters."""
    sig = inspect.signature(TransportCls.__init__)
    params = sig.parameters
    kw: Dict[str, Any] = {}

    if tcp:
        host, port = parse_hostport(tcp)
        for k in ("host", "hostname", "ip", "addr", "address"):
            if k in params:
                kw[k] = host
                break
        for k in ("port", "tcp_port"):
            if k in params:
                kw[k] = port
                break
        for k in ("timeout", "io_timeout", "read_timeout", "write_timeout"):
            if k in params:
                kw[k] = io_timeout
                break
        try:
            return TransportCls(**kw)
        except TypeError:
            try:
                return TransportCls(host, port)
            except TypeError:
                return TransportCls(tcp)

    if not serial:
        raise RuntimeError("serial transport requested but no serial port provided")

    for k in ("port", "device", "path", "serial", "serial_path", "dev"):
        if k in params:
            kw[k] = serial
            break
    for k in ("baud", "baudrate"):
        if k in params:
            kw[k] = baud
            break
    for k in ("timeout", "io_timeout", "read_timeout", "write_timeout"):
        if k in params:
            kw[k] = io_timeout
            break

    try:
        return TransportCls(**kw)
    except TypeError:
        try:
            return TransportCls(serial, baud)
        except TypeError:
            return TransportCls(serial)


def _send_reliable_supports_timeout(client: Any) -> Tuple[bool, Optional[str]]:
    """Check if client's send_reliable supports timeout parameter."""
    fn = getattr(client, "send_reliable", None)
    if not callable(fn):
        return False, None
    try:
        sig = inspect.signature(fn)
    except Exception:
        return False, None
    params = sig.parameters
    for name in ("timeout_s", "timeout", "command_timeout_s", "cmd_timeout_s"):
        if name in params:
            return True, name
    return False, None


def ack_is_ok(ack: Any) -> Tuple[bool, Optional[str]]:
    """Check if an ack response indicates success."""
    if ack is None:
        return False, "no ack"
    if isinstance(ack, dict):
        if ack.get("ok") is True:
            return True, None
        return False, ack.get("error") or "command failed"
    return True, None


def should_skip_cmd(
    cmd: str,
    *,
    payload_spec: PayloadSpec,
    only_set: Optional[set[str]],
    unsafe_motion: bool,
) -> Optional[str]:
    """Determine if a command should be skipped."""
    if only_set is not None and cmd in only_set:
        return None

    if cmd in DISRUPTIVE_COMMANDS:
        return "skipped (disruptive command; use --only to force)"

    if (not unsafe_motion) and (cmd in MOTION_COMMANDS):
        return "skipped (motion command; use --unsafe-motion or --only)"

    if cmd in NO_PAYLOAD_OK:
        return None

    has_payload = bool(payload_spec) if not isinstance(payload_spec, list) else (len(payload_spec) > 0)
    if cmd in REQUIRES_PAYLOAD and not has_payload:
        return "skipped (missing required payload/config)"

    return None


def payload_items(spec: PayloadSpec) -> List[Payload]:
    """Extract payload items from a PayloadSpec."""
    if isinstance(spec, list):
        return [p for p in spec if isinstance(p, dict)]
    if isinstance(spec, dict):
        return [spec]
    return []
