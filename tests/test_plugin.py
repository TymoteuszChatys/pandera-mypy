"""Integration tests — plugin active, real pandera + polars installation.

Every ``.txt`` file under ``sources/plugin/`` is a standalone mypy
source that must pass cleanly with the plugin enabled.  The suite covers
both ``Series[T]``-style and bare-type column annotations as well as
edge cases (ClassVar attributes, plain classes, classmethods).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .support import run_mypy

_SOURCES_DIR = Path(__file__).parent / "sources" / "plugin"


def _cases() -> list[pytest.param]:
    return [
        pytest.param(p.read_text(), id=p.stem)
        for p in sorted(_SOURCES_DIR.glob("*.txt"))
    ]


@pytest.mark.parametrize("source", _cases())
def test_plugin_accepts(source: str, tmp_path: Path) -> None:
    """Mypy must accept every well-typed pandera usage with the plugin.

    Covers both ``Series[T]``-style annotations (where pandera stubs
    already infer ``str``) and bare-type annotations (e.g.
    ``quantity: int``, where the plugin is the sole source of correct
    ``str`` inference).
    """
    stdout, _stderr, exit_code = run_mypy(source, tmp_path)
    assert exit_code == 0, f"mypy reported errors:\n{stdout}"
