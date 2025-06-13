#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
feeder.py – Collect source files (optionally pre-processed by extension
handlers), print them, and copy the result to the clipboard
(Windows & macOS).

Example
=======
    python feeder.py --root ./shader --include *.comp *.glsl
"""

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List


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
            input=text.encode("utf-8"),
            check=True,
        )
        print("\n--- Copied to clipboard (Windows) ---")
    except FileNotFoundError:
        print("\n--- Error: powershell.exe not found ---")
    except subprocess.CalledProcessError as exc:
        print(f"\n--- PowerShell exited with code {exc.returncode} ---")
    except Exception as exc:  # pragma: no cover
        print(f"\n--- Unexpected clipboard error (Windows): {exc} ---")


def _copy_macos(text: str) -> None:
    """Copy *text* to the clipboard on macOS using pbcopy."""
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        print("\n--- Copied to clipboard (macOS) ---")
    except FileNotFoundError:
        print("\n--- Error: pbcopy not found ---")
    except subprocess.CalledProcessError as exc:
        print(f"\n--- pbcopy exited with code {exc.returncode} ---")
    except Exception as exc:  # pragma: no cover
        print(f"\n--- Unexpected clipboard error (macOS): {exc} ---")


def copy_to_clipboard(text: str) -> None:
    """Dispatch to the platform-specific clipboard implementation."""
    if sys.platform == "win32":
        _copy_windows(text)
    elif sys.platform == "darwin":
        _copy_macos(text)
    else:
        print(f"--- Clipboard not supported on platform={sys.platform} ---")


# --------------------------------------------------------------------------- #
# Extension system
# --------------------------------------------------------------------------- #
Handler = Callable[[Path], str]
_HANDLER_REGISTRY: Dict[str, Handler] = {}


def register_handler(*suffixes: str) -> Callable[[Handler], Handler]:
    """Decorator that registers *suffixes* for the decorated handler."""

    def decorator(func: Handler) -> Handler:
        for sfx in suffixes:
            _HANDLER_REGISTRY[sfx.lower()] = func
        return func

    return decorator


def get_handler(path: Path) -> Handler:
    """Return a handler for *path* or the default handler."""
    return _HANDLER_REGISTRY.get(path.suffix.lower(), _default_handler)


def _default_handler(path: Path) -> str:
    """Read a UTF-8 (with BOM allowed) text file as-is."""
    return path.read_text(encoding="utf-8-sig").rstrip("\n")


@register_handler(".ipynb")
def _ipynb_handler(path: Path) -> str:
    """Return concatenated *code cells* from a Jupyter notebook."""
    with path.open(encoding="utf-8") as fh:
        nb = json.load(fh)

    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    if not code_cells:
        return "(no code cells)"

    chunks: List[str] = []
    for idx, cell in enumerate(code_cells, start=1):
        chunks.append(f"# ----- Code Cell [{idx}] -----")
        src = cell.get("source", [])
        chunks.append("".join(src) if isinstance(src, list) else str(src))

    return "\n".join(chunks).rstrip("\n")


# --------------------------------------------------------------------------- #
# Core logic
# --------------------------------------------------------------------------- #
def collect_files(root: Path, patterns: List[str]) -> List[Path]:
    """Return all files under *root* whose names match *patterns* (fnmatch)."""
    result: List[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and any(fnmatch.fnmatch(p.name, pat) for pat in patterns):
            result.append(p)
    return sorted(result, key=lambda p: p.as_posix())


def build_output(files: List[Path], separator: str) -> str:
    """Return the final multi-file string representation."""
    parts: List[str] = []

    for idx, p in enumerate(files):
        header = f"File: {p}"
        parts.extend([header, "-" * len(header)])

        try:
            content = get_handler(p)(p)
        except UnicodeDecodeError as exc:
            content = f"(decode error: {exc})"
        except json.JSONDecodeError as exc:
            content = f"(invalid JSON: {exc})"
        except Exception as exc:  # pragma: no cover
            content = f"(error reading file: {exc})"

        parts.append(content)

        if idx < len(files) - 1:
            parts.append(separator)

    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Concatenate source files and copy them to the clipboard "
        "(Windows/macOS).",
        epilog="Example: python feeder.py --root ./shader --include *.comp *.glsl",
    )
    parser.add_argument(
        "--root",
        required=True,
        type=Path,
        help="Root directory to search recursively",
    )
    parser.add_argument(
        "--include",
        nargs="+",
        required=True,
        metavar="PATTERN",
        help="One or more fnmatch patterns, e.g. *.py *.glsl",
    )
    parser.add_argument(
        "--no-clipboard",
        action="store_true",
        help="Print only, do not copy to the clipboard",
    )
    args = parser.parse_args()

    if not args.root.is_dir():
        sys.exit(f"Error: '{args.root}' is not a directory.")

    files = collect_files(args.root, args.include)
    if not files:
        sys.exit("No matching files found.")

    output = build_output(files, "\n" + "=" * 80 + "\n")
    print("\n" + output + "\n")
    print(f"--- Processed {len(files)} file(s) ---")

    if not args.no_clipboard and sys.platform in ("win32", "darwin"):
        copy_to_clipboard(output)
    else:
        print(f"--- Clipboard step skipped (platform={sys.platform}) ---")


if __name__ == "__main__":
    main()
