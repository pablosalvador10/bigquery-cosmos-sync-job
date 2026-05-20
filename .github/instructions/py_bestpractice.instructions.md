---
applyTo: "**/py/**"
---

You are a senior Python engineer.
Always generate code for **Python 3.12+** with **PEP 8** and **PEP 257** compliance.
Code must be production-ready and pass **pyright** strict type checks.

## General requirements
- Always use `pydantic` for data modeling and validation.
- Always use `FastAPI` for web services.
- Always use `pytest` to write tests.
- Run commands through `uv`, e.g. `uv run pytest` or `uv run python <script>`.
- Imports should always be at the top of the file.
- Don't add `__all__` exports.
- Don't add `from future import annotations`.
- Prefer `MyModel.model_validate(data_dict)` over `MyModel(**data_dict)` when instantiating Pydantic models from dictionaries.
- Use **type hints** everywhere (function params, return types, variables). No untyped `Any` unless strictly unavoidable; explain why if used.
- Write **modular code**: small functions, single responsibility principle.
- Add **logging** (standard library `logging`) for production code; never use `print()` in libraries or applications.
- When dealing with resources (files, DB, network), use **context managers** (`with` statement).
- Document assumptions and pre/post-conditions in docstrings.
- Optimize only when needed: prefer clarity first, but use generators/`itertools` for large data.

## Output format
- Show the full `.py` file with imports at the top.
- If multiple files are needed (e.g., module + tests), output them as **separate blocks with filenames**.
- Include a **usage example** of the main function/class at the end.
- Include **unit tests** using `pytest` that cover:
  - Normal cases
  - Edge cases (empty, None, invalid input)
  - Error handling (exceptions)

## Code style
- Naming: `snake_case` for variables/functions, `PascalCase` for classes, `UPPER_CASE` for constants.
- Use f-strings for formatting.
- Keep functions under ~50 lines where possible.
- Add **docstrings** (`"""Google-style or NumPy-style"""`) for public functions/classes.

## When generating or refactoring code
- First explain **reasoning** (design choices, trade-offs, optimizations) in 1–2 short paragraphs.
- Then provide the **final code solution**.

## Nullability

* **Never** use empty strings to represent "no value". Use `None` instead.
* **Never** use the number zero to represent "no value". Use `None` instead.
* **Never** use `False` to represent "no value". Use `None` instead.

There are typically three options when definining a primitive value's type. The examples below are for Pydantic model fields, but this also applies to function parameters and return types.

### Required and non-nullable

```py
class MyModel(FrozenBaseModel):
    name: str  # must be provided, cannot be None
```

### Required but nullable

```py
class MyModel(FrozenBaseModel):
    name: str | None  # must be provided, but can be None
```

ℹ️ This is useful in scenarios where you want the consumer of your class / service / library to make a conscious choice about a field's value, even if that value can be `None`. For example, when updating a resource, you may want to distinguish between "do not update this field" (omitted) vs "update this field to be null" (explicitly set to `None`).

### Optional and nullable

```py
class MyModel(FrozenBaseModel):
    name: str | None = None  # can be omitted, and defaults to None
```

## Environment variables and settings

Use [`pydantic-settings`](https://docs.pydantic.dev/latest/concepts/pydantic_settings) for managing environment variables and other configs. **Do not use `os.environ` directly.**

Each application should have a top-level `settings.py` file:

**`src/settings.py`**

```py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str

settings = Settings()
```

Then, anywhere in your code that needs access to these settings, import the `settings` instance:

```py
from src.settings import settings

def connect_to_database():
    db_url = settings.DATABASE_URL
    ...
```
