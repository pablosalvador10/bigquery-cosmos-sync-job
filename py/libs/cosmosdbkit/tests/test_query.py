"""Tests for QueryBuilder and parameter normalization."""

import pytest

from ms.fde.cosmosdbkit.query import QueryBuilder, normalize_parameters


def test_build_basic_query() -> None:
    qb = QueryBuilder("SELECT * FROM c WHERE c.id = @id").bind("id", "x")
    sql, params = qb.build()
    assert sql == "SELECT * FROM c WHERE c.id = @id"
    assert params == [{"name": "@id", "value": "x"}]


def test_bind_auto_prefixes_at_sign() -> None:
    qb = QueryBuilder("SELECT * FROM c WHERE c.id = @id").bind("id", "x")
    _, params = qb.build()
    assert params[0]["name"] == "@id"


def test_bind_accepts_pre_prefixed_name() -> None:
    qb = QueryBuilder("SELECT * FROM c").bind("@id", "x")
    _, params = qb.build()
    assert params[0]["name"] == "@id"


def test_bind_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        QueryBuilder("SELECT * FROM c").bind("", "x")


def test_bind_rejects_duplicate_names() -> None:
    qb = QueryBuilder("SELECT * FROM c").bind("id", "x")
    with pytest.raises(ValueError, match="already bound"):
        qb.bind("id", "y")


def test_bind_many_chains() -> None:
    qb = QueryBuilder("SELECT * FROM c").bind_many(a=1, b="2", c=True)
    _, params = qb.build()
    names = [p["name"] for p in params]
    assert names == ["@a", "@b", "@c"]


def test_bind_supports_string_int_float_bool_none() -> None:
    qb = QueryBuilder("SELECT * FROM c")
    qb.bind("s", "x").bind("i", 1).bind("f", 1.5).bind("b", True).bind("n", None)
    _, params = qb.build()
    assert {p["name"] for p in params} == {"@s", "@i", "@f", "@b", "@n"}


def test_bind_supports_list_value() -> None:
    qb = QueryBuilder("SELECT * FROM c").bind("ids", ["a", "b", "c"])
    _, params = qb.build()
    assert params[0]["value"] == ["a", "b", "c"]


def test_bind_rejects_unsupported_type() -> None:
    with pytest.raises(TypeError, match="Unsupported"):
        QueryBuilder("SELECT * FROM c").bind("x", {"nested": 1})


def test_bind_rejects_bytes() -> None:
    with pytest.raises(TypeError):
        QueryBuilder("SELECT * FROM c").bind("x", b"raw")


def test_bind_rejects_set() -> None:
    with pytest.raises(TypeError):
        QueryBuilder("SELECT * FROM c").bind("x", {1, 2})


def test_build_rejects_empty_sql() -> None:
    with pytest.raises(ValueError):
        QueryBuilder("   ").build()


def test_build_returns_tuple_of_str_and_list() -> None:
    qb = QueryBuilder("SELECT * FROM c")
    sql, params = qb.build()
    assert isinstance(sql, str)
    assert isinstance(params, list)


def test_normalize_none_returns_empty_list() -> None:
    assert normalize_parameters(None) == []


def test_normalize_dict_to_list() -> None:
    out = normalize_parameters({"id": "x", "n": 1})
    assert {(p["name"], p["value"]) for p in out} == {("@id", "x"), ("@n", 1)}


def test_normalize_passthrough_for_correctly_shaped_list() -> None:
    src = [{"name": "@id", "value": "x"}]
    out = normalize_parameters(src)
    assert out == src
    assert out is not src  # makes a copy


def test_normalize_validates_list_entries() -> None:
    with pytest.raises(ValueError):
        normalize_parameters([{"oops": 1}])


def test_normalize_validates_value_types_in_dict() -> None:
    with pytest.raises(TypeError):
        normalize_parameters({"x": object()})


def test_normalize_dict_preserves_at_prefix() -> None:
    out = normalize_parameters({"@id": "x"})
    assert out == [{"name": "@id", "value": "x"}]


def test_querybuilder_initial_parameters_kwarg_default() -> None:
    qb = QueryBuilder("SELECT 1")
    assert qb.parameters == {}


def test_normalize_list_with_nested_list_value() -> None:
    out = normalize_parameters({"ids": ["a", "b"]})
    assert out == [{"name": "@ids", "value": ["a", "b"]}]
