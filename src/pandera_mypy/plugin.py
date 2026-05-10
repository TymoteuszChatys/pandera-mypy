"""Mypy plugin resolving Pandera DataFrameModel column attrs as ``str``.

Background
----------
Pandera's :class:`~pandera.api.base.model.DataFrameModel` (and its polars
variant) supports two column-annotation forms::

    import pandera.polars as pa
    from pandera.typing.polars import Series

    class MySchema(pa.DataFrameModel):
        price: Series[float]   # Series-style annotation
        quantity: int          # bare-type annotation (equivalent in pandera)

Pandera's metaclass intercepts class-attribute access and returns the
*column name* as a plain :class:`str` at runtime::

    >>> MySchema.price
    'price'
    >>> MySchema.quantity
    'quantity'

For ``Series[T]``-style annotations, pandera's own stubs already type
class-level attribute access as ``str`` across all supported versions
(0.21.1-0.31.1).

For **bare-type annotations** (e.g. ``quantity: int``), mypy infers the
declared type (``int``) rather than ``str``, causing a spurious error
whenever that value is passed to a :class:`str`-expecting function::

    import polars as pl

    pl.col(MySchema.quantity)
    # ^ error: Argument 1 has incompatible type "int"; expected "str"

This plugin overrides the attribute type for every column-annotated field
on a DataFrameModel subclass so that mypy sees ``str`` instead of the
column dtype, matching the actual runtime behaviour.  Both
``Series[T]``-style and bare-type annotations are handled, ensuring
consistent inference when schemas mix both annotation forms.

Plugin entry point
------------------
Register in ``mypy.ini``::

    [mypy]
    plugins = pandera_mypy.plugin

or in ``pyproject.toml``::

    [tool.mypy]
    plugins = ["pandera_mypy.plugin"]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mypy.nodes import TypeInfo, Var
from mypy.plugin import AttributeContext, Plugin

if TYPE_CHECKING:
    from collections.abc import Callable

    from mypy.types import Type


def plugin(_version: str) -> type[PanderaPlugin]:
    """Return the plugin class (mypy entry point).

    Args:
        _version: The mypy version string passed by mypy itself
            (e.g. ``"1.10.0"``). Not used by this plugin.

    Returns:
        The :class:`PanderaPlugin` class.

    """
    return PanderaPlugin


class PanderaPlugin(Plugin):
    """Mypy plugin resolving Pandera DataFrameModel column attrs as ``str``.

    Registers a type hook (:func:`_column_attr_hook`) for every
    column-annotated attribute on a
    :class:`~pandera.api.base.model.DataFrameModel` subclass so that mypy
    understands that accessing such an attribute yields the column *name*
    (a :class:`str`) rather than a value of the column *dtype*.

    The plugin is essential for **bare-type annotations** (e.g.
    ``quantity: int``), where mypy infers the declared type rather than
    ``str``.  For ``Series[T]``-style annotations, pandera's own stubs
    already provide the correct ``str`` inference, but the plugin ensures
    uniform behaviour when both annotation forms appear in the same schema.

    See the module docstring for configuration instructions.
    """

    def get_attribute_hook(
        self,
        fullname: str,
    ) -> Callable[[AttributeContext], Type] | None:
        """Return the pandera column hook for instance attribute access.

        Mypy calls this method when an attribute is accessed on an *instance*
        of a class.  For class-level access (e.g. ``MySchema.price``) mypy
        uses :meth:`get_class_attribute_hook` instead.

        Args:
            fullname: The fully-qualified attribute name in the form
                ``my_module.MySchema.col_name``.

        Returns:
            :func:`_column_attr_hook` when the attribute is a pandera column,
            ``None`` otherwise.

        """
        return self._hook_for(fullname)

    def get_class_attribute_hook(
        self,
        fullname: str,
    ) -> Callable[[AttributeContext], Type] | None:
        """Return the pandera column hook for class-level attribute access.

        Mypy calls this method when an attribute is accessed directly on the
        *class* (e.g. ``MySchema.price``).  This is the common pattern when
        passing column names to :func:`polars.col`.

        Args:
            fullname: The fully-qualified attribute name in the form
                ``my_module.MySchema.col_name``.

        Returns:
            :func:`_column_attr_hook` when the attribute is a pandera column,
            ``None`` otherwise.

        """
        return self._hook_for(fullname)

    def _hook_for(
        self, fullname: str
    ) -> Callable[[AttributeContext], Type] | None:
        """Return the column-attribute hook for *fullname*, or ``None``.

        Handles both ``Series[T]``-style annotations and bare-type
        annotations (e.g. ``quantity: int``), since pandera treats
        both as column declarations at runtime and returns the column
        *name* as a :class:`str` for both forms.

        Shared implementation used by both :meth:`get_attribute_hook` (instance
        access) and :meth:`get_class_attribute_hook` (class-level access such as
        ``MySchema.price``).

        Args:
            fullname: The fully-qualified attribute name in the form
                ``my_module.MySchema.col_name``.

        Returns:
            :func:`_column_attr_hook` when the attribute is a pandera column,
            ``None`` otherwise.

        """
        dot = fullname.rfind(".")
        if dot == -1:
            return None  # pragma: no cover - mypy always qualifies names

        class_fullname = fullname[:dot]
        attr_name = fullname[dot + 1 :]

        class_sym = self.lookup_fully_qualified(class_fullname)
        if class_sym is None or not isinstance(
            class_sym.node, TypeInfo
        ):  # pragma: no cover
            return None

        class_info: TypeInfo = class_sym.node

        if not _is_pandera_dataframe_model(class_info):
            return None

        attr_sym = class_info.names.get(attr_name)
        if attr_sym is None or not isinstance(attr_sym.node, Var):
            return None

        node: Var = attr_sym.node
        if node.type is None or node.is_classvar:
            return None

        return _column_attr_hook


def _column_attr_hook(ctx: AttributeContext) -> Type:
    """Return the built-in ``str`` type for a DataFrameModel column attribute.

    Pandera's metaclass returns the column *name* (a plain :class:`str`)
    whenever a column-annotated attribute is accessed on a DataFrameModel
    subclass.  For bare-type annotations (e.g. ``quantity: int``), mypy
    infers the declared type without this hook, so the hook is necessary
    to correct the inference to ``str``.  For ``Series[T]``-style
    annotations, pandera's stubs already produce ``str``, but the hook
    ensures consistent behaviour across mixed schemas.

    Args:
        ctx: The attribute-access context provided by mypy.

    Returns:
        The ``builtins.str`` type.

    """
    return ctx.api.named_generic_type("builtins.str", [])


def _is_pandera_dataframe_model(info: TypeInfo) -> bool:
    """Return ``True`` if *info* is a subclass of any pandera DataFrameModel.

    Walks the full MRO so that indirect subclasses are detected correctly.

    Args:
        info: A mypy :class:`~mypy.nodes.TypeInfo` representing a class.

    Returns:
        ``True`` when any entry in the MRO satisfies
        :func:`_is_dataframe_model_base_fullname`.

    """
    return any(
        _is_dataframe_model_base_fullname(base.fullname) for base in info.mro
    )


def _is_dataframe_model_base_fullname(fullname: str) -> bool:
    """Return ``True`` if *fullname* identifies a pandera DataFrameModel base.

    The check requires the ``pandera.`` namespace prefix to avoid false
    positives with third-party classes that happen to be named
    ``DataFrameModel`` or ``BaseModel``.

    Args:
        fullname: A fully-qualified class name from mypy's symbol table,
            e.g. ``pandera.api.polars.model.DataFrameModel``.

    Returns:
        ``True`` when the name is in the pandera namespace and refers to
        ``DataFrameModel`` or ``BaseModel``.

    """
    return _is_pandera_ns(fullname) and (
        "DataFrameModel" in fullname or "BaseModel" in fullname
    )


def _is_pandera_ns(fullname: str) -> bool:
    """Return ``True`` if *fullname* belongs to the pandera namespace.

    Matches names that start with ``pandera.`` (the primary case for all
    public pandera APIs) or contain ``.pandera.`` as a segment (for rare
    cases where pandera is re-exported from a nested namespace).

    Args:
        fullname: A fully-qualified name from mypy's symbol table.

    Returns:
        ``True`` when *fullname* is unambiguously in the ``pandera``
        namespace.

    """
    return fullname.startswith("pandera.") or ".pandera." in fullname
