"""Checks the model's final answer for claims that an action was completed
(study session scheduled, quiz saved, score recorded) and compares them with the
tool calls that really succeeded while answering the current message.

This check is deliberately conservative:
  - it only looks for clear "it is done" phrases, such as "I've scheduled ..." or
    "your session has been scheduled",
  - it skips sentences that are conditional or negative ("if the session is scheduled",
    "it was not scheduled"), so explanations like "you can schedule ..." are not flagged,
  - it never deletes text; it adds a clear warning to the answer instead.

Limitation: it is based on wording patterns, so an unusual phrasing ("All set for
Tuesday!") may not be noticed. The system prompt rules are the first line of defence.
"""

import re

# Words that make a sentence conditional or negative, so it is not a completion claim.
SKIP_WORDS = re.compile(
    r"\b(if|once|when|whenever|unless|until|not|never|cannot|unable|failed)\b|n['’]t\b",
    re.IGNORECASE,
)

I_DID = r"\bi(?:['’]ve|\s+have)?\s+(?:just\s+|successfully\s+|now\s+)?"
IT_WAS = r"(?:has been|have been|was|were|is now)\s+(?:successfully\s+|now\s+)?"
IT_IS = r"(?:has been|have been|was|were|is now|is|are)\s+(?:successfully\s+|now\s+)?"

CLAIMS = [
    {
        "label": "a study session was scheduled",
        "tool": "schedule_study_session",
        "action": None,
        "patterns": [
            I_DID + r"(?:scheduled|booked|recorded|set up|added|created)\b[^.!?\n]*\bsession",
            r"\bsession\b[^.!?\n]{0,80}?\b" + IT_IS + r"(?:scheduled|booked|recorded|confirmed|saved|set up|created)\b",
            r"\bsession\s+(?:is\s+)?confirmed\b",
        ],
    },
    {
        "label": "a quiz was saved",
        "tool": "quiz_tracker",
        "action": "save_quiz",
        "patterns": [
            I_DID + r"(?:saved|created|stored|added)\b[^.!?\n]*\bquiz",
            r"\bquiz\b[^.!?\n]{0,80}?\b" + IT_WAS + r"(?:saved|created|stored|added)\b",
        ],
    },
    {
        "label": "a quiz score was recorded",
        "tool": "quiz_tracker",
        "action": "log_score",
        "patterns": [
            I_DID + r"(?:logged|recorded|saved)\b[^.!?\n]*\bscores?\b",
            r"\bscores?\b[^.!?\n]{0,80}?\b" + IT_WAS + r"(?:logged|recorded|saved)\b",
        ],
    },
]
for _claim in CLAIMS:
    _claim["patterns"] = [re.compile(p, re.IGNORECASE) for p in _claim["patterns"]]

DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
QUIZ_ID = re.compile(r"\bquiz[\s_]*(?:id|number|#)\s*[:#]?\s*(\d+)", re.IGNORECASE)
SESSION_ID = re.compile(r"\bsession[\s_]*(?:id|number|#)\s*[:#]?\s*(\d+)", re.IGNORECASE)


def find_unverified_claims(answer, tool_calls):
    """Return a list of problems (empty if every completion claim is backed by a successful tool call).
    `tool_calls` is the agent's list of tool calls made for the current message."""
    problems = []
    for sentence in re.split(r"[.!?\n]+", answer):
        if SKIP_WORDS.search(sentence):
            continue
        for claim in CLAIMS:
            if not any(pattern.search(sentence) for pattern in claim["patterns"]):
                continue
            results = _successful_results(claim, tool_calls)
            if not results:
                problems.append(f"the answer says {claim['label']}, but no successful "
                                f"{_tool_label(claim)} call happened for this message")
                continue
            problems += _check_details(claim, sentence, results)
    return list(dict.fromkeys(problems))  # remove duplicates, keep order


def add_unverified_warning(answer, problems):
    """Append a clear warning listing the claims that could not be verified."""
    lines = "\n".join(f"- {problem}." for problem in problems)
    return (
        f"{answer}\n\n"
        "[Study Buddy check] Part of this answer could not be verified:\n"
        f"{lines}\n"
        "That action was NOT completed. Please ask again if you want it done."
    )


def _successful_results(claim, tool_calls):
    """The results of successful tool calls that would prove this claim."""
    results = []
    for call in tool_calls:
        if call["name"] != claim["tool"] or not call["result"].get("ok"):
            continue
        if claim["action"] and call["arguments"].get("action") != claim["action"]:
            continue
        if call["result"].get("status") != "success":
            continue
        results.append(call["result"].get("result") or {})
    return results


def _check_details(claim, sentence, results):
    """Dates and IDs mentioned in a claim must match what the tool really returned."""
    problems = []
    if claim["tool"] == "schedule_study_session":
        sessions = [r.get("session", {}) for r in results if isinstance(r, dict)]
        real_dates = {s.get("date") for s in sessions}
        real_ids = {str(s.get("session_id")) for s in sessions}
        for day in DATE.findall(sentence):
            if day not in real_dates:
                problems.append(f"the answer gives the session date {day}, but the session was saved for "
                                f"{', '.join(sorted(d for d in real_dates if d)) or 'another date'}")
        for session_id in SESSION_ID.findall(sentence):
            if session_id not in real_ids:
                problems.append(f"the answer mentions session ID {session_id}, which no tool returned")
    else:
        real_ids = {str(r.get("quiz_id")) for r in results if isinstance(r, dict)}
        for quiz_id in QUIZ_ID.findall(sentence):
            if quiz_id not in real_ids:
                problems.append(f"the answer mentions quiz ID {quiz_id}, which no tool returned")
    return problems


def _tool_label(claim):
    if claim["action"]:
        return f"{claim['tool']} ({claim['action']})"
    return claim["tool"]
