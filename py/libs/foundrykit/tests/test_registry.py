from foundrykit.tools import ToolRegistry


def test_register_keeps_function_callable() -> None:
    registry = ToolRegistry()

    @registry.register
    def example(name: str) -> str:
        return f"hello {name}"

    assert example("world") == "hello world"
