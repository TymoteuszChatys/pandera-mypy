# pandera-mypy

> A mypy plugin that resolves [Pandera](https://pandera.readthedocs.io/) `DataFrameModel` column attributes as `str`, eliminating false type errors when passing column names to `polars.col()` or any other `str`-expecting API.

## The Problem

Pandera's `DataFrameModel` supports a convenient **bare-type** shorthand for
column annotations, where a plain Python type is used instead of the full
`Series[T]` form:

```python
import pandera.polars as pa

class MySchema(pa.DataFrameModel):
    quantity: int   # shorthand for Series[int]
    label: str      # shorthand for Series[str]
```

At **runtime**, accessing a column attribute always returns its *name* as a
plain `str`:

```python
>>> MySchema.quantity
'quantity'
>>> MySchema.label
'label'
```

Without the plugin, mypy infers the **declared type** (`int`, `str`, …) rather
than `str`, causing spurious errors when column names are passed to
`polars.col()` or any other `str`-expecting API:

```python
import polars as pl

pl.col(MySchema.quantity)
# ^ error: Argument 1 to "col" has incompatible type "int"; expected "str"
```

> **`Series[T]` annotations**: Pandera's bundled stubs already type
> class-level attribute access as `str` for `Series[T]`-annotated columns
> across all supported versions (0.21.1-0.31.1). The plugin ensures uniform
> `str` inference when schemas mix `Series[T]` and bare-type annotations.

## The Solution

This plugin overrides the inferred type of every column-annotated attribute on
a `DataFrameModel` subclass to `str`, matching the actual runtime behaviour —
no changes to your Pandera models required.

```python
# With the plugin enabled:
pl.col(MySchema.quantity)         # ✅  no error
col_name: str = MySchema.quantity # ✅  no error
```

## Installation

```bash
pip install pandera-mypy
```

```bash
# or with uv:
uv add pandera-mypy
```

## Configuration

Add the plugin to your mypy configuration and that's it:

**`mypy.ini`**
```ini
[mypy]
plugins = pandera_mypy.plugin
```

**`pyproject.toml`**
```toml
[tool.mypy]
plugins = ["pandera_mypy.plugin"]
```

**`setup.cfg`**
```ini
[mypy]
plugins = pandera_mypy.plugin
```

## Compatibility

| Python | Supported |
|--------|-----------|
| 3.10   | ✅        |
| 3.11   | ✅        |
| 3.12   | ✅        |
| 3.13   | ✅        |
| 3.14   | ✅        |

Requires `mypy >= 1.0.0` and works with both the **Polars** and **Pandas** backends of Pandera.

## How It Works

The plugin implements mypy's `get_class_attribute_hook` (for `MySchema.price` style class-level access) and `get_attribute_hook` (for instance-level access).

For every attribute access, it checks whether:

1. The owning class inherits from a Pandera `DataFrameModel` (detected via the MRO, so indirect subclasses work too).
2. The attribute is annotated with a Pandera column type — either `Series[T]` or a bare type such as `int`.

When both conditions hold, the plugin replaces the inferred type with `builtins.str`.

> **Why `get_class_attribute_hook`?**  
> Mypy routes class-level attribute access (e.g. `MySchema.price`) through
> `get_class_attribute_hook` in `mypy.checkmember`, **not** through
> `get_attribute_hook`. Using only `get_attribute_hook` would leave the common
> `pl.col(MySchema.price)` pattern uncorrected.

## Development

```bash
# Install all dependencies including the dev group
uv sync --group dev

# Run the test suite with coverage
uv run pytest

# Type-check the plugin
uv run mypy src

# Lint (report only)
uv run ruff check .

# Lint and auto-fix
uv run ruff check --fix .

# Format
uv run ruff format .

# Check formatting without changing files
uv run ruff format --check .

# Verify the lockfile is up to date with pyproject.toml
uv lock --check

# Build the wheel and sdist
uv build
```
