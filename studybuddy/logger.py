"""Logging for StudyBuddy: writes a readable trace of model calls and tool calls to logs/.

Privacy: the student's questions and the model's answers are NOT logged, only their
length. Tool arguments and results are logged (they are needed to trace tool calls),
but long values are shortened, and secrets and student identifiers are hidden.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
MAX_LOGGED_CHARS = 300
# Dict keys containing any of these words have their values replaced by *** in the log.
SECRET_KEY_WORDS = ("password", "passwd", "secret", "token", "api_key", "apikey", "authorization")
PERSONAL_KEY_WORDS = ("student", "email", "phone")

logger = logging.getLogger("studybuddy")


def setup_logging(log_dir=LOG_DIR):
    """Start writing to logs/studybuddy_<date>.log (one file per day). Returns the file path."""
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"studybuddy_{datetime.now():%Y-%m-%d}.log"

    already_added = any(
        isinstance(h, logging.FileHandler) and Path(h.baseFilename) == log_file.resolve()
        for h in logger.handlers
    )
    if not already_added:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", "%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return log_file


# ---- One small function per kind of event, so agent.py stays easy to read ----

def log_session_start(model, tool_names, using_mocks, mock_tool_names=()):
    tools = ", ".join(tool_names) or "none"
    mode = "TEMPORARY MOCK tools" if using_mocks else "real tools"
    extra = f" | MOCK mode: {', '.join(mock_tool_names)}" if mock_tool_names and not using_mocks else ""
    logger.info("##### Session started | model=%s | %s: %s%s", model, mode, tools, extra)


def log_question(text):
    logger.info("===== New question (%d characters, text not logged) =====", len(text))


def log_model_call(step, max_steps, tools_offered, seconds):
    logger.info("step %d/%d | model replied in %.1fs | tools offered: %s", step, max_steps, seconds, tools_offered)


def log_tool_call(step, name, arguments, result, is_mock, is_registered):
    label = "[MOCK]" if is_mock else "[REAL]" if is_registered else "[UNREGISTERED]"
    source = result_source(result)
    if source:
        label += f" source={source}"
    logger.info("step %d | TOOL REQUEST %s %s | args=%s", step, name, label, summarize(arguments))
    if not result["ok"]:
        logger.warning("step %d | TOOL ERROR   %s %s | error=%s", step, name, label, summarize(result["error"]))
    elif result.get("status") == "not_found":
        logger.info("step %d | TOOL NO MATCH %s %s | result=%s", step, name, label, summarize(result["result"]))
    else:
        logger.info("step %d | TOOL OK      %s %s | result=%s", step, name, label, summarize(result["result"]))


def log_final_answer(step, answer):
    logger.info("step %d | FINAL ANSWER (%d characters, text not logged)", step, len(answer))


def log_max_steps(max_steps):
    logger.warning("MAX STEPS reached (%d). Last model call made without tools to force an answer.", max_steps)


def log_problem(step, message):
    logger.warning("step %d | PROBLEM: %s", step, message)


def log_model_error(step, error):
    logger.error("step %d | MODEL ERROR %s: %s", step, type(error).__name__, summarize(str(error)))


def log_turn_rolled_back(removed_messages):
    logger.warning("Turn rolled back: %d unfinished message(s) removed from history.", removed_messages)


def log_unexpected_error(error):
    logger.exception("UNEXPECTED ERROR %s", type(error).__name__)


# ---- Helpers ----

def result_source(result):
    """Return the 'source' label (e.g. live or mock) from a tool's result, if it has one."""
    inner = result.get("result")
    if isinstance(inner, dict) and isinstance(inner.get("source"), str):
        return inner["source"]
    return None


def summarize(value):
    """Turn a value into short, single-line JSON text with secrets and student identifiers hidden."""
    text = json.dumps(hide_sensitive(value), ensure_ascii=False, default=str)
    if len(text) > MAX_LOGGED_CHARS:
        text = text[:MAX_LOGGED_CHARS] + f"... [{len(text) - MAX_LOGGED_CHARS} more characters]"
    return text


def hide_sensitive(value):
    """Return a copy of value where dict entries with secret or personal keys are replaced by ***."""
    hidden_words = SECRET_KEY_WORDS + PERSONAL_KEY_WORDS
    if isinstance(value, dict):
        return {
            key: "***" if any(word in str(key).lower() for word in hidden_words) else hide_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [hide_sensitive(item) for item in value]
    return value
