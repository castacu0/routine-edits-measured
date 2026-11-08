"""
Corpus-path guards shared by every harness entry point.

Two speed bumps, not security controls: a corpus must live OUTSIDE this
repository, and the caller must affirm it is benign. The actual control is the
person running the command. See research/README.md and docs/ETHICS_AND_IRB.md.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def inside_repo(path: Path) -> bool:
    try:
        path.resolve().relative_to(REPO)
        return True
    except ValueError:
        return False


def guard_corpus(path: Path, confirmed: bool) -> None:
    resolved = path.resolve()
    if not resolved.exists():
        raise SystemExit(f"✖ corpus not found: {resolved}")
    if inside_repo(resolved):
        raise SystemExit(
            "✖ The corpus must live OUTSIDE this repository.\n"
            "  No image dataset belongs in a zero-custody repo, benign or not.\n"
            "  Point --corpus at a directory elsewhere on disk."
        )
    if not confirmed:
        raise SystemExit(
            "✖ Refusing to run without --i-confirm-benign-corpus.\n\n"
            "  This harness is benign-only. By passing that flag you state that\n"
            "  the corpus contains ordinary images, no abuse material, and no\n"
            "  case data, and that you are licensed to process it.\n\n"
            "  See docs/ETHICS_AND_IRB.md."
        )


def guard_output(path: Path) -> None:
    """Derived artefacts (hash files, generated images) never land in the repo either."""
    if inside_repo(path):
        raise SystemExit(
            "✖ Output directory must be OUTSIDE this repository.\n"
            "  Hash files and generated images are published as release assets or\n"
            "  kept on disk elsewhere; see research/COMPUTE.md."
        )
