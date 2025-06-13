#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
feeder.py – Concatenate readable source files and copy them to the clipboard
(Windows & macOS).

Features
========
1. Prints a directory tree (filtered by --ignore).
2. Skips unreadable / binary files automatically.
3. --ignore supports            • file names (e.g.  *.tmp)
                                • whole dirs (trailing “/”, e.g.  ./.git/)
                                • path patterns (e.g.  docs/**/*.bak)
"""

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, Iterable, List


# --------------------------------------------------------------------------- #
# Clipboard helpers
# --------------------------------------------------------------------------- #
def _copy_windows(text: str) -> None:
    """Copy *text* to the clipboard on Windows using PowerShell."""
    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "[Console]::InputEncoding=[Text.Encoding]::UTF8;"
                "Set-Clipboard -Value ([Console]::In.ReadToEnd())",
            ],
            input=text.encode(),
            check=True,
        )
        print("\n--- Copied to clipboard (Windows) ---")
    except Exception as exc:  # pragma: no cover
        print(f"\n--- Clipboard error (Windows): {exc} ---")


def _copy_macos(text: str) -> None:
    """Copy *text* to the clipboard on macOS using pbcopy."""
    try:
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
        print("\n--- Copied to clipboard (macOS) ---")
    except Exception as exc:  # pragma: no cover
        print(f"\n--- Clipboard error (macOS): {exc} ---")


def copy_to_clipboard(text: str) -> None:
    if sys.platform == "win32":
        _copy_windows(text)
    elif sys.platform == "darwin":
        _copy_macos(text)


# --------------------------------------------------------------------------- #
# Extension system
# --------------------------------------------------------------------------- #
Handler = Callable[[Path], str]
_HANDLER_REGISTRY: Dict[str, Handler] = {}


def register_handler(*suffixes: str) -> Callable[[Handler], Handler]:
    def decorator(func: Handler) -> Handler:
        for sfx in suffixes:
            _HANDLER_REGISTRY[sfx.lower()] = func
        return func

    return decorator


def get_handler(path: Path) -> Handler:
    return _HANDLER_REGISTRY.get(path.suffix.lower(), _default_handler)


def _default_handler(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").rstrip("\n")


@register_handler(".ipynb")
def _ipynb_handler(path: Path) -> str:
    with path.open(encoding="utf-8") as fh:
        nb = json.load(fh)
    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    if not code_cells:
        return "(no code cells)"
    chunks: List[str] = []
    for i, cell in enumerate(code_cells, 1):
        chunks.append(f"# ----- Code Cell [{i}] -----")
        src = cell.get("source", [])
        chunks.append("".join(src) if isinstance(src, list) else str(src))
    return "\n".join(chunks).rstrip("\n")


# --------------------------------------------------------------------------- #
# Ignore-handling & binary detection
# --------------------------------------------------------------------------- #
_BINARY_EXTS = {
    ".exe",
    ".dll",
    ".so",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".tgz",
    ".7z",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".wav",
}


def _strip_leading_dot_slash(pat: str) -> str:
    """Remove a single leading './' or '.\\' (nothing more)."""
    if pat.startswith("./"):
        return pat[2:]
    if pat.startswith(".\\"):
        return pat[2:]
    return pat


def should_ignore(path: Path, root: Path, patterns: List[str]) -> bool:
    """
    True if *path* matches any ignore pattern.

    Trailing '/'  →  directory pattern
    '/' in middle →  match against relative POSIX path
    no '/'        →  match against basename only
    """
    rel = path.relative_to(root).as_posix()
    name = path.name

    for raw in patterns:
        pat = _strip_leading_dot_slash(raw)

        # directory pattern
        if pat.endswith("/"):
            dir_pat = pat.rstrip("/")
            if rel == dir_pat or rel.startswith(dir_pat + "/"):
                return True
            continue

        # path pattern
        if "/" in pat:
            if fnmatch.fnmatch(rel, pat):
                return True
            continue

        # basename pattern
        if fnmatch.fnmatch(name, pat):
            return True

    return False


def is_binary(path: Path) -> bool:
    if path.suffix.lower() in _BINARY_EXTS:
        return True
    try:
        with path.open("rb") as fh:
            return b"\0" in fh.read(1024)
    except Exception:
        return True


# --------------------------------------------------------------------------- #
# Collect files & build output
# --------------------------------------------------------------------------- #
def collect_files(root: Path, ignore_patterns: List[str]) -> List[Path]:
    files: List[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        cur_dir = Path(dirpath)

        # prune ignored dirs
        dirnames[:] = [
            d for d in dirnames if not should_ignore(cur_dir / d, root, ignore_patterns)
        ]

        for fname in filenames:
            p = cur_dir / fname
            if should_ignore(p, root, ignore_patterns):
                continue
            if is_binary(p):
                continue
            files.append(p)

    files.sort(key=lambda p: p.as_posix())
    return files


def build_output(files: Iterable[Path], separator: str) -> str:
    parts: List[str] = []
    for i, p in enumerate(files):
        header = f"File: {p}"
        parts.extend([header, "-" * len(header)])
        try:
            parts.append(get_handler(p)(p))
        except Exception as exc:
            parts.append(f"(error reading file: {exc})")
        if i < len(files) - 1:
            parts.append(separator)
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Directory-tree printer (with ignore filtering)
# --------------------------------------------------------------------------- #
def print_dir_tree(root: Path, ignore_patterns: List[str]) -> None:
    def _walk(base: Path, prefix: str = "") -> None:
        entries = [
            e
            for e in sorted(base.iterdir(), key=lambda p: p.name.lower())
            if not should_ignore(e, root, ignore_patterns)
        ]
        for i, entry in enumerate(entries):
            connector = "└── " if i == len(entries) - 1 else "├── "
            print(prefix + connector + entry.name + ("/" if entry.is_dir() else ""))
            if entry.is_dir():
                _walk(
                    entry,
                    prefix + ("    " if i == len(entries) - 1 else "│   "),
                )

    print(str(root.resolve()) + "/")
    _walk(root)
    print()


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Concatenate readable source files and copy them to the "
        "clipboard.",
        epilog=(
            "Examples:\n"
            "  python feeder.py --root . --ignore ./.git/ *.tmp\n"
            "  python feeder.py --root project --ignore build/ docs/**/*.bak\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--root", required=True, type=Path, help="Root directory")
    parser.add_argument(
        "--ignore",
        nargs="*",
        default=[],
        metavar="PATTERN",
        help=(
            "Skip files/dirs.  Trailing '/' hides directory recursively.\n"
            "Patterns follow fnmatch/glob rules."
        ),
    )
    parser.add_argument("--no-clipboard", action="store_true", help="Skip clipboard")
    args = parser.parse_args()

    if not args.root.is_dir():
        sys.exit(f"Error: '{args.root}' is not a directory.")

    # 1. Pretty tree (respect --ignore)
    print_dir_tree(args.root, args.ignore)

    # 2. File contents
    files = collect_files(args.root, args.ignore)
    if not files:
        sys.exit("No readable files found (after applying ignore patterns).")

    output = build_output(files, "\n" + "=" * 80 + "\n")
    print(output + "\n")
    print(f"--- Processed {len(files)} readable file(s) ---")

    if not args.no_clipboard and sys.platform in ("win32", "darwin"):
        copy_to_clipboard(output)
    else:
        print(f"--- Clipboard step skipped (platform={sys.platform}) ---")


if __name__ == "__main__":
    main()
