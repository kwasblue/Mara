"""
MARA Monorepo Structure Scanner
Scans Python and C++ codebases and outputs structure to console and/or file
"""

import ast
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import argparse

try:
    import pathspec
    HAS_PATHSPEC = True
except ImportError:
    HAS_PATHSPEC = False
    print("pathspec not installed. Install with: pip install pathspec")


# ============================================================================
# GITIGNORE HANDLING
# ============================================================================

def load_gitignore(project_root: Path) -> Optional['pathspec.PathSpec']:
    """Load .gitignore patterns if pathspec is available"""
    if not HAS_PATHSPEC:
        return None

    gitignore_path = project_root / ".gitignore"
    if not gitignore_path.exists():
        return None

    try:
        with open(gitignore_path, "r", encoding="utf-8") as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    except Exception as e:
        print(f"Warning: Failed to load .gitignore: {e}")
        return None


# ============================================================================
# PYTHON AST PARSING
# ============================================================================

def attach_parents(tree: ast.AST) -> None:
    """Attach parent references to all AST nodes"""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            setattr(child, "parent", node)


def extract_python_defs(filepath: Path) -> List[Dict]:
    """Extract classes and functions from a Python file."""
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            content = file.read()

        tree = ast.parse(content, filename=str(filepath))
    except SyntaxError as e:
        return []
    except Exception as e:
        return []

    attach_parents(tree)

    results = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    args = [arg.arg for arg in item.args.args]
                    methods.append({
                        "name": item.name,
                        "args": args,
                        "lineno": item.lineno
                    })

            results.append({
                "type": "class",
                "name": node.name,
                "methods": methods,
                "lineno": node.lineno
            })

        elif isinstance(node, ast.FunctionDef):
            parent = getattr(node, "parent", None)
            if not isinstance(parent, ast.ClassDef):
                args = [arg.arg for arg in node.args.args]
                results.append({
                    "type": "function",
                    "name": node.name,
                    "args": args,
                    "lineno": node.lineno
                })

    results.sort(key=lambda x: x["lineno"])
    return results


# ============================================================================
# C++ PARSING (REGEX-BASED)
# ============================================================================

def extract_cpp_defs(filepath: Path) -> List[Dict]:
    """Extract classes, structs, and functions from a C++ file using regex."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
            content = file.read()
    except Exception as e:
        return []

    results = []

    # Pattern for class/struct definitions
    class_pattern = re.compile(
        r'^\s*(class|struct)\s+(\w+)(?:\s*:\s*(?:public|private|protected)?\s*\w+)?(?:\s*\{)?',
        re.MULTILINE
    )

    # Pattern for function definitions (simplified)
    func_pattern = re.compile(
        r'^\s*(?:virtual\s+)?(?:static\s+)?(?:inline\s+)?'
        r'(?:const\s+)?(?:\w+(?:<[^>]+>)?(?:::\w+)?[*&\s]+)'
        r'(\w+)\s*\(([^)]*)\)\s*(?:const)?(?:\s*override)?(?:\s*\{|\s*;)',
        re.MULTILINE
    )

    # Skip common patterns that aren't function definitions
    skip_names = {'if', 'while', 'for', 'switch', 'catch', 'return', 'sizeof', 'typeof'}

    # Find classes/structs
    for match in class_pattern.finditer(content):
        class_type = match.group(1)
        class_name = match.group(2)
        lineno = content[:match.start()].count('\n') + 1

        results.append({
            "type": class_type,
            "name": class_name,
            "methods": [],
            "lineno": lineno
        })

    # Find standalone functions
    for match in func_pattern.finditer(content):
        func_name = match.group(1)
        if func_name in skip_names:
            continue

        args_str = match.group(2).strip()
        lineno = content[:match.start()].count('\n') + 1

        # Check if this is inside a class (rough heuristic)
        preceding = content[:match.start()]
        open_braces = preceding.count('{') - preceding.count('}')

        if open_braces <= 1:
            results.append({
                "type": "function",
                "name": func_name,
                "args": [args_str] if args_str else [],
                "lineno": lineno
            })

    # Sort by line number and deduplicate
    seen = set()
    unique_results = []
    for item in sorted(results, key=lambda x: x["lineno"]):
        key = (item["type"], item["name"], item["lineno"])
        if key not in seen:
            seen.add(key)
            unique_results.append(item)

    return unique_results


# ============================================================================
# DIRECTORY SCANNING
# ============================================================================

PYTHON_EXTENSIONS = {'.py'}
CPP_EXTENSIONS = {'.cpp', '.cc', '.cxx', '.c', '.h', '.hpp', '.hxx'}
ALL_EXTENSIONS = PYTHON_EXTENSIONS | CPP_EXTENSIONS


def should_ignore_path(rel_path: str) -> bool:
    """Check if path should be ignored (common patterns)"""
    ignore_patterns = [
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        ".env",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        "build",
        "dist",
        ".egg-info",
        ".pio",
        ".ccls-cache",
    ]

    path_parts = Path(rel_path).parts
    for pattern in ignore_patterns:
        if pattern in path_parts:
            return True
        if any(part.startswith('.') and len(part) > 1 for part in path_parts[:-1]):
            return True
    return False


def get_file_type(filepath: Path) -> Optional[str]:
    """Determine file type based on extension"""
    ext = filepath.suffix.lower()
    if ext in PYTHON_EXTENSIONS:
        return "python"
    elif ext in CPP_EXTENSIONS:
        return "cpp"
    return None


def scan_directory(
    base_path: Path,
    respect_gitignore: bool = True,
    file_types: Optional[set] = None
) -> Tuple[Dict[str, List[Dict]], Dict[str, str]]:
    """
    Scan directory for source files and extract structure.

    Returns:
        Tuple of (structure dict, file_types dict)
    """
    base_path = Path(base_path).resolve()
    gitignore = load_gitignore(base_path) if respect_gitignore else None
    code_structure = {}
    file_type_map = {}

    if file_types is None:
        file_types = {"python", "cpp"}

    print(f"Scanning: {base_path}")

    file_count = 0
    skipped_count = 0

    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if not should_ignore_path(d)]

        for file in files:
            full_path = Path(root) / file
            rel_path = full_path.relative_to(base_path)

            ftype = get_file_type(full_path)
            if ftype is None or ftype not in file_types:
                continue

            if gitignore and gitignore.match_file(str(rel_path)):
                skipped_count += 1
                continue

            if should_ignore_path(str(rel_path)):
                skipped_count += 1
                continue

            try:
                if ftype == "python":
                    defs = extract_python_defs(full_path)
                elif ftype == "cpp":
                    defs = extract_cpp_defs(full_path)
                else:
                    defs = []

                if defs:
                    code_structure[str(rel_path)] = defs
                    file_type_map[str(rel_path)] = ftype
                    file_count += 1
            except Exception as e:
                pass

    print(f"Scanned {file_count} files ({skipped_count} skipped)")
    return code_structure, file_type_map


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

def format_args(args: List[str], is_python: bool = True) -> str:
    """Format function arguments"""
    if not args:
        return "()"
    if is_python and args[0] == "self":
        args = args[1:]
        if not args:
            return "(self)"
        return f"(self, {', '.join(args)})"
    return f"({', '.join(args)})"


def get_icon(item_type: str, file_type: str = "python") -> str:
    """Get appropriate icon for item type"""
    icons = {
        "class": "Class",
        "struct": "Struct",
        "function": "Fn",
        "namespace": "NS",
    }
    return icons.get(item_type, "-")


def print_structure(
    structure: Dict[str, List[Dict]],
    file_type_map: Dict[str, str],
    output_file: Optional[Path] = None,
    show_line_numbers: bool = False,
    group_by_component: bool = True
) -> None:
    """Print structure to console and/or file."""
    lines = []

    lines.append("=" * 80)
    lines.append("MARA MONOREPO STRUCTURE")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total Files: {len(structure)}")
    lines.append("=" * 80)
    lines.append("")

    if group_by_component:
        components = {
            "host/": [],
            "firmware/mcu/": [],
            "firmware/cam/": [],
            "tools/": [],
            "protocol/": [],
            "(root)": [],
        }

        for file_path in sorted(structure.keys()):
            placed = False
            for component in ["host/", "firmware/mcu/", "firmware/cam/", "tools/", "protocol/"]:
                if file_path.startswith(component):
                    components[component].append(file_path)
                    placed = True
                    break
            if not placed:
                components["(root)"].append(file_path)

        component_names = {
            "host/": "HOST (Python)",
            "firmware/mcu/": "FIRMWARE/MCU (C++)",
            "firmware/cam/": "FIRMWARE/CAM (C++)",
            "tools/": "TOOLS",
            "protocol/": "PROTOCOL",
            "(root)": "ROOT",
        }

        for component, files in components.items():
            if not files:
                continue

            lines.append("")
            lines.append("-" * 80)
            lines.append(component_names.get(component, component))
            lines.append("-" * 80)

            for file_path in sorted(files):
                defs = structure[file_path]
                ftype = file_type_map.get(file_path, "python")
                is_python = ftype == "python"

                lines.append(f"  {file_path}")

                for item in defs:
                    lineno = f":{item['lineno']}" if show_line_numbers else ""
                    icon = get_icon(item["type"], ftype)

                    if item["type"] in ("class", "struct"):
                        lines.append(f"    [{icon}] {item['name']}{lineno}")

                        if item.get("methods"):
                            for i, method in enumerate(item["methods"]):
                                is_last = (i == len(item["methods"]) - 1)
                                prefix = "`--" if is_last else "|--"
                                args_str = format_args(method.get("args", []), is_python)
                                method_lineno = f":{method['lineno']}" if show_line_numbers else ""
                                lines.append(f"      {prefix} {method['name']}{args_str}{method_lineno}")

                    elif item["type"] == "function":
                        args_str = format_args(item.get("args", []), is_python)
                        lines.append(f"    [{icon}] {item['name']}{args_str}{lineno}")

                lines.append("")
    else:
        for file_path, defs in sorted(structure.items()):
            ftype = file_type_map.get(file_path, "python")
            is_python = ftype == "python"

            lines.append(f"  {file_path}")

            for item in defs:
                lineno = f":{item['lineno']}" if show_line_numbers else ""
                icon = get_icon(item["type"], ftype)

                if item["type"] in ("class", "struct"):
                    lines.append(f"    [{icon}] {item['name']}{lineno}")
                elif item["type"] == "function":
                    args_str = format_args(item.get("args", []), is_python)
                    lines.append(f"    [{icon}] {item['name']}{args_str}{lineno}")

            lines.append("")

    # Statistics
    py_files = sum(1 for f in file_type_map.values() if f == "python")
    cpp_files = sum(1 for f in file_type_map.values() if f == "cpp")
    total_classes = sum(1 for defs in structure.values() for d in defs if d["type"] == "class")
    total_structs = sum(1 for defs in structure.values() for d in defs if d["type"] == "struct")
    total_functions = sum(1 for defs in structure.values() for d in defs if d["type"] == "function")
    total_methods = sum(
        len(d.get("methods", []))
        for defs in structure.values()
        for d in defs
        if d["type"] in ("class", "struct")
    )

    lines.append("")
    lines.append("=" * 80)
    lines.append("STATISTICS")
    lines.append("=" * 80)
    lines.append(f"Python Files:     {py_files}")
    lines.append(f"C++ Files:        {cpp_files}")
    lines.append(f"Total Classes:    {total_classes}")
    lines.append(f"Total Structs:    {total_structs}")
    lines.append(f"Total Functions:  {total_functions}")
    lines.append(f"Total Methods:    {total_methods}")
    lines.append("=" * 80)

    output = "\n".join(lines)
    print(output)

    if output_file:
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"\nOutput saved to: {output_file}")
        except Exception as e:
            print(f"\nFailed to write to {output_file}: {e}")


def generate_tree_view(structure: Dict[str, List[Dict]], file_type_map: Dict[str, str]) -> str:
    """Generate a simple tree view of files"""
    lines = ["MARA Monorepo Tree", ""]

    files_by_dir = {}
    for file_path in sorted(structure.keys()):
        dir_path = str(Path(file_path).parent)
        if dir_path == ".":
            dir_path = "(root)"
        files_by_dir.setdefault(dir_path, []).append(Path(file_path).name)

    for dir_path, files in sorted(files_by_dir.items()):
        lines.append(f"  {dir_path}/")
        for file in sorted(files):
            ext = Path(file).suffix
            marker = "[py]" if ext == ".py" else "[cpp]" if ext in (".cpp", ".cc", ".c") else "[h]" if ext in (".h", ".hpp") else ""
            lines.append(f"    {marker} {file}")
        lines.append("")

    return "\n".join(lines)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point with CLI argument parsing"""
    parser = argparse.ArgumentParser(
        description="Scan MARA monorepo and extract structure (Python + C++)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan entire monorepo
  python structure.py

  # Scan specific component
  python structure.py host/
  python structure.py firmware/mcu/

  # Save to file
  python structure.py --output mara_structure.txt

  # Python only
  python structure.py --python-only

  # C++ only
  python structure.py --cpp-only

  # Show line numbers
  python structure.py --line-numbers

  # Generate tree view
  python structure.py --tree
        """
    )

    parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="Project directory to scan (default: current directory)"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path (e.g., structure.txt)"
    )
    parser.add_argument(
        "-l", "--line-numbers",
        action="store_true",
        help="Show line numbers for definitions"
    )
    parser.add_argument(
        "-t", "--tree",
        action="store_true",
        help="Generate simple tree view"
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Don't respect .gitignore patterns"
    )
    parser.add_argument(
        "--python-only",
        action="store_true",
        help="Only scan Python files"
    )
    parser.add_argument(
        "--cpp-only",
        action="store_true",
        help="Only scan C++ files"
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Don't group by component (flat alphabetical list)"
    )

    args = parser.parse_args()

    file_types = set()
    if args.python_only:
        file_types = {"python"}
    elif args.cpp_only:
        file_types = {"cpp"}
    else:
        file_types = {"python", "cpp"}

    project_path = Path(args.project_dir).resolve()

    if not project_path.exists():
        print(f"Error: Directory does not exist: {project_path}")
        return 1

    structure, file_type_map = scan_directory(
        project_path,
        respect_gitignore=not args.no_gitignore,
        file_types=file_types
    )

    if not structure:
        print("No source files with definitions found.")
        return 0

    if args.tree:
        tree_output = generate_tree_view(structure, file_type_map)
        print("\n" + tree_output)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(tree_output)
            print(f"\nOutput saved to: {args.output}")
    else:
        print_structure(
            structure,
            file_type_map,
            output_file=args.output,
            show_line_numbers=args.line_numbers,
            group_by_component=not args.flat
        )

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
