"""pandera-mypy - mypy plugin resolving DataFrameModel columns as ``str``.

Usage:
    Add the plugin to your mypy configuration:

    .. code-block:: ini

        # mypy.ini
        [mypy]
        plugins = pandera_mypy.plugin

    .. code-block:: toml

        # pyproject.toml
        [tool.mypy]
        plugins = ["pandera_mypy.plugin"]
"""

__all__ = ["PanderaPlugin", "plugin"]

from pandera_mypy.plugin import PanderaPlugin, plugin
