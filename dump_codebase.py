"""
dump_codebase.py
Concatenates the project's source files into a single markdown file
so it can be pasted into an AI with a large context window (e.g. Gemini).

Run from the project root:  python dump_codebase.py
Output: codebase_dump.md
"""

import os

# ---- CONFIG: edit these to fit your project ----

ROOT_DIR = "."  # project root, since script lives there

# File extensions to include in the dump
INCLUDE_EXTENSIONS = {
    ".py",
    ".html",
    ".css",
    ".js",
    ".yaml", ".yml",
    ".json"       # include if you want existing README/notes as context too
}

# Folder names to skip entirely (checked against each path segment)
EXCLUDE_DIRS = {
    "venv", ".venv", "env",
    "__pycache__",
    ".git",
    "node_modules",
    ".idea", ".vscode",
    "output", "notes", "generated",   # adjust to your actual output folder name(s)
    "tests", "test",                  # remove this line if you want tests included
    "site-packages",
    ".pytest_cache",
    "build", "dist",
}

# Specific filenames to always skip
EXCLUDE_FILES = {
    "dump_codebase.py",   # don't include this script itself
    "codebase_dump.md",   # don't include the output file if re-run
    ".DS_Store",
}

OUTPUT_FILE = "codebase_dump.md"

# ---- SCRIPT ----

def should_skip_dir(dirname: str) -> bool:
    return dirname in EXCLUDE_DIRS or dirname.startswith(".")


def should_include_file(filename: str) -> bool:
    if filename in EXCLUDE_FILES:
        return False
    _, ext = os.path.splitext(filename)
    return ext in INCLUDE_EXTENSIONS


def main():
    collected_files = []

    for current_dir, subdirs, files in os.walk(ROOT_DIR):
        # prune excluded directories in-place so os.walk doesn't descend into them
        subdirs[:] = [d for d in subdirs if not should_skip_dir(d)]

        for fname in files:
            if should_include_file(fname):
                full_path = os.path.join(current_dir, fname)
                collected_files.append(full_path)

    collected_files.sort()  # stable, predictable order

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("# Codebase Dump\n\n")
        out.write(f"Total files included: {len(collected_files)}\n\n")
        out.write("## File list\n")
        for path in collected_files:
            out.write(f"- {path}\n")
        out.write("\n---\n\n")

        for path in collected_files:
            out.write(f"--- FILE: {path} ---\n\n")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                content = "[Could not read file: non-UTF-8 content, likely binary]"
            out.write("```\n")
            out.write(content)
            out.write("\n```\n\n")

    print(f"Done. Wrote {len(collected_files)} files to {OUTPUT_FILE}")
    print("Files included:")
    for path in collected_files:
        print(f"  {path}")


if __name__ == "__main__":
    main()