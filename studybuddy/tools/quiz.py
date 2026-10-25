import json
from pathlib import Path
from datetime import datetime

#Store quiz data in the project folder
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "study_buddy_data"
DATA_FILE = DATA_DIR / "quizzes_and_scores.json"

def _load_data():
    """Load saved quizess and scores from the JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_FILE.exists():
        return {
            "next_quiz_id": 1,
            "quizzes": {},
            "scores": []
        }
    
    try:
        with DATA_FILE.open("r", encoding="utf-8") as files:
            data = json.load(file)

        data.setdefault("next_quiz_id", 1)
        data.setdefault("quizzes", {})
        data.setdefault("scores", [])
        return data

    except (json.JSONDecodeError, OSError):
        raise RuntimeError(
            "Could not read quiz data. Check the JSON file."
        )

def _save_data():
    """Save quizzes and scores to the JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def _find_quiz(data, quiz_id):
    """Find a quiz using its ID."""
    try:
        quiz_id = int(quiz_id)
    except (TypeError, ValueError):
        return None

    return data ["quizzes"].get(str(quiz_id))

def quiz_manager(action: str, data: dict) ->dict:
    """Manage quizzes and student scores.

    Supported actions: save_quiz, get_quiz, submit_answer, log_score, get_scores"""

    if not isinstance(data, dict):
        return {
            "status": "error",
            "message": "Data must be a dictionary."
        }

    try:
        database = _load_data()

        #1.SAVE QUIZ

        if action == "save quiz":
            topic = data.get("topic")
            questions = data.get("questions")

            if not isinstance(topic, str) or not topic.strip():
                return {
                    "status": "error",
                    "message": "A valid topic is required."
                } 

            if not isinstance(questions, list) or not questions:
                return {
                    "status": "error",
                    "message": "Questions must be a non-empty list."
                }

            #Validate every question
            for question in questions:
                if not isinstance(question, dict):
                    return {
                        "status": "error",
                        "message": "Each question must be a dictionary."
                    }

                if not isinstance(question.get("question"), str) or not question["question"].strip():
                    return {
                        "status": "error",
                        "message": "Every question needs question text."
                    }

                if not isinstance(question.get("answer"), str) or not question["answer"].strip():
                    return {
                        "status": "error",
                        "message": "Every question needs a correct answer."
                    }

                options = question.get("options")
                if options is not None and (
                    not isinstance(options, list)
                    or not all(isinstance(option, str) for option in options)
                ):
                    return {
                        "status": "error",
                        "message": "Options must be a list of strings."
                    }

                explanation = question.get("explanation")
                if explanation is not None and not isinstance(explanation, str):
                    return {
                        "status": "error",
                        "message": "Explanation must be a string."
                    }

            quiz_id = database["next_quiz_id"]

            database["quizzes"][str(quiz_id)] = {
                "quiz_id": quiz_id,
                "topic": topic.strip(),
                "questions": questions,
                "created_at": datetime.now().isoformat(timespec="seconds")
            }

            database["next_quiz_id"] += 1
            _save_data(database)

            return {
                "status": "ok",
                "quiz_id": quiz_id,
                "num_questions": len(questions)
            }

        #2. GET QUIZ (HIDE ANSWERS AND EXPLANATIONS)

        elif action == "get_quiz":
            quiz = _find_quiz(dabase, data.get("quiz_id"))

            if quiz is None:
                return {
                    "status": "error",
                    "message": "Quiz not found."
                }

            public_questions = []

            for question in quiz["question"]:
                public_question = {
                    "question": question["question"]
                }

                if "options" in question:
                    public_question["options"] = question["options"]

                public_questions.append(public_question)

            return {
                "status": "ok",
                "quiz_id": quiz["quiz_id"],
                "topic": quiz["topic"],
                "quetions": public_questions
            }

        #3.SUBMIT ANSWER

        elif action == "submit_answer":
            quiz = _find_quiz(database, data.get("quiz_id"))

            if quiz is None:
                return {
                    "status": "error",
                    "message": "Quiz not found."
                }    

            student = data.get("student")
            question_index = data.get("quetion_index")
            student_answer = data.get("answer")

            if not isinstance(student, str) or not student.strip():
                return {
                    "status": "error",
                    "message": "A student name is rwquired."
                }

            #Reject booleans and non-integer indexes
            if isinstance(question_index, bool) or not isinstance(question_index, int):
                return {
                    "status": "error",
                    "message": "question_index must be an integer."
                }

            questions = quiz["questions"]

            if question_index < 0 or question_index >= len(questions):
                return {
                    "status": "error",
                    "message": "Question index is out of range."
                }

            if not isinstance(student_answer, str):
                return {
                    "status": "error",
                    "message": "Answer must be a string."
                }

            question = questions[question_index]
            correct_answer = question["answer"]

            is_correct = (
                student_answer.strip().casefold()
                == correct_answer.strip().casefold()
            )

            return {
                "status": "ok",
                "correct": is_correct,
                "correct_answer": correct_answer,
                "explanation": question.get("explanation", "")
            }

        #4. LOG SCORE

        elif action == "log score":
            quiz = _find_quiz(database, data.get("quiz_id"))

            if quiz is None:
                return {
                    "status": "error",
                    "message": "Quiz not found."                                      
            }

            student = data.get("student")

            if not isinstance(student, str) or not student.strip():
                return {
                    "status": "error",
                    "message": "A student name is required."
                }

            #If score and total are provided, use them.
            #Othewise, accept score and total from saved answers.
            score = data.get("score")
            total = data.get("total")

            if score is None or total is None:
                answers = data.get("answers")

                if not isinstance(answers, list):
                    return {
                        "status": "error",
                        "message": (
                            "Provide score and total, or an answers list."
                        )
                    }
                if len(answers) != len(quiz["questions"]):
                    if not isinstance(answer, str):
                        return {
                            "status": "error",
                            "message": (
                                "Answers must match the number of quiz questions."
                            )
                        }

                score = 0
                for index, answer in enumerate(answers):
                    if not isinstance(answer, str):
                        return {
                            "status": "error",
                            "message": "Every submitted answer must be astring."
                        }

                    correct = quiz["questions"][index]["answer"]
                    if  answer.strip().casefold() == coorect.strip().casefold():
                        score += 1
                total = len(quiz["questions"])

            if (
                isinstance(score, bool)
                or not isinstance(score, int)
                or isinstance(total, bool)
                or not isinstance(total, int)
                or total <= 0
                or score < 0
                or score > total
            ):
                return{
                    "status": "error",
                    "message": "Score an total must be valid integers."
                }

            percent = round((score / total) * 100, 2)

            database["scores"].append({
                "quiz_id": quiz["topic"],
                "score": score,
                "total": total,
                "percent": percent, 
                "logged at": datetime.now().jsonformat(timespec="sounds")
            })

            _save_data(database)

            return {
                "status": "ok",
                "score": score,
                "total": total,
                "percent": percent
            }


        #5.GET SCORES

        elif action == "get scores":
            student_filter = data.get("student")

            if student_filter is not None and (
                not isinstance(student_filter, str)
                or not student_filter.strip()
            ):
                return {
                    "status": "error",
                    "message": "Student must be a non-emptystring."
                } 

            history = database["scores"]

            if student_filter is not None:
                history = [
                    item for item in history 
                    if item["student"].casefold()
                    == student_filter.strip().casefold()
                ]

            attempts = len(history)

            average_percent = None
            if attempts > 0:
                average_percent = round(
                    sum(item["percent"] for item in history) / attempts, 
                    2
                )

            return {
                "status": "ok",
                "attempts": attempts,
                "average_percent": average_percent,
                "history": history
            }

        #UNKOWN ACTION

        else:
            return {
                "status": "error",
                "message": (
                    "Unkown action. Use save_quiz, get_quiz,submit_answer, log_score, or get_scores."
                )
            }

    except (OSError, RuntimeError) as error:
        return {
            "status": "error",
            "message": str(error)
        }