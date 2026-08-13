# AGENTS.md

> Project constitution for AI-assisted development.

## Commands

```bash
uv run pytest                # Run test suite
uv run pytest -x             # Stop on first failure
uv run ruff check .          # Lint
uv run ruff format .         # Format
uv run python src/main.py    # Run the application
```

> Do NOT use pip, pip install, or requirements.txt. This project uses UV.
> Do NOT create virtual environments manually. UV manages environments automatically.

## Project structure

```
wpsrt/
  pyproject.toml          # Single source of truth for deps and config
  uv.lock                 # Lockfile — do not edit manually
  src/
    wpsrt/
      methods/            # Module for different soring methods
        __init__.py
        aspectration.py   # Algorithm to sort images by aspect ratio
        clip.py           # AI vision assisted image sorting using `clip-ViT-B-32`
        nsfw.py           # AI vision assisted image sorting using onnx NudeDetector
      tools/              # Structured logging setup
        __init__.py 
        converter.py      # Utilities for converting image formats
        hashing.py        # Image hashing library and hash database management
      __init__.py
      errors.py           # Custom Exception classes
      inpsector.py        # Used for NudeDetector module as assisting tool
      main.py             # Entry point
      wallpapers.py       # Core functions for wallpaper sorting and routes calls to wpsrt.methods.*
  tests/
    conftest.py           # Shared fixtures
    test_inventory.py
    test_connections.py
  inventory/
    hosts.yaml            # Device inventory
```

## Dependencies

- Python 3.12+
- UV for package and environment management
- Ruff for linting and formatting
- pytest for testing

Adding a dependency:
```bash
uv add <package>           # Adds to pyproject.toml and updates uv.lock
uv add --dev <package>     # Dev dependency
```

## Code style

- **Type hints** on all function signatures. Use `from __future__ import annotations` at the top of every module.
- **Docstrings** on public functions and classes. Google style.
- **Snake_case** for functions, variables, and modules. **PascalCase** for classes.
- **f-strings** for string formatting. No `.format()` or `%` formatting.
- **pathlib.Path** for file paths. No `os.path`.
- **Structured logging** via the `logging` module. No bare `print()` statements.
- Functions should do one thing. If a function exceeds 30 lines, consider splitting it.

## Error handling

- Catch specific exceptions, never bare `except:`.
- Network operations (SSH, API calls) must have explicit timeout parameters.
- Use `contextlib.suppress()` for expected exceptions, not try/except/pass.
- Re-raise unexpected exceptions. Do not silently swallow errors.

## Design patterns

- **Protocols over inheritance.** Use `typing.Protocol` to define interfaces.
- **Context managers** for anything that needs cleanup — files, connections, temporary state.
- **Dataclasses for internal state, Pydantic for boundaries.** Use `dataclasses.dataclass` for value objects. Use Pydantic `BaseModel` when parsing external input.
- **Dependency injection** for testability. Pass collaborators as parameters instead of constructing them internally.
- **Composition over inheritance.** Small, focused functions that compose together.

## Testing

- Every new module gets a corresponding test file in `tests/`.
- Use fixtures for device connections and shared state.
- Mock external network calls in unit tests. Integration tests can hit lab devices.
- Test names describe the scenario: `test_inventory_loads_from_yaml`, not `test_inventory_1`.

## Constraints

- Do NOT use pip, virtualenv, poetry, or pipenv. UV only.
- Do NOT create requirements.txt files.
- Do NOT use `os.system()` or `subprocess.run()` for tasks UV can handle.
- Do NOT commit `.env` files or credentials. Use environment variables.
- Do NOT modify uv.lock manually.
- Ruff configuration lives in pyproject.toml, not in separate config files.