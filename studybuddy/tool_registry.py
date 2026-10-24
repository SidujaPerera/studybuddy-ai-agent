"""ToolRegistry: the list of tools the agent is allowed to use, and a safe way to run them.

The agent never calls a tool function directly. It asks the registry, which:
  1. checks the tool name is registered,
  2. checks the arguments against the tool's schema,
  3. runs the function and catches any error,
  4. returns a JSON-serializable dict: {"ok": True, "result": ...} or {"ok": False, "error": "..."}.
"""

import inspect
import json

# JSON Schema type name -> Python types that are accepted for it.
JSON_TYPES = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


class ToolRegistry:
    def __init__(self):
        # name -> {"function": callable, "schema": Ollama tool schema}
        self._tools = {}

    def register(self, name, function, description, parameters):
        """Add a tool. `parameters` is a JSON Schema object describing its arguments.

        Raises ValueError straight away if the tool does not match its schema,
        so mistakes are found when the program starts, not in the middle of a chat.
        """
        if not name.isidentifier():
            raise ValueError(f"Tool name '{name}' must be a valid Python-style name.")
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered.")
        if not callable(function):
            raise ValueError(f"Tool '{name}': function is not callable.")
        if parameters.get("type") != "object" or "properties" not in parameters:
            raise ValueError(f"Tool '{name}': parameters must be {{'type': 'object', 'properties': {{...}}}}.")

        properties = parameters["properties"]
        required = parameters.get("required", [])
        for param in required:
            if param not in properties:
                raise ValueError(f"Tool '{name}': required parameter '{param}' is not in properties.")
        _check_function_matches_schema(name, function, properties, required)

        self._tools[name] = {
            "function": function,
            "schema": {
                "type": "function",
                "function": {"name": name, "description": description, "parameters": parameters},
            },
        }

    def names(self):
        """Return the names of all registered tools."""
        return list(self._tools)

    def description(self, name):
        """Return the description of one registered tool."""
        return self._tools[name]["schema"]["function"]["description"]

    def schemas(self):
        """Return all tool schemas in the format ollama.chat(tools=...) expects."""
        return [tool["schema"] for tool in self._tools.values()]

    def execute(self, name, arguments):
        """Run a registered tool safely. Never raises; problems come back as {"ok": False, ...}."""
        if name not in self._tools:
            available = ", ".join(self._tools) or "none"
            return {"ok": False, "error": f"Unknown tool '{name}'. Available tools: {available}."}

        tool = self._tools[name]
        parameters = tool["schema"]["function"]["parameters"]
        try:
            clean_arguments = _validate_arguments(arguments, parameters)
        except ValueError as error:
            return {"ok": False, "error": f"Invalid arguments for '{name}': {error}"}

        try:
            result = tool["function"](**clean_arguments)
        except Exception as error:
            return {"ok": False, "error": f"Tool '{name}' failed: {type(error).__name__}: {error}"}

        return {"ok": True, "result": _make_json_safe(result)}


def _check_function_matches_schema(name, function, properties, required):
    """Make sure the Python function accepts exactly the parameters the schema describes."""
    signature = inspect.signature(function)
    accepts_any_keyword = any(p.kind == p.VAR_KEYWORD for p in signature.parameters.values())

    for param in properties:
        if param not in signature.parameters and not accepts_any_keyword:
            raise ValueError(f"Tool '{name}': schema parameter '{param}' is not a parameter of the function.")

    try:
        signature.bind(**{param: None for param in required})
    except TypeError as error:
        raise ValueError(
            f"Tool '{name}': the function has required parameters missing from the schema's 'required' list ({error})."
        ) from None


def _validate_arguments(arguments, parameters):
    """Check the model's arguments against the schema. Returns a cleaned copy or raises ValueError."""
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be a JSON object.")

    properties = parameters["properties"]
    required = parameters.get("required", [])

    unknown = [key for key in arguments if key not in properties]
    if unknown:
        raise ValueError(f"unknown parameter(s) {unknown}. Allowed: {list(properties)}.")

    missing = [key for key in required if arguments.get(key) in (None, "")]
    if missing:
        raise ValueError(f"missing required parameter(s) {missing}.")

    clean = {}
    for key, value in arguments.items():
        if value is None:
            continue  # treat null as "not given" so the function's default is used
        rules = properties[key]
        value = _convert_type(key, value, rules.get("type"))
        if "enum" in rules and value not in rules["enum"]:
            raise ValueError(f"'{key}' must be one of {rules['enum']}, got {value!r}.")
        clean[key] = value
    return clean


def _convert_type(key, value, expected_type):
    """Check a value has the expected JSON type. Small models often send numbers as text,
    so "5" is accepted for an integer and "2.5" for a number."""
    if expected_type is None or expected_type not in JSON_TYPES:
        return value

    if expected_type in ("integer", "number") and isinstance(value, str):
        try:
            value = int(value) if expected_type == "integer" else float(value)
        except ValueError:
            raise ValueError(f"'{key}' must be a {expected_type}, got {value!r}.") from None

    # bool is a subclass of int in Python, so reject it explicitly for numbers.
    if isinstance(value, bool) and expected_type != "boolean":
        raise ValueError(f"'{key}' must be a {expected_type}, got a boolean.")
    if not isinstance(value, JSON_TYPES[expected_type]):
        raise ValueError(f"'{key}' must be a {expected_type}, got {type(value).__name__}.")
    return value


def _make_json_safe(result):
    """Return the result unchanged if it can be turned into JSON, otherwise as text."""
    try:
        json.dumps(result)
        return result
    except (TypeError, ValueError):
        return str(result)
