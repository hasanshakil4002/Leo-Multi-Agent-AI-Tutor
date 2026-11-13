from crewai.tools import tool


@tool("calculator")
def calculator(expression: str) -> str:
    """
    Evaluate a basic arithmetic expression, e.g. '12 * (3 + 4) / 2'.
    Only supports numbers and + - * / ( ) ** operators. Use this whenever a
    lesson or quiz question needs a verified numeric answer.
    """
    allowed = set("0123456789+-*/(). \t")
    if not set(expression) <= allowed:
        return "Error: expression contains unsupported characters."
    try:
        # restricted eval: no builtins, only arithmetic characters were allowed above
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as exc:  # noqa: BLE001
        return f"Error evaluating expression: {exc}"


ALL_TOOLS = [calculator]
