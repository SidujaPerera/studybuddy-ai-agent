"""The ONE place where study tools are connected to the agent.

The model sees four tool names. Each one is connected to one of Mehansa's functions
in studybuddy/tools/ (see _real_tool_functions). agent.py never imports the tools itself.
Set USE_MOCK_TOOLS = True to go back to the temporary mock tools for offline testing.
"""

import functools

from studybuddy import config
from studybuddy.tool_registry import ToolRegistry

# True = temporary mock tools (fake data). False = Mehansa's real tools.
USE_MOCK_TOOLS = False

QUIZ_ACTIONS = ["save_quiz", "get_quiz", "submit_answer", "log_score", "get_scores"]

# What the model is told about each tool. Parameter names and types match Mehansa's functions.
TOOL_SCHEMAS = {
    "search_notes": {
        "description": "Search the student's saved study notes (.txt, .json and .md files) for a topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic or keyword to search the notes for."},
            },
            "required": ["topic"],
        },
    },
    "quiz_tracker": {
        "description": "Save quizzes, show a saved quiz, check a student's answer, log quiz scores and list scores.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": QUIZ_ACTIONS, "description": "What to do."},
                # Ollama does not pass nested schemas to the model, so the fields are described in text.
                "data": {
                    "type": "object",
                    "description": (
                        "Fields for the chosen action. "
                        "save_quiz: topic (text), questions (list of {question, answer, optional options "
                        "(list of text), optional explanation}). "
                        "get_quiz: quiz_id (number returned by save_quiz). "
                        "submit_answer: quiz_id, student, question_index (0 = first question), answer. "
                        "log_score: quiz_id, student, optional score and total "
                        "(without a score it is calculated from submitted answers). "
                        "get_scores: optional student."
                    ),
                },
            },
            "required": ["action", "data"],
        },
    },
    "wikipedia_search": {
        "description": (
            "Look up educational information on Wikipedia. Results include source: "
            "'live' is real Wikipedia content, 'mock' is placeholder data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Topic or question to look up."},
            },
            "required": ["query"],
        },
    },
    "schedule_study_session": {
        "description": (
            "Record a planned study session and return a confirmation. "
            "This does not create calendar invites or send notifications."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format, today or later."},
                "duration_minutes": {"type": "integer", "description": "Length of the session in minutes (5 to 720)."},
                "topic": {"type": "string", "description": "What the student will study."},
            },
            "required": ["date", "duration_minutes", "topic"],
        },
    },
}

# The fields allowed in quiz_tracker's "data" for each action: name -> expected type.
QUIZ_DATA_RULES = {
    "save_quiz": {"required": {"topic": "text", "questions": "list"}, "optional": {}},
    "get_quiz": {"required": {"quiz_id": "whole number"}, "optional": {}},
    "submit_answer": {
        "required": {"quiz_id": "whole number", "student": "text", "question_index": "whole number", "answer": "text"},
        "optional": {},
    },
    "log_score": {
        "required": {"quiz_id": "whole number", "student": "text"},
        "optional": {"score": "whole number", "total": "whole number", "answers": "list"},
    },
    "get_scores": {"required": {}, "optional": {"student": "text"}},
}
QUESTION_FIELDS = {"question": "text", "answer": "text", "options": "list of text", "explanation": "text"}


def _has_type(value, expected):
    if expected == "text":
        return isinstance(value, str) and bool(value.strip())
    if expected == "whole number":
        if isinstance(value, bool):
            return False
        if isinstance(value, int):
            return True
        return isinstance(value, str) and value.strip().lstrip("-").isdigit()
    if expected == "list":
        return isinstance(value, list)
    if expected == "list of text":
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    return True


def check_quiz_data(arguments):
    """Check quiz_tracker's nested "data" for the chosen action.
    Returns an error message for the model, or None if the data is fine."""
    action = arguments["action"]
    data = arguments["data"]
    rules = QUIZ_DATA_RULES[action]
    allowed = {**rules["required"], **rules["optional"]}
    expected_fields = ", ".join(f"{field} ({kind})" for field, kind in allowed.items()) or "no fields"

    unknown = [key for key in data if key not in allowed]
    if unknown:
        return f"{action} does not accept data field(s) {unknown}. Allowed: {expected_fields}."

    missing = [field for field in rules["required"] if data.get(field) is None]
    if missing:
        return f"{action} needs data field(s) {missing}. Expected: {expected_fields}."

    for field, kind in allowed.items():
        if data.get(field) is not None and not _has_type(data[field], kind):
            return f"{action}: data.{field} must be {kind}."

    if action == "save_quiz":
        if not data["questions"]:
            return "save_quiz needs at least one question."
        for number, question in enumerate(data["questions"]):
            if not isinstance(question, dict):
                return f"save_quiz: question {number} must be an object like {{question, answer}}."
            unknown = [key for key in question if key not in QUESTION_FIELDS]
            if unknown:
                return f"save_quiz: question {number} has unknown field(s) {unknown}. Allowed: {list(QUESTION_FIELDS)}."
            for field in ("question", "answer"):
                if not _has_type(question.get(field), "text"):
                    return f"save_quiz: question {number} needs '{field}' text."
            for field in ("options", "explanation"):
                if question.get(field) is not None and not _has_type(question[field], QUESTION_FIELDS[field]):
                    return f"save_quiz: question {number} field '{field}' must be {QUESTION_FIELDS[field]}."
    return None


EXTRA_CHECKS = {"quiz_tracker": check_quiz_data}


def _mock_tool_functions():
    from studybuddy import mock_tools

    return {
        "search_notes": mock_tools.mock_search_notes,
        "quiz_tracker": mock_tools.mock_quiz_tracker,
        "wikipedia_search": mock_tools.mock_wikipedia_search,
        "schedule_study_session": mock_tools.mock_schedule_study_session,
    }


def _real_tool_functions():
    from studybuddy.tools.notes import notes_search
    from studybuddy.tools.quiz import quiz_manager
    from studybuddy.tools.scheduler import schedule_study_sessions
    from studybuddy.tools.wikipedia import wikipedia_search

    return {
        "search_notes": notes_search,
        "quiz_tracker": quiz_manager,
        # use_mock is fixed here from config, so the model can never switch it on or off.
        "wikipedia_search": functools.partial(wikipedia_search, use_mock=config.WIKIPEDIA_USE_MOCK),
        "schedule_study_session": schedule_study_sessions,
    }


def is_mock_tool(name):
    """True if this tool currently returns mock (placeholder) data."""
    return USE_MOCK_TOOLS or (name == "wikipedia_search" and config.WIKIPEDIA_USE_MOCK)


def build_registry():
    """Create a ToolRegistry containing the four study tools."""
    functions = _mock_tool_functions() if USE_MOCK_TOOLS else _real_tool_functions()

    registry = ToolRegistry()
    for name, schema in TOOL_SCHEMAS.items():
        registry.register(name, functions[name], schema["description"], schema["parameters"],
                          is_mock=is_mock_tool(name), extra_check=EXTRA_CHECKS.get(name))
    return registry
