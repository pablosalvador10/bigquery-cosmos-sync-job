"""Parameterized SQL query helpers.

The Azure Cosmos SDK accepts SQL strings + a parameter list shaped like
``[{"name": "@foo", "value": ...}]``. Hand-building these is error prone, so
``QueryBuilder`` enforces:

* parameter names are auto-prefixed with ``@``
* values must be JSON-serializable scalars or lists
* duplicate parameter names raise immediately
"""

from dataclasses import dataclass, field
from typing import Any

_AllowedScalar = str | int | float | bool | None


def _validate_value(value: Any) -> Any:
    """Reject obviously-wrong parameter values (objects, sets, bytes, ...)."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_validate_value(v) for v in value]
    msg = f"Unsupported query parameter value type: {type(value).__name__}"
    raise TypeError(msg)


@dataclass
class QueryBuilder:
    """Build a ``(query, parameters)`` pair safely.

    Example::

        qb = QueryBuilder(
            "SELECT * FROM c WHERE c.hackathonId = @hid AND c.status = @status"
        )
        qb.bind("hid", "fde-fy26").bind("status", "submitted")
        sql, params = qb.build()
    """

    sql: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def bind(self, name: str, value: Any) -> "QueryBuilder":
        """Bind a value to a named parameter. Names are normalised to start with ``@``."""
        if not name:
            msg = "Parameter name must be a non-empty string"
            raise ValueError(msg)
        key = name if name.startswith("@") else f"@{name}"
        if key in self.parameters:
            msg = f"Parameter {key} already bound"
            raise ValueError(msg)
        self.parameters[key] = _validate_value(value)
        return self

    def bind_many(self, **kwargs: Any) -> "QueryBuilder":
        for k, v in kwargs.items():
            self.bind(k, v)
        return self

    def build(self) -> tuple[str, list[dict[str, Any]]]:
        if not self.sql.strip():
            msg = "SQL query must be non-empty"
            raise ValueError(msg)
        params = [{"name": k, "value": v} for k, v in self.parameters.items()]
        return self.sql, params


def normalize_parameters(
    parameters: dict[str, Any] | list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Coerce a dict or already-shaped list into the SDK parameter format."""
    if parameters is None:
        return []
    if isinstance(parameters, list):
        for entry in parameters:
            if not isinstance(entry, dict) or "name" not in entry or "value" not in entry:
                msg = f"Invalid parameter entry: {entry!r}"
                raise ValueError(msg)
        return list(parameters)
    out: list[dict[str, Any]] = []
    for k, v in parameters.items():
        key = k if k.startswith("@") else f"@{k}"
        out.append({"name": key, "value": _validate_value(v)})
    return out
