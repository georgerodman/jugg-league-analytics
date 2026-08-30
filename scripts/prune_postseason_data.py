#!/usr/bin/env python3
"""Prune completed-season data while preserving the verified Draft Room runtime."""

from __future__ import annotations

import argparse
from pathlib import Path

from audit_repository_artifacts import ROOT, RUNTIME_ROOTS, TEST_ROOTS, closure


DATA = ROOT / "data"
LARGE_REFETCHABLE_RAW = (
    DATA / "raw" / "nflverse",
    DATA / "raw" / "nflverse_depth_charts",
)


def retained_paths() -> set[str]:
    runtime, runtime_missing = closure(RUNTIME_ROOTS)
    tests, test_missing = closure(TEST_ROOTS)
    missing = runtime_missing | test_missing
    if missing:
        raise RuntimeError(f"Cannot prune with missing runtime/test artifacts: {sorted(missing)}")

    retained = runtime | tests
    raw = DATA / "raw"
    for path in raw.rglob("*"):
        if not path.is_file():
            continue
        if any(path.is_relative_to(source) for source in LARGE_REFETCHABLE_RAW):
            continue
        retained.add(str(path.relative_to(ROOT)))
    return retained


def candidates(retained: set[str]) -> list[Path]:
    return sorted(
        (
            path
            for path in DATA.rglob("*")
            if path.is_file() and str(path.relative_to(ROOT)) not in retained
        ),
        key=lambda path: str(path.relative_to(ROOT)),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Delete the reported files.")
    parser.add_argument(
        "--archive-confirmed",
        action="store_true",
        help="Confirm the checksummed season-data archive was copied outside the repository.",
    )
    args = parser.parse_args()

    retained = retained_paths()
    removal = candidates(retained)
    bytes_removed = sum(path.stat().st_size for path in removal)
    print(f"Retained files: {len(retained)}")
    print(f"Candidate files: {len(removal)}")
    print(f"Candidate bytes: {bytes_removed}")
    for path in removal:
        print(path.relative_to(ROOT))

    if not args.apply:
        print("Dry run only. Use --apply --archive-confirmed after copying the season archive.")
        return
    if not args.archive_confirmed:
        raise SystemExit("Refusing to prune without --archive-confirmed")

    for path in removal:
        path.unlink()
    for directory in sorted((path for path in DATA.rglob("*") if path.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass
    print(f"Removed {len(removal)} files ({bytes_removed} bytes).")


if __name__ == "__main__":
    main()
