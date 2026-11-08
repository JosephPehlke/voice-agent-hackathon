"""Validate every submissions/*/agent.yaml (used in CI on pull requests)."""
import sys

from .common import load_submissions, validate_submission


def main() -> int:
    bad = 0
    for slug, data in load_submissions().items():
        errs = validate_submission(slug, data)
        print(f"{'FAIL' if errs else 'ok  '} {slug}" + (f": {'; '.join(errs)}" if errs else ""))
        bad += bool(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
