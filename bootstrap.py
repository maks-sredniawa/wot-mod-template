#!/usr/bin/env python3
"""Turns the example mod into a new mod: renames its id, files and package, and swaps in the mod README."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SLUG = "example_mod"
NAME = "Example Mod"
DESCRIPTION = "Writes a line to game.log when a battle loads."
SKIP = {".git", "build", "dist", "__pycache__"}


def tracked_files() -> list[Path]:
    paths = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix == ".pyc" or path.name == "bootstrap.py":
            continue
        if SKIP.intersection(path.relative_to(ROOT).parts):
            continue
        paths.append(path)
    return paths


def lowercase_description(description: str) -> str:
    return description[0].lower() + description[1:]


def replacements(slug: str, name: str, description: str) -> list[tuple[str, str]]:
    return [
        (DESCRIPTION, description),
        (lowercase_description(DESCRIPTION), lowercase_description(description)),
        (SLUG, slug),
        (SLUG.replace("_", "-"), slug.replace("_", "-")),
        (NAME, name),
    ]


def rewrite(path: Path, pairs: list[tuple[str, str]], dry_run: bool) -> None:
    text = path.read_text(encoding="utf-8")
    new = text
    for old, replacement in pairs:
        new = new.replace(old, replacement)
    if new != text:
        print(f"rewrite {path.relative_to(ROOT)}")
        if not dry_run:
            path.write_text(new, encoding="utf-8")


def renamed(path: Path, slug: str) -> Path:
    return ROOT / str(path.relative_to(ROOT)).replace(SLUG, slug)


def move(source: Path, target: Path, dry_run: bool) -> None:
    print(f"move    {source.relative_to(ROOT)} -> {target.relative_to(ROOT)}")
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "mv", "-f", str(source), str(target)], cwd=ROOT, check=True)


def remove_empty_dirs(dry_run: bool) -> None:
    for path in sorted(ROOT.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and not SKIP.intersection(path.relative_to(ROOT).parts) and not any(path.iterdir()):
            if not dry_run:
                path.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True, help="snake_case id, e.g. ping_distance. The mod id becomes maksforge.<slug>.")
    parser.add_argument("--name", required=True, help='Name shown in the README and release titles, e.g. "Ping Distance".')
    parser.add_argument("--description", required=True, help="One sentence for meta.xml and the README, ending with a full stop.")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Print what would change and stop.")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z][a-z0-9_]*", args.slug):
        sys.exit("--slug must be lowercase letters, digits and underscores, starting with a letter")
    if args.slug == SLUG:
        sys.exit(f"--slug must differ from the template's {SLUG}")
    if not (ROOT / "mod-README.md").is_file():
        sys.exit("mod-README.md is missing: this repository has already been bootstrapped")

    pairs = replacements(args.slug, args.name, args.description)
    for path in tracked_files():
        rewrite(path, pairs, args.dry_run)
    for path in tracked_files():
        if SLUG in str(path.relative_to(ROOT)):
            move(path, renamed(path, args.slug), args.dry_run)
    move(ROOT / "mod-README.md", ROOT / "README.md", args.dry_run)
    remove_empty_dirs(args.dry_run)

    if args.dry_run:
        return 0
    subprocess.run(["git", "rm", "-q", "bootstrap.py"], cwd=ROOT, check=True)
    print("\nDone. Next: python2.7 -m unittest discover -s tests && ./build.sh, then commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
