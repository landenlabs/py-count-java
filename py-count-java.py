#!/usr/bin/env python3
# ----------------------------------------------------------------------
# Copyright (c) 2026 LanDen Labs - Dennis Lang
# https://landenlabs.com
# ----------------------------------------------------------------------
"""py-count-java - Count Java "lines of code" using the locjava rule set.

Reimplements the counting rule described by the locjava tool
(https://sourceforge.net/p/locjava/wiki/Home/):

    The number of lines is computed as the number of terminal semicolons
    and right braces.  Semicolons within a for statement are not counted.
    Comment statements are ignored.

The scanner does a lexical pass rather than a full parse, so it also
tracks string/char literals and comments closely enough to avoid counting
semicolons or braces that only appear inside them.  Since it never
validates grammar, it will happily produce a count for C code, pseudocode,
or any plain text file -- same as the original tool.
"""

import argparse
import os
import sys

VERSION = "v0.1.0"

IDENT_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$"
)

LANGUAGE_BY_EXT = {
    ".java": "Java",
}


# ---------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------

def count_code_lines(text):
    """Count terminal semicolons and right braces, per the locjava rule set.

    Comments and string/char literals are skipped so that punctuation
    inside them is never counted.  Semicolons that appear directly inside
    a for-statement's own "( ... )" header are excluded; braces are always
    counted, including ones inside a for header (e.g. a lambda block).
    """
    n = len(text)
    i = 0
    code_count = 0
    paren_depth = 0
    for_header_depths = []  # stack of paren_depth values that are for(...) headers
    last_ident = ""

    while i < n:
        c = text[i]

        if c == "/" and i + 1 < n and text[i + 1] == "/":
            i += 2
            while i < n and text[i] != "\n":
                i += 1
            last_ident = ""
            continue

        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            end = text.find("*/", i)
            i = n if end == -1 else end + 2
            last_ident = ""
            continue

        if c == '"':
            # Java 15+ text block: """ ... """
            if text[i:i + 3] == '"""':
                end = text.find('"""', i + 3)
                i = n if end == -1 else end + 3
            else:
                i += 1
                while i < n and text[i] != '"':
                    i += 2 if text[i] == "\\" else 1
                i += 1
            last_ident = ""
            continue

        if c == "'":
            i += 1
            while i < n and text[i] != "'":
                i += 2 if text[i] == "\\" else 1
            i += 1
            last_ident = ""
            continue

        if c in IDENT_CHARS:
            j = i
            while j < n and text[j] in IDENT_CHARS:
                j += 1
            last_ident = text[i:j]
            i = j
            continue

        if c == "(":
            paren_depth += 1
            if last_ident == "for":
                for_header_depths.append(paren_depth)
            last_ident = ""
            i += 1
            continue

        if c == ")":
            if for_header_depths and for_header_depths[-1] == paren_depth:
                for_header_depths.pop()
            paren_depth = max(0, paren_depth - 1)
            last_ident = ""
            i += 1
            continue

        if c == ";":
            in_for_header = bool(for_header_depths) and for_header_depths[-1] == paren_depth
            if not in_for_header:
                code_count += 1
            last_ident = ""
            i += 1
            continue

        if c == "}":
            code_count += 1
            last_ident = ""
            i += 1
            continue

        if c.isspace():
            i += 1
            continue

        last_ident = ""
        i += 1

    return code_count


def count_physical_lines(text):
    if not text:
        return 0
    return len(text.splitlines())


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def language_for(path):
    ext = os.path.splitext(path)[1].lower()
    return LANGUAGE_BY_EXT.get(ext, ext[1:].upper() if ext else "(no extension)")


def find_files(paths, extensions):
    """Resolve explicit files and directories (scanned recursively) into a
    flat, de-duplicated list of file paths.  Explicit files are always
    included regardless of extension; directories are filtered to the
    given extensions and skip hidden (dot) subdirectories.
    """
    seen = set()
    files = []

    def add(path):
        real = os.path.realpath(path)
        if real not in seen:
            seen.add(real)
            files.append(path)

    for path in paths:
        if os.path.isfile(path):
            add(path)
        elif os.path.isdir(path):
            for root, dirs, names in os.walk(path):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for name in names:
                    ext = os.path.splitext(name)[1].lower()
                    if ext in extensions:
                        add(os.path.join(root, name))
        else:
            print("Warning: path not found: %s" % path, file=sys.stderr)

    return files


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(results, by_file):
    by_language = {}
    for path, lines, code in results:
        lang = language_for(path)
        agg = by_language.setdefault(lang, [0, 0, 0])
        agg[0] += 1
        agg[1] += lines
        agg[2] += code

    sep = "-" * 60
    print(sep)
    print("%-24s %10s %10s %10s" % ("Language", "files", "lines", "code"))
    print(sep)

    if by_file:
        for path, lines, code in results:
            print("%-24s %10s %10d %10d" % (path, "", lines, code))
        print(sep)

    total_files = total_lines = total_code = 0
    for lang in sorted(by_language):
        n_files, n_lines, n_code = by_language[lang]
        print("%-24s %10d %10d %10d" % (lang, n_files, n_lines, n_code))
        total_files += n_files
        total_lines += n_lines
        total_code += n_code
    print(sep)

    if len(by_language) > 1:
        print("%-24s %10d %10d %10d" % ("SUM:", total_files, total_lines, total_code))
        print(sep)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=f"py-count-java {VERSION}\n"
                     "Count Java lines of code using the locjava rule set "
                     "(terminal semicolons + right braces).",
        epilog="""Examples:
  py-count-java.py file1.java file2.java
  py-count-java.py dir1 dir2/subdir
  py-count-java.py file1.java dir1 --by-file
  py-count-java.py --ext java,jav src/
""",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "paths", nargs="+", metavar="FILE_OR_DIR",
        help="Java files and/or directories to scan (directories are scanned recursively)",
    )
    parser.add_argument(
        "--ext", default="java", metavar="EXT[,EXT...]",
        help="Comma-separated extensions to include when scanning directories "
             "(default: java); explicit file arguments are always counted",
    )
    parser.add_argument(
        "--by-file", action="store_true",
        help="Show a row per file in addition to the per-language totals",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()
    extensions = {"." + e.strip().lstrip(".").lower() for e in args.ext.split(",") if e.strip()}

    files = find_files(args.paths, extensions)
    if not files:
        print("No files found to count.", file=sys.stderr)
        sys.exit(1)

    results = []
    for path in files:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as e:
            print("Warning: could not read %s: %s" % (path, e), file=sys.stderr)
            continue
        results.append((path, count_physical_lines(text), count_code_lines(text)))

    print_report(results, args.by_file)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
