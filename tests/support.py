"""Shared test scaffolding for the pandera_mypy test suite.

Provides :func:`run_mypy` and the mypy configuration constants used by
both :mod:`test_plugin` (plugin active) and
:mod:`test_problem_statement` (plugin absent, bare-type sources only).
"""

from __future__ import annotations

import textwrap
from pathlib import Path  # noqa: TC003

import mypy.api

_MYPY_CONFIG_WITH_PLUGIN = """\
[mypy]
plugins = pandera_mypy.plugin
ignore_missing_imports = True
"""

_MYPY_CONFIG_WITHOUT_PLUGIN = """\
[mypy]
ignore_missing_imports = True
"""


def run_mypy(
    source: str, tmp_path: Path, *, with_plugin: bool = True
) -> tuple[str, str, int]:
    """Run mypy on *source*, return ``(stdout, stderr, exit_code)``."""
    config = (
        _MYPY_CONFIG_WITH_PLUGIN if with_plugin else _MYPY_CONFIG_WITHOUT_PLUGIN
    )
    src_file = tmp_path / "subject.py"
    src_file.write_text(textwrap.dedent(source))
    cfg_file = tmp_path / "mypy.ini"
    cfg_file.write_text(config)
    return mypy.api.run(
        [
            "--config-file",
            str(cfg_file),
            "--no-error-summary",
            "--show-error-codes",
            str(src_file),
        ]
    )
