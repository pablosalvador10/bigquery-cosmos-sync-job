import pytest

from ms.fde.bigquerykit.query import QueryBuilder, to_query_parameters


def test_builds_sql_and_parameters() -> None:
    qb = QueryBuilder("SELECT * FROM `p.d.t` WHERE country = @country AND age >= @min_age")
    qb.bind("country", "US").bind("min_age", 18)
    sql, params = qb.build()
    assert "@country" in sql and "@min_age" in sql
    by_name = {p.name: p for p in params}
    assert by_name["country"].type_ == "STRING"
    assert by_name["country"].value == "US"
    assert by_name["min_age"].type_ == "INT64"
    assert by_name["min_age"].value == 18


def test_duplicate_param_rejected() -> None:
    qb = QueryBuilder("SELECT 1").bind("x", 1)
    with pytest.raises(ValueError, match="already bound"):
        qb.bind("x", 2)


def test_at_prefix_is_normalized() -> None:
    qb = QueryBuilder("SELECT 1").bind("@x", 1)
    _, params = qb.build()
    assert params[0].name == "x"


def test_array_binding() -> None:
    qb = QueryBuilder("SELECT * FROM `t` WHERE id IN UNNEST(@ids)")
    qb.bind_array("ids", ["a", "b", "c"])
    _, params = qb.build()
    assert params[0].name == "ids"
    assert params[0].array_type == "STRING"
    assert params[0].values == ["a", "b", "c"]


def test_empty_array_requires_explicit_type() -> None:
    qb = QueryBuilder("SELECT * FROM `t` WHERE id IN UNNEST(@ids)")
    with pytest.raises(ValueError, match="type_ is required"):
        qb.bind_array("ids", [])
    qb.bind_array("ids", [], type_="STRING")
    _, params = qb.build()
    assert params[0].array_type == "STRING"


def test_unsupported_value_type_rejected() -> None:
    qb = QueryBuilder("SELECT 1")
    with pytest.raises(TypeError):
        qb.bind("x", {"not": "allowed"})


def test_to_query_parameters_empty() -> None:
    assert to_query_parameters({}) == []
