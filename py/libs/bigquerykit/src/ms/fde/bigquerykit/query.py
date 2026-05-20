"""Parameterized SQL query helpers for BigQuery.

BigQuery accepts standard SQL with ``@named`` placeholders plus a list of
``ScalarQueryParameter`` / ``ArrayQueryParameter`` objects. Hand-building these
is verbose and error prone, so ``QueryBuilder`` enforces:

* parameter names are auto-prefixed with ``@`` in the SQL string only — the
  parameter objects themselves use the bare name (per SDK convention).
* values are validated against a small allow-list of scalar / list types.
* duplicate parameter names raise immediately.
* type strings are inferred from Python types and can be overridden.
"""

from dataclasses import dataclass, field
from typing import Any


def _infer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "BOOL"
    if isinstance(value, int):
        return "INT64"
    if isinstance(value, float):
        return "FLOAT64"
    if isinstance(value, str):
        return "STRING"
    msg = f"Cannot infer BigQuery type for value of type {type(value).__name__}"
    raise TypeError(msg)


def _validate_scalar(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    # Accept datetime-like via str() for safety only when caller cast already.
    msg = f"Unsupported query parameter scalar type: {type(value).__name__}"
    raise TypeError(msg)


@dataclass
class _BoundParameter:
    name: str
    value: Any
    type_: str
    is_array: bool


@dataclass
class QueryBuilder:
    """Build a ``(sql, parameters)`` pair safely.

    Example::

        qb = QueryBuilder(
            "SELECT * FROM `proj.ds.learners` "
            "WHERE country = @country AND updated_at >= @since"
        )
        qb.bind("country", "US").bind("since", "2026-05-01T00:00:00Z")
        sql, params = qb.build()
    """

    sql: str
    _parameters: dict[str, _BoundParameter] = field(default_factory=dict)

    def bind(self, name: str, value: Any, *, type_: str | None = None) -> "QueryBuilder":
        """Bind a scalar value to a named parameter.

        ``type_`` overrides type inference (e.g. pass ``"TIMESTAMP"`` for an
        ISO-8601 string).
        """
        clean = self._normalize_name(name)
        if clean in self._parameters:
            msg = f"Parameter @{clean} already bound"
            raise ValueError(msg)
        v = _validate_scalar(value)
        t = type_ or _infer_type(v)
        self._parameters[clean] = _BoundParameter(clean, v, t, is_array=False)
        return self

    def bind_array(self, name: str, values: list[Any], *, type_: str | None = None) -> "QueryBuilder":
        """Bind a list of scalar values as a BigQuery ``ARRAY`` parameter."""
        clean = self._normalize_name(name)
        if clean in self._parameters:
            msg = f"Parameter @{clean} already bound"
            raise ValueError(msg)
        if not values:
            if type_ is None:
                msg = "type_ is required when binding an empty array"
                raise ValueError(msg)
            t = type_
        else:
            t = type_ or _infer_type(values[0])
        coerced = [_validate_scalar(v) for v in values]
        self._parameters[clean] = _BoundParameter(clean, coerced, t, is_array=True)
        return self

    def bind_many(self, **kwargs: Any) -> "QueryBuilder":
        for k, v in kwargs.items():
            self.bind(k, v)
        return self

    def build(self) -> tuple[str, list[Any]]:
        if not self.sql.strip():
            msg = "SQL query must be non-empty"
            raise ValueError(msg)
        return self.sql, to_query_parameters(self._parameters)

    @staticmethod
    def _normalize_name(name: str) -> str:
        if not name:
            msg = "Parameter name must be a non-empty string"
            raise ValueError(msg)
        return name[1:] if name.startswith("@") else name


def to_query_parameters(bound: dict[str, _BoundParameter]) -> list[Any]:
    """Materialize bound parameters into google-cloud-bigquery objects."""
    if not bound:
        return []
    from google.cloud.bigquery import (
        ArrayQueryParameter,
        ScalarQueryParameter,
    )

    out: list[Any] = []
    for p in bound.values():
        if p.is_array:
            out.append(ArrayQueryParameter(p.name, p.type_, p.value))
        else:
            out.append(ScalarQueryParameter(p.name, p.type_, p.value))
    return out
