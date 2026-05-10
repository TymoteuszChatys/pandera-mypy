"""Tests demonstrating the type error the plugin is designed to resolve.

Pandera's ``DataFrameModel`` supports **bare-type** column annotations such
as ``quantity: int`` as a shorthand for ``quantity: Series[int]``.  When a
bare-type annotation is used, mypy infers the declared type (e.g. ``int``)
rather than ``str``, causing a false error at sites like
``pl.col(MySchema.quantity)``.

These tests verify that such sources *fail* mypy type-checking when the
plugin is **not** active, confirming that the plugin is necessary to
produce the correct ``str`` inference for bare-type annotations.

Note: For ``Series[T]``-style annotations, pandera's own stubs already
type class-level attribute access as ``str`` (verified across pandera
0.21.1-0.31.1), so no problem-statement test is needed for that form.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .support import run_mypy

_SOURCES_DIR = Path(__file__).parent / "sources" / "plugin"


def _cases() -> list[pytest.param]:
    return [
        pytest.param(p.read_text(), id=p.stem)
        for p in sorted(_SOURCES_DIR.glob("bare_type_*.txt"))
    ]


@pytest.mark.parametrize("source", _cases())
def test_problem_statement_fails_without_plugin(
    source: str, tmp_path: Path
) -> None:
    """Mypy must reject bare-type column sources without the plugin.

    Bare-type annotations (e.g. ``quantity: int``) are inferred as the
    declared type by mypy without the plugin, so assigning to ``str``
    must produce a type error.  The plugin corrects this to ``str``.
    """
    _stdout, _stderr, exit_code = run_mypy(source, tmp_path, with_plugin=False)
    assert exit_code != 0, "expected mypy to report a type error"
