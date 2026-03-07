"""
C++ Project Structure Scanner (no dependencies)
- Scans .cpp/.cc/.cxx/.h/.hpp/.hh
- Extracts namespaces, classes/structs, enums, and function definitions (best effort)
"""

from __future__ import annotations

import os
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    import pathspec  # type: ignore
    HAS_PATHSPEC = True
except ImportError:
    HAS_PATHSPEC = False


# ----------------------------
# gitignore handling (optional)
# ----------------------------

def load_gitignore(project_root: Path):
    if not HAS_PATHSPEC:
        return None
    p = project_root / ".gitignore"
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    except Exception:
        return None


# ----------------------------
# ignore rules
# ----------------------------

IGNORE_DIRS = {
    ".git", ".idea", ".vscode",
    "build", "dist", "out", "cmake-build-debug", "cmake-build-release",
    "Debug", "Release",
    "bazel-bin", "bazel-out", "bazel-testlogs",
    "node_modules",
    "__pycache__",
}

CPP_EXTS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".ipp"}


def should_ignore_path(rel_path: str) -> bool:
    p = Path(rel_path)
    # ignore hidden dirs
    for part in p.parts[:-1]:
        if part.startswith("."):
            return True
        if part in IGNORE_DIRS:
            return True
    if any(part in IGNORE_DIRS for part in p.parts):
        return True
    return False


# ----------------------------
# lightweight "parser"
# ----------------------------

def safe_read_text(fp: Path, max_bytes: int = 2_000_000) -> Optional[str]:
    try:
        if fp.stat().st_size > max_bytes:
            return None
        return fp.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


# Very simple comment stripper to reduce false positives
_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)
_COMMENT_LINE = re.compile(r"//.*?$", re.MULTILINE)
_STRING_LIT = re.compile(r'"(?:\\.|[^"\\])*"')  # keep strings but blank them

def strip_comments(code: str) -> str:
    code = _COMMENT_BLOCK.sub("", code)
    code = _COMMENT_LINE.sub("", code)
    # replace string contents to avoid braces/keywords inside strings
    code = _STRING_LIT.sub('""', code)
    return code


# Patterns (heuristic)
RE_NAMESPACE = re.compile(r"^\s*namespace\s+([A-Za-z_]\w*)\s*\{", re.MULTILINE)

RE_CLASS = re.compile(
    r"^\s*(template\s*<[^;{]+>\s*)?"
    r"(class|struct)\s+([A-Za-z_]\w*)"
    r"(\s*:\s*[^ {]+(\s*,\s*[^ {]+)*)?\s*\{",
    re.MULTILINE
)

RE_ENUM = re.compile(r"^\s*enum(\s+class)?\s+([A-Za-z_]\w*)\s*\{", re.MULTILINE)

# Free function definition (not a declaration): ... name(args) {  OR  ... name(args) noexcept {  OR  ... name(args) -> T {
# Excludes control keywords.
CONTROL = {"if", "for", "while", "switch", "catch"}

# ✅ FIX (recommended): simpler args capture prevents None + fewer weird matches
RE_FREE_FUNC = re.compile(
    r"""
    ^\s*
    (?:template\s*<[^;{]+>\s*)?
    (?:[\w:\<\>\*\&\s]+?)            # return type (best effort)
    \s+
    (?P<name>[A-Za-z_]\w*(?:::\w+)*) # name or qualified name
    \s*
    \(
        (?P<args>[^\)]*)             # args (single-line, robust)
    \)
    \s*
    (?:const\s*)?
    (?:noexcept\s*)?
    (?:->\s*[\w:\<\>\*\&\s]+\s*)?
    \{
    """,
    re.MULTILINE | re.VERBOSE
)

# Method defined inside a class body: name(args) { ... }  (return type may be omitted for ctors)
# ✅ FIX (recommended): simpler args capture prevents None
RE_INCLASS_METHOD = re.compile(
    r"""
    ^\s*
    (?:virtual\s+|static\s+|inline\s+|constexpr\s+|friend\s+|explicit\s+|typename\s+|consteval\s+|constinit\s+|mutable\s+|)\s*
    (?:[\w:\<\>\*\&\s]+?\s+)?         # optional return type (ctors won't have)
    (?P<name>[~A-Za-z_]\w*)           # method name or dtor
    \s*
    \(
        (?P<args>[^\)]*)              # args (single-line, robust)
    \)
    \s*
    (?:const\s*)?
    (?:noexcept\s*)?
    (?:->\s*[\w:\<\>\*\&\s]+\s*)?
    \{
    """,
    re.MULTILINE | re.VERBOSE
)


def _line_of_index(code: str, idx: int) -> int:
    # 1-based
    return code.count("\n", 0, idx) + 1


def extract_defs_cpp(fp: Path) -> List[Dict[str, Any]]:
    raw = safe_read_text(fp)
    if raw is None:
        return []

    code = strip_comments(raw)

    results: List[Dict[str, Any]] = []

    # namespaces
    for m in RE_NAMESPACE.finditer(code):
        results.append({"type": "namespace", "name": m.group(1), "lineno": _line_of_index(code, m.start())})

    # enums
    for m in RE_ENUM.finditer(code):
        results.append({"type": "enum", "name": m.group(2), "lineno": _line_of_index(code, m.start())})

    # classes (plus in-class methods)
    for m in RE_CLASS.finditer(code):
        kind = m.group(2)
        name = m.group(3)
        start = m.start()
        start_line = _line_of_index(code, start)

        # Find the class body region by naive brace matching from the '{' we matched.
        brace_pos = code.find("{", m.end() - 1)
        if brace_pos == -1:
            continue

        depth = 0
        end_pos = None
        for i in range(brace_pos, len(code)):
            c = code[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end_pos = i
                    break

        body = code[brace_pos:end_pos] if end_pos else ""
        methods: List[Dict[str, Any]] = []

        # in-class method definitions
        for mm in RE_INCLASS_METHOD.finditer(body):
            meth_name = mm.group("name")
            if meth_name in CONTROL:
                continue

            # ✅ FIX: args group can be None; always default to ""
            args_raw = mm.group("args") or ""

            methods.append({
                "name": meth_name,
                "signature": f"({args_raw.strip()})",   # ✅ FIXED LINE
                "lineno": _line_of_index(code, brace_pos + mm.start())
            })

        results.append({
            "type": kind,  # "class" or "struct"
            "name": name,
            "lineno": start_line,
            "methods": sorted(methods, key=lambda x: x["lineno"])
        })

    # free function definitions
    for m in RE_FREE_FUNC.finditer(code):
        name = m.group("name")
        base = name.split("::")[-1]
        if base in CONTROL:
            continue

        args_raw = m.group("args") or ""
        results.append({
            "type": "function",
            "name": name,
            "lineno": _line_of_index(code, m.start()),
            "signature": f"({args_raw.strip()})"
        })

    results.sort(key=lambda x: x["lineno"])
    return results


# ----------------------------
# scanning + printing
# ----------------------------

def scan_directory(base_path: Path, respect_gitignore: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    base_path = base_path.resolve()
    gitignore = load_gitignore(base_path) if respect_gitignore else None

    structure: Dict[str, List[Dict[str, Any]]] = {}
    file_count = 0
    skipped = 0

    print(f"🔍 Scanning C++ project: {base_path}")

    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]

        for f in files:
            fp = Path(root) / f
            rel = fp.relative_to(base_path)

            if should_ignore_path(str(rel)):
                skipped += 1
                continue

            if gitignore and gitignore.match_file(str(rel)):
                skipped += 1
                continue

            if fp.suffix.lower() not in CPP_EXTS:
                continue

            defs = extract_defs_cpp(fp)
            if defs:
                structure[str(rel)] = defs
                file_count += 1

    print(f"✅ Scanned {file_count} files ({skipped} skipped)")
    return structure


def print_structure(structure: Dict[str, List[Dict[str, Any]]],
                   output_file: Optional[Path] = None,
                   show_line_numbers: bool = False) -> None:
    lines: List[str] = []
    lines.append("=" * 80)
    lines.append("📂 C++ PROJECT STRUCTURE")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total Files: {len(structure)}")
    lines.append("=" * 80)
    lines.append("")

    for file_path in sorted(structure.keys()):
        lines.append(f"🧩 📄 {file_path}")

        for item in structure[file_path]:
            lineno = f":{item['lineno']}" if show_line_numbers else ""

            if item["type"] in ("class", "struct"):
                lines.append(f"   🧱 {item['type']} {item['name']}{lineno}")
                methods = item.get("methods") or []
                if methods:
                    for i, m in enumerate(methods):
                        prefix = "└──" if i == len(methods) - 1 else "├──"
                        m_lineno = f":{m['lineno']}" if show_line_numbers else ""
                        sig = m.get("signature", "()")
                        lines.append(f"      {prefix} {m['name']}{sig}{m_lineno}")
                else:
                    lines.append("      (no in-class method bodies detected)")
            elif item["type"] == "enum":
                lines.append(f"   🧾 enum {item['name']}{lineno}")
            elif item["type"] == "namespace":
                lines.append(f"   📦 namespace {item['name']}{lineno}")
            else:
                sig = item.get("signature", "()")
                lines.append(f"   ⚙️  {item['name']}{sig}{lineno}")

        lines.append("")

    # stats
    total_classes = sum(1 for defs in structure.values() for d in defs if d["type"] in ("class", "struct"))
    total_funcs = sum(1 for defs in structure.values() for d in defs if d["type"] == "function")
    total_enums = sum(1 for defs in structure.values() for d in defs if d["type"] == "enum")
    total_namespaces = sum(1 for defs in structure.values() for d in defs if d["type"] == "namespace")
    total_methods = sum(len(d.get("methods") or []) for defs in structure.values() for d in defs if d["type"] in ("class", "struct"))

    lines.append("=" * 80)
    lines.append("📊 STATISTICS")
    lines.append("=" * 80)
    lines.append(f"Namespaces:       {total_namespaces}")
    lines.append(f"Classes/Structs:  {total_classes}")
    lines.append(f"Enums:            {total_enums}")
    lines.append(f"Free Functions:   {total_funcs}")
    lines.append(f"In-class Methods: {total_methods}")
    lines.append("=" * 80)

    output = "\n".join(lines)
    print(output)

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(output, encoding="utf-8")
        print(f"\n✅ Output saved to: {output_file}")


def generate_tree_view(structure: Dict[str, List[Dict[str, Any]]]) -> str:
    lines = ["📂 Project Tree (files with detected defs)", ""]
    by_dir: Dict[str, List[str]] = {}
    for fp in sorted(structure.keys()):
        d = str(Path(fp).parent)
        if d == ".":
            d = "(root)"
        by_dir.setdefault(d, []).append(Path(fp).name)

    for d, files in sorted(by_dir.items()):
        lines.append(f"  📁 {d}")
        for f in sorted(files):
            lines.append(f"     └── 🧩 {f}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan a C++ project and extract structure (regex-based)")
    parser.add_argument("project_dir", nargs="?", default=".", help="Project directory to scan")
    parser.add_argument("-o", "--output", type=Path, help="Output file path")
    parser.add_argument("-l", "--line-numbers", action="store_true", help="Show line numbers")
    parser.add_argument("-t", "--tree", action="store_true", help="Generate simple tree view")
    parser.add_argument("--no-gitignore", action="store_true", help="Don't respect .gitignore patterns")

    args = parser.parse_args()
    project_path = Path(args.project_dir).resolve()

    if not project_path.exists():
        print(f"❌ Error: Directory does not exist: {project_path}")
        return 1

    structure = scan_directory(project_path, respect_gitignore=not args.no_gitignore)

    if not structure:
        print("⚠️  No C/C++ files with detected definitions found.")
        return 0

    if args.tree:
        tree = generate_tree_view(structure)
        print("\n" + tree)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(tree, encoding="utf-8")
    else:
        print_structure(structure, output_file=args.output, show_line_numbers=args.line_numbers)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
