import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

# Runtime quiz data is stored in the project folder, based on this file's location
# (not the terminal's current directory). parents[2] is <project>.
PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "study_buddy_data"
DATA_FILE = DATA_DIR / "quizzes_and_scores.json"

ACTIONS = ("save_quiz", "get_quiz", "submit_answer", "log_score", "get_scores")


def _error(message: str) -> dict:
    return {"status": "error", "message": message}


def _empty_database() -> dict:
    return {"next_quiz_id": 1, "quizzes": {}, "submissions": [], "scores": []}


def _load_data() -> dict:
    """Load saved quizzes and scores from the JSON file.

    Raises RuntimeError if the file cannot be read, so a damaged file is
    reported instead of being silently replaced with empty data."""
    if not DATA_FILE.exists():
        return _empty_database()

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, UnicodeError, ValueError):
        raise RuntimeError(
            f"Could not read quiz data in {DATA_FILE.name}. "
            "The file was left unchanged. Check or restore it."
        ) from None

    if not isinstance(data, dict) or not isinstance(data.get("quizzes", {}), dict):
        raise RuntimeError(
            f"Quiz data in {DATA_FILE.name} has an unexpected format. The file was left unchanged."
        )

    for key, default in _empty_database().items():
        data.setdefault(key, default)
    return data


def _save_data(data: dict) -> None:
    """Save quizzes and scores safely: write a temporary file first, then replace
    the old file, so a crash while saving cannot leave a half-written file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    handle, temp_path = tempfile.mkstemp(dir=DATA_DIR, prefix=DATA_FILE.name, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        os.replace(temp_path, DATA_FILE)
    except BaseException:
        Path(temp_path).unlink(missing_ok=True)
        raise


def _as_int(value):
    """Return value as an int (accepts 3 or "3"), or None if it is not a whole number."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _find_quiz(data: dict, quiz_id):
    """Find a quiz using its ID. Returns None if the ID is invalid or unknown."""
    quiz_id = _as_int(quiz_id)
    if quiz_id is None:
        return None
    return data["quizzes"].get(str(quiz_id))


def _quiz_not_found(quiz_id) -> dict:
    return _error(f"Quiz {quiz_id!r} not found. Use the quiz_id returned by save_quiz.")


def _valid_student(student) -> bool:
    return isinstance(student, str) and bool(student.strip())


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def quiz_manager(action: str, data: dict) -> dict:
    """Manage quizzes and student scores.

    Supported actions: save_quiz, get_quiz, submit_answer, log_score, get_scores"""

    if not isinstance(action, str) or action.strip() not in ACTIONS:
        return _error(f"Unknown action {action!r}. Use one of: {', '.join(ACTIONS)}.")

    if not isinstance(data, dict):
        return _error("Data must be a dictionary.")

    try:
        database = _load_data()
        action = action.strip()

        if action == "save_quiz":
            return _save_quiz(database, data)
        elif action == "get_quiz":
            return _get_quiz(database, data)
        elif action == "submit_answer":
            return _submit_answer(database, data)
        elif action == "log_score":
            return _log_score(database, data)
        else:
            return _get_scores(database, data)

    except (OSError, RuntimeError) as error:
        return _error(str(error))


# 1. SAVE QUIZ

def _save_quiz(database: dict, data: dict) -> dict:
    topic = data.get("topic")
    questions = data.get("questions")

    if not isinstance(topic, str) or not topic.strip():
        return _error("A valid topic is required.")

    if not isinstance(questions, list) or not questions:
        return _error("Questions must be a non-empty list.")

    # Validate every question and keep only the supported fields.
    clean_questions = []
    for number, question in enumerate(questions):
        if not isinstance(question, dict):
            return _error(f"Question {number} must be a dictionary.")

        text = question.get("question")
        if not isinstance(text, str) or not text.strip():
            return _error(f"Question {number} needs question text.")

        answer = question.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            return _error(f"Question {number} needs a correct answer.")

        clean_question = {"question": text.strip(), "answer": answer.strip()}

        options = question.get("options")
        if options is not None:
            if not isinstance(options, list) or not all(isinstance(option, str) for option in options):
                return _error(f"Options for question {number} must be a list of strings.")
            clean_question["options"] = options

        explanation = question.get("explanation")
        if explanation is not None:
            if not isinstance(explanation, str):
                return _error(f"Explanation for question {number} must be a string.")
            clean_question["explanation"] = explanation

        clean_questions.append(clean_question)

    # Never overwrite an existing quiz, even if next_quiz_id was edited by hand.
    quiz_id = _as_int(database["next_quiz_id"]) or 1
    while str(quiz_id) in database["quizzes"]:
        quiz_id += 1

    database["quizzes"][str(quiz_id)] = {
        "quiz_id": quiz_id,
        "topic": topic.strip(),
        "questions": clean_questions,
        "created_at": _now()
    }
    database["next_quiz_id"] = quiz_id + 1
    _save_data(database)

    return {
        "status": "success",
        "quiz_id": quiz_id,
        "topic": topic.strip(),
        "num_questions": len(clean_questions)
    }


# 2. GET QUIZ (HIDE ANSWERS AND EXPLANATIONS)

def _get_quiz(database: dict, data: dict) -> dict:
    quiz = _find_quiz(database, data.get("quiz_id"))
    if quiz is None:
        return _quiz_not_found(data.get("quiz_id"))

    public_questions = []
    for index, question in enumerate(quiz["questions"]):
        public_question = {"question_index": index, "question": question["question"]}
        if "options" in question:
            public_question["options"] = question["options"]
        public_questions.append(public_question)

    return {
        "status": "success",
        "quiz_id": quiz["quiz_id"],
        "topic": quiz["topic"],
        "questions": public_questions
    }


# 3. SUBMIT ANSWER

def _submit_answer(database: dict, data: dict) -> dict:
    quiz = _find_quiz(database, data.get("quiz_id"))
    if quiz is None:
        return _quiz_not_found(data.get("quiz_id"))

    student = data.get("student")
    question_index = _as_int(data.get("question_index"))
    student_answer = data.get("answer")

    if not _valid_student(student):
        return _error("A student name is required.")

    if question_index is None:
        return _error("question_index must be an integer (the first question is 0).")

    questions = quiz["questions"]
    if question_index < 0 or question_index >= len(questions):
        return _error(
            f"Question index is out of range. This quiz has questions 0 to {len(questions) - 1}."
        )

    if not isinstance(student_answer, str) or not student_answer.strip():
        return _error("Answer must be a non-empty string.")

    question = questions[question_index]
    correct_answer = question["answer"]
    is_correct = student_answer.strip().casefold() == correct_answer.strip().casefold()

    # Save the answer so log_score can calculate the score later.
    # A new answer to the same question replaces the student's previous one.
    student_key = student.strip().casefold()
    database["submissions"] = [
        item for item in database["submissions"]
        if not (
            item.get("quiz_id") == quiz["quiz_id"]
            and item.get("student", "").casefold() == student_key
            and item.get("question_index") == question_index
        )
    ]
    database["submissions"].append({
        "quiz_id": quiz["quiz_id"],
        "student": student.strip(),
        "question_index": question_index,
        "answer": student_answer.strip(),
        "correct": is_correct,
        "submitted_at": _now()
    })
    _save_data(database)

    return {
        "status": "success",
        "quiz_id": quiz["quiz_id"],
        "question_index": question_index,
        "correct": is_correct,
        "correct_answer": correct_answer,
        "explanation": question.get("explanation", "")
    }


# 4. LOG SCORE

def _log_score(database: dict, data: dict) -> dict:
    quiz = _find_quiz(database, data.get("quiz_id"))
    if quiz is None:
        return _quiz_not_found(data.get("quiz_id"))

    student = data.get("student")
    if not _valid_student(student):
        return _error("A student name is required.")

    questions = quiz["questions"]
    score = data.get("score")
    total = data.get("total")

    if score is not None:
        # 1) Score given directly. Total defaults to the number of questions.
        score = _as_int(score)
        total = len(questions) if total is None else _as_int(total)
        source = "provided"
    elif data.get("answers") is not None:
        # 2) A full list of answers, one per question, in question order.
        answers = data["answers"]
        if not isinstance(answers, list) or len(answers) != len(questions):
            return _error(f"Answers must be a list with exactly {len(questions)} answers.")
        if not all(isinstance(answer, str) for answer in answers):
            return _error("Every submitted answer must be a string.")
        score = sum(
            answer.strip().casefold() == question["answer"].strip().casefold()
            for answer, question in zip(answers, questions)
        )
        total = len(questions)
        source = "answers_list"
    else:
        # 3) Answers saved earlier with submit_answer. Unanswered questions count as wrong.
        student_key = student.strip().casefold()
        submitted = [
            item for item in database["submissions"]
            if item.get("quiz_id") == quiz["quiz_id"] and item.get("student", "").casefold() == student_key
        ]
        if not submitted:
            return _error(
                "Provide score (and optionally total), an answers list, "
                "or submit answers with submit_answer first."
            )
        score = sum(1 for item in submitted if item.get("correct"))
        total = len(questions)
        source = "submitted_answers"

    if score is None or total is None or total <= 0 or score < 0 or score > total:
        return _error("Score and total must be whole numbers, with 0 <= score <= total and total > 0.")

    percent = round((score / total) * 100, 2)
    record = {
        "quiz_id": quiz["quiz_id"],
        "topic": quiz["topic"],
        "student": student.strip(),
        "score": score,
        "total": total,
        "percent": percent,
        "logged_at": _now()
    }
    database["scores"].append(record)
    _save_data(database)

    return {
        "status": "success",
        "quiz_id": quiz["quiz_id"],
        "score": score,
        "total": total,
        "percent": percent,
        "calculated_from": source
    }


# 5. GET SCORES

def _get_scores(database: dict, data: dict) -> dict:
    student_filter = data.get("student")

    if student_filter is not None and not _valid_student(student_filter):
        return _error("Student must be a non-empty string.")

    history = database["scores"]
    if student_filter is not None:
        wanted = student_filter.strip().casefold()
        history = [item for item in history if item.get("student", "").casefold() == wanted]

    attempts = len(history)
    average_percent = None
    if attempts > 0:
        average_percent = round(sum(item.get("percent", 0) for item in history) / attempts, 2)

    return {
        "status": "success",
        "attempts": attempts,
        "average_percent": average_percent,
        "history": history
    }
