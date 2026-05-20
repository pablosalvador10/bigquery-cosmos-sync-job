---
applyTo: "**/py/**"
---

# Pydantic model conventions

## Overview

Prefer a project-local `FrozenBaseModel` — a Pydantic `BaseModel` with `frozen=True` — as the base class for value objects and domain models. Frozen models are immutable after construction, which prevents accidental mutation and keeps data flow easy to reason about.

```python
from pydantic import BaseModel, ConfigDict


class FrozenBaseModel(BaseModel):
    model_config = ConfigDict(frozen=True)
```

Drop this in a shared `models/base.py` module per app or library and import from there.

## Usage

### `FrozenBaseModel`

```python
from app.models.base import FrozenBaseModel

class User(FrozenBaseModel):
    name: str
    age: int
    email: str | None = None

# Create a user instance
user = User(name="Alice", age=30, email="alice@example.com")

# This works fine
print(user.name)  # "Alice"
print(user.age)   # 30

# This will raise a ValidationError because the model is frozen
try:
    user.name = "Bob"  # ❌ ValidationError: Instance is frozen
except ValidationError as e:
    print(f"Error: {e}")
```

### `model_config` Inheritance

If a child class inheriting from `FrozenBaseModel` also specifies a `model_config`, the config from the child class will be _merged_ with the parent's:

```py
from pydantic import BaseModel
from pydantic import ConfigDict


class FrozenBaseModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class Child(FrozenBaseModel):
    model_config = ConfigDict(str_to_lower=True)

    x: str


child = Child(x='FOO')
print(child.model_dump())
#> {'x': 'foo'}
print(child.model_config)
#> {'frozen': True, 'str_to_lower': True}
```

## `dict_adapter` decorator

A `dict_adapter` decorator pattern is useful for converting dictionary inputs into Pydantic model instances automatically. This keeps function signatures strongly typed when integrating with third-party libraries or frameworks that pass dictionaries (e.g., serverless function bindings, dynamic providers, event handlers).

```python
from app.models.base import FrozenBaseModel
from app.models.dict_adapter import dict_adapter

class InputModel(FrozenBaseModel):
    x: float
    y: float

class OutputModel(FrozenBaseModel):
    sum: float
    product: float

@dict_adapter
def compute(input_model: InputModel) -> OutputModel:
    return OutputModel(
        sum=input_model.x + input_model.y,
        product=input_model.x * input_model.y
    )

assert compute({"x": 3.0, "y": 4.0}) == {"sum": 7.0, "product": 12.0}
```
