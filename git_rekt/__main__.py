"""Allow `python -m git_rekt` as an alternative to the `git-rekt` entry point."""

from git_rekt.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
