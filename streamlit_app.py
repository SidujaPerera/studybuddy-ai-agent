"""Study Buddy web interface built with Streamlit.

Start it from the project folder:   streamlit run streamlit_app.py

This file is only a user interface. It reuses:
  - StudyBuddyAgent (agent loop, memory, MAX_STEPS, rollback, action-claim safeguard)
  - the ToolRegistry from register_tools.build_registry()
The forms call the registered tools through registry.execute(), so they get the same
argument checks, error / not_found handling and log redaction as tool calls made by the model.
"""

import html
import json
from datetime import date, timedelta

import ollama
import streamlit as st

from studybuddy import config, logger, register_tools
from studybuddy.agent import StudyBuddyAgent
from studybuddy.cli import MODEL_MISSING_TEXT, OLLAMA_UNAVAILABLE_TEXT, check_ollama

NAVY = "#171A35"
PURPLE = "#6857E8"
BACKGROUND = "#F7F7FC"
CLAIM_WARNING = "[Study Buddy check]"

EXAMPLE_PROMPTS = [
    "Explain the water cycle in simple words.",
    "Search my notes for photosynthesis and summarise them.",
    "Give me 3 quick tips for revising Python loops.",
]

# Text and colours for each tool status: (label, text colour, background colour)
STATUS_BADGES = {
    "success": ("Success", "#137A4B", "#E3F6EC"),
    "not_found": ("No results", "#8A5A00", "#FFF4D6"),
    "error": ("Error", "#B42828", "#FDE8E8"),
    "unknown": ("Result shortened", "#4B4E6D", "#ECECF4"),
}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, .stApp, button, input, textarea, select {{ font-family: 'Inter', sans-serif; }}
.stApp {{ background: {BACKGROUND}; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1180px; }}

.sb-header {{ background: {NAVY}; color: #FFFFFF; border-radius: 18px; padding: 18px 24px;
  display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap;
  margin-bottom: 18px; box-shadow: 0 8px 24px rgba(23, 26, 53, 0.18); }}
.sb-brand {{ display: flex; align-items: center; gap: 14px; }}
.sb-logo {{ width: 46px; height: 46px; border-radius: 14px; background: {PURPLE};
  display: flex; align-items: center; justify-content: center; font-size: 24px; }}
.sb-title {{ font-size: 1.35rem; font-weight: 700; line-height: 1.2; }}
.sb-subtitle {{ font-size: 0.85rem; color: #B9BCE0; }}
.sb-pill {{ font-size: 0.8rem; padding: 6px 12px; border-radius: 999px;
  background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.16); white-space: nowrap; }}
.sb-dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 7px; }}

div[role="tablist"] {{ gap: 6px; background: #FFFFFF; padding: 6px; border-radius: 14px;
  border: 1px solid #E7E7F3; flex-wrap: wrap; }}
div[data-testid="stTab"] {{ border-radius: 10px; padding: 8px 16px; font-weight: 600; }}
div[data-testid="stTab"][aria-selected="true"] {{ background: {PURPLE}; }}
div[data-testid="stTab"][aria-selected="true"] p {{ color: #FFFFFF !important; }}

/* White cards: every container created with key="card-..." */
div[class*="st-key-card-"] {{ background: #FFFFFF; border-radius: 16px; border: 1px solid #E7E7F3;
  box-shadow: 0 2px 10px rgba(23, 26, 53, 0.05); }}
.stButton > button, .stFormSubmitButton > button {{ border-radius: 10px; font-weight: 600; }}

div[data-testid="stChatMessage"] {{ background: #FFFFFF; border-radius: 16px; border: 1px solid #E7E7F3;
  padding: 12px 16px; margin-bottom: 10px; }}
div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {{
  background: #EFEDFD; border-color: #DCD7FB; }}

.sb-badge {{ display: inline-block; font-size: 0.75rem; font-weight: 600; padding: 3px 10px;
  border-radius: 999px; margin: 0 6px 4px 0; }}
.sb-muted {{ color: #6B6E8E; font-size: 0.9rem; }}
.sb-section-title {{ font-size: 1.15rem; font-weight: 700; color: {NAVY}; margin: 0 0 2px 0; }}
</style>
"""


# ---------------- shared resources (created once per server) ----------------

@st.cache_resource
def start_logging():
    return logger.setup_logging()


@st.cache_resource
def shared_registry():
    """The same tool registry the CLI uses. It holds no per-student state, so it can be shared."""
    return register_tools.build_registry()


@st.cache_data(ttl=20, show_spinner=False)
def ollama_problem():
    """None if Ollama is running with our model, otherwise a message (checked at most every 20 s)."""
    return check_ollama()


# ---------------- small helpers ----------------

def badge(text, colour, background):
    return f'<span class="sb-badge" style="color:{colour};background:{background}">{html.escape(text)}</span>'


def result_badges(result):
    """Status badge plus a live/mock source badge, based only on what the tool really returned."""
    if result is None or result.get("ok") is None:
        status = "unknown"
    else:
        status = result.get("status") or ("success" if result["ok"] else "error")
    label, colour, background = STATUS_BADGES.get(status, STATUS_BADGES["unknown"])
    badges = badge(label, colour, background)

    source = logger.result_source(result) if result else None
    if source == "live":
        badges += badge("Source: live Wikipedia", "#1D5FBF", "#E5EFFD")
    elif source == "mock":
        badges += badge("Source: MOCK placeholder", "#B42828", "#FDE8E8")
    elif source:
        badges += badge(f"Source: {source}", "#4B4E6D", "#ECECF4")
    return badges


def run_tool(registry, name, arguments):
    """Call a registered tool from a web form. Logged like model tool calls (shown as step 0)."""
    result = registry.execute(name, arguments)
    logger.log_tool_call(0, name, arguments, result, registry.is_mock(name), registry.is_registered(name))
    return result


def show_result_status(result, success_text):
    """Show the outcome honestly: a success message only if the tool really succeeded."""
    st.markdown(result_badges(result), unsafe_allow_html=True)
    if not result["ok"]:
        st.error(result["error"])
    elif result.get("status") == "not_found":
        st.info(result.get("result", {}).get("message", "No matching results were found."))
    else:
        st.success(success_text)
    if logger.result_source(result) == "mock":
        st.warning("This is placeholder (mock) data, not real Wikipedia content.")


def raw_result(result):
    with st.expander("Raw tool result"):
        st.json(result)


def section_title(icon, title, caption):
    st.markdown(f'<p class="sb-section-title">{icon} {html.escape(title)}</p>'
                f'<p class="sb-muted">{html.escape(caption)}</p>', unsafe_allow_html=True)


# ---------------- per-student session ----------------

def get_agent(registry):
    """One StudyBuddyAgent per browser session, so each student has their own memory."""
    if "agent" not in st.session_state:
        st.session_state.agent = StudyBuddyAgent(registry=registry)
        logger.log_session_start(config.MODEL_NAME, registry.names(), register_tools.USE_MOCK_TOOLS,
                                 [name for name in registry.names() if registry.is_mock(name)])
    return st.session_state.agent


def conversation_turns(history):
    """Turn the agent's history into what the page shows: questions, answers and the tools used.
    The system prompt and the model's hidden reasoning are never shown."""
    turns, pending_tools = [], []
    for message in history[1:]:
        role = message.get("role")
        if role == "user":
            turns.append({"role": "user", "content": message["content"]})
            pending_tools = []
        elif role == "assistant" and message.get("tool_calls"):
            for call in message["tool_calls"]:
                pending_tools.append({"name": call["function"]["name"],
                                      "arguments": call["function"]["arguments"], "result": None})
        elif role == "tool":
            for tool in pending_tools:
                if tool["result"] is None:
                    tool["result"] = _parse_tool_message(message["content"])
                    break
        elif role == "assistant":
            turns.append({"role": "assistant", "content": message["content"], "tools": pending_tools})
            pending_tools = []
    return turns


def _parse_tool_message(text):
    try:
        return json.loads(text)
    except ValueError:
        return None  # very long results are shortened before being sent to the model


def ask_agent(agent, prompt):
    """Ask the existing agent. Returns an error message for the page, or None on success."""
    try:
        agent.ask(prompt)
    except ConnectionError:
        return OLLAMA_UNAVAILABLE_TEXT
    except ollama.ResponseError as error:
        return MODEL_MISSING_TEXT if error.status_code == 404 else f"Ollama reported a problem: {error.error}"
    except Exception as error:
        logger.log_unexpected_error(error)
        return f"Something went wrong while talking to the model ({type(error).__name__}). Details are in the log file."
    return None


# ---------------- page sections ----------------

def render_header(problem):
    if problem:
        status = f'<span class="sb-pill"><span class="sb-dot" style="background:#FF6B6B"></span>Ollama unavailable</span>'
    else:
        status = (f'<span class="sb-pill"><span class="sb-dot" style="background:#3DD68C"></span>'
                  f'Local AI ready · {html.escape(config.MODEL_NAME)}</span>')
    st.markdown(
        f"""<div class="sb-header">
              <div class="sb-brand">
                <div class="sb-logo">🎓</div>
                <div><div class="sb-title">Study Buddy</div>
                     <div class="sb-subtitle">Your private AI study assistant · runs locally with Ollama</div></div>
              </div>
              {status}
            </div>""",
        unsafe_allow_html=True,
    )


def render_message(turn):
    if turn["role"] == "user":
        with st.chat_message("user"):
            st.markdown(turn["content"])
        return

    with st.chat_message("assistant", avatar="🎓"):
        answer, marker, warning = turn["content"].partition(CLAIM_WARNING)
        st.markdown(answer.strip())
        if marker:
            st.warning(marker + warning)
        if turn["tools"]:
            with st.expander(f"🛠 Tools used ({len(turn['tools'])})"):
                for tool in turn["tools"]:
                    arguments = html.escape(json.dumps(tool["arguments"], ensure_ascii=False))
                    st.markdown(f"**{html.escape(tool['name'])}** <code>{arguments}</code><br>"
                                f"{result_badges(tool['result'])}", unsafe_allow_html=True)
                    if tool["result"] and not tool["result"].get("ok"):
                        st.caption(tool["result"].get("error", ""))


def tutor_tab(agent, problem):
    header, button = st.columns([4, 1], vertical_alignment="center")
    with header:
        section_title("🤖", "AI Tutor", "Ask questions, get explanations, and let Study Buddy use your study tools.")
    with button:
        if st.button("➕ New chat", key="new_chat", width="stretch"):
            agent.reset()  # the existing reset: clears the conversation memory
            st.session_state.pop("chat_error", None)
            st.rerun()

    if problem:
        st.error(problem)
        if st.button("Check connection again", key="retry_ollama"):
            ollama_problem.clear()
            st.rerun()

    turns = conversation_turns(agent.history)
    chat_box = st.container(height=480, border=True, key="card-chat")
    with chat_box:
        if not turns:
            st.markdown('<p class="sb-muted">👋 Hi! I\'m Study Buddy. Ask me about a topic, or try an example:</p>',
                        unsafe_allow_html=True)
            for number, example in enumerate(EXAMPLE_PROMPTS):
                if st.button(example, key=f"example_{number}", disabled=bool(problem)):
                    st.session_state.pending_prompt = example
                    st.rerun()
        for turn in turns:
            render_message(turn)

    if st.session_state.get("chat_error"):
        st.error(st.session_state.chat_error + "\n\nYour question was not saved, so you can simply ask it again.")

    typed = st.chat_input("Ask Study Buddy about your studies…", key="chat_input", disabled=bool(problem))
    prompt = typed or st.session_state.pop("pending_prompt", None)
    if prompt and not problem:
        with chat_box:
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant", avatar="🎓"):
                with st.spinner("Study Buddy is thinking… the local AI runs on your CPU, so this can take several minutes."):
                    st.session_state.chat_error = ask_agent(agent, prompt)
        st.rerun()


def notes_tab(registry):
    left, right = st.columns(2, gap="large")

    with left, st.container(border=True, key="card-notes"):
        section_title("📝", "Search my notes", "Searches the saved notes in the project's notes/ folder (.txt, .md, .json).")
        with st.form("notes_form"):
            topic = st.text_input("Topic", placeholder="e.g. photosynthesis", key="notes_topic")
            if st.form_submit_button("Search notes", type="primary", key="notes_submit"):
                st.session_state.notes_result = run_tool(registry, "search_notes", {"topic": topic})
        result = st.session_state.get("notes_result")
        if result:
            show_result_status(result, f"Found {result.get('result', {}).get('result_count', 0)} matching note(s).")
            if result["ok"] and result.get("status") == "success":
                for note in result["result"]["results"]:
                    with st.expander(f"📄 {note['file']}"):
                        st.text(note["content"])
            raw_result(result)

    with right, st.container(border=True, key="card-wiki"):
        section_title("🌐", "Wikipedia lookup", "Searches the real Wikipedia website. Always check important facts.")
        with st.form("wiki_form"):
            query = st.text_input("Search Wikipedia", placeholder="e.g. water cycle", key="wiki_query")
            if st.form_submit_button("Search Wikipedia", type="primary", key="wiki_submit"):
                with st.spinner("Contacting Wikipedia…"):
                    st.session_state.wiki_result = run_tool(registry, "wikipedia_search", {"query": query})
        result = st.session_state.get("wiki_result")
        if result:
            show_result_status(result, f"{result.get('result', {}).get('results_count', 0)} article(s) found.")
            if result["ok"] and result.get("status") == "success":
                for article in result["result"]["results"]:
                    title = article["title"]
                    if article.get("url"):
                        st.markdown(f"**[{title}]({article['url']})**")
                    else:
                        st.markdown(f"**{title}**")
                    st.caption(article.get("summary", ""))
                if result["result"].get("note"):
                    st.caption(f"ℹ️ {result['result']['note']}")
            raw_result(result)


def parse_questions(text):
    """Turn lines like 'question | answer' into quiz questions. Returns (questions, error)."""
    questions = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 2 or not all(parts):
            return None, f"Line {number} must look like: question | answer"
        questions.append({"question": parts[0], "answer": parts[1]})
    if not questions:
        return None, "Add at least one question."
    return questions, None


def quiz_tab(registry):
    st.caption("Use fictional student names for the demo. Saved quizzes and scores stay on this computer.")
    left, right = st.columns(2, gap="large")

    with left, st.container(border=True, key="card-scores"):
        section_title("📊", "Scores", "Load saved quiz scores, for one student or for everyone.")
        with st.form("scores_form"):
            student = st.text_input("Student (optional)", placeholder="e.g. Test Student A", key="scores_student")
            if st.form_submit_button("Load scores", type="primary", key="scores_submit"):
                data = {"student": student.strip()} if student.strip() else {}
                st.session_state.scores_result = run_tool(registry, "quiz_tracker", {"action": "get_scores", "data": data})
        result = st.session_state.get("scores_result")
        if result:
            show_result_status(result, "Scores loaded.")
            if result["ok"]:
                info = result["result"]
                attempts, average = st.columns(2)
                attempts.metric("Attempts", info["attempts"])
                average.metric("Average", "–" if info["average_percent"] is None else f"{info['average_percent']}%")
                if info["history"]:
                    st.dataframe(info["history"], width="stretch", hide_index=True)
            raw_result(result)

    with right, st.container(border=True, key="card-open-quiz"):
        section_title("🧠", "Open a quiz", "Shows a saved quiz without its answers.")
        with st.form("get_quiz_form"):
            quiz_id = st.number_input("Quiz ID", min_value=1, step=1, value=1, key="get_quiz_id")
            if st.form_submit_button("Open quiz", type="primary", key="get_quiz_submit"):
                st.session_state.get_quiz_result = run_tool(
                    registry, "quiz_tracker", {"action": "get_quiz", "data": {"quiz_id": int(quiz_id)}})
        result = st.session_state.get("get_quiz_result")
        if result:
            show_result_status(result, "Quiz loaded.")
            if result["ok"]:
                st.markdown(f"**{result['result']['topic']}**")
                for question in result["result"]["questions"]:
                    st.markdown(f"{question['question_index'] + 1}. {question['question']}")
                    if question.get("options"):
                        st.caption("Options: " + ", ".join(question["options"]))
            raw_result(result)

    left, right = st.columns(2, gap="large")
    with left, st.container(border=True, key="card-save-quiz"):
        section_title("➕", "Create a quiz", "One question per line, written as: question | answer")
        with st.form("save_quiz_form"):
            topic = st.text_input("Quiz topic", placeholder="e.g. Water cycle", key="save_quiz_topic")
            lines = st.text_area("Questions", key="save_quiz_questions", height=120,
                                 placeholder="What forms clouds? | Condensation\nRain, snow and hail are called? | Precipitation")
            if st.form_submit_button("Save quiz", type="primary", key="save_quiz_submit"):
                questions, form_error = parse_questions(lines)
                if form_error:
                    st.session_state.save_quiz_result = {"ok": False, "status": "error", "error": form_error}
                else:
                    st.session_state.save_quiz_result = run_tool(
                        registry, "quiz_tracker", {"action": "save_quiz", "data": {"topic": topic, "questions": questions}})
        result = st.session_state.get("save_quiz_result")
        if result:
            quiz_id = result.get("result", {}).get("quiz_id")
            show_result_status(result, f"Quiz saved. Its quiz ID is {quiz_id}.")
            if "result" in result:
                raw_result(result)

    with right, st.container(border=True, key="card-log-score"):
        section_title("✅", "Log a score", "Record a quiz result for a (fictional) student.")
        with st.form("log_score_form"):
            columns = st.columns(2)
            log_quiz_id = columns[0].number_input("Quiz ID", min_value=1, step=1, value=1, key="log_quiz_id")
            log_student = columns[1].text_input("Student", placeholder="e.g. Test Student A", key="log_student")
            score = columns[0].number_input("Score", min_value=0, step=1, value=0, key="log_score_value")
            total = columns[1].number_input("Out of", min_value=1, step=1, value=10, key="log_total_value")
            if st.form_submit_button("Log score", type="primary", key="log_score_submit"):
                st.session_state.log_score_result = run_tool(registry, "quiz_tracker", {
                    "action": "log_score",
                    "data": {"quiz_id": int(log_quiz_id), "student": log_student,
                             "score": int(score), "total": int(total)},
                })
        result = st.session_state.get("log_score_result")
        if result:
            info = result.get("result", {})
            show_result_status(result, f"Score recorded: {info.get('score')}/{info.get('total')} ({info.get('percent')}%).")
            raw_result(result)


def planner_tab(registry):
    left, right = st.columns([3, 2], gap="large")
    with left, st.container(border=True, key="card-planner"):
        section_title("📅", "Plan a study session", "Book time to study a topic.")
        st.info("**Simulated scheduling.** This records a mock study session in Study Buddy's local data. "
                "It does not create a real calendar invitation or send any notification.")
        with st.form("planner_form"):
            session_date = st.date_input("Date", value=date.today() + timedelta(days=1),
                                         min_value=date.today(), format="YYYY-MM-DD", key="plan_date")
            duration = st.number_input("Duration (minutes)", min_value=5, max_value=720, step=5, value=45,
                                       key="plan_duration")
            topic = st.text_input("Topic", placeholder="e.g. photosynthesis", key="plan_topic")
            if st.form_submit_button("Record study session", type="primary", key="plan_submit"):
                st.session_state.plan_result = run_tool(registry, "schedule_study_session", {
                    "date": session_date.isoformat(), "duration_minutes": int(duration), "topic": topic})

    with right, st.container(border=True, key="card-planner-result"):
        section_title("🗓", "Result", "The scheduler's real response.")
        result = st.session_state.get("plan_result")
        if not result:
            st.markdown('<p class="sb-muted">No session recorded yet in this browser session.</p>',
                        unsafe_allow_html=True)
        else:
            show_result_status(result, "Mock study session recorded (simulated - no calendar invite was sent).")
            if result["ok"]:
                session = result["result"]["session"]
                progress = result["result"]["progress"]
                st.markdown(f"**{session['topic']}** · {session['date']} · {session['duration_minutes']} min")
                st.caption(f"Session ID {session['session_id']} · status: {session['status']}")
                first, second = st.columns(2)
                first.metric("Sessions recorded", progress["total_sessions"])
                second.metric("Minutes planned", progress["total_study_minutes"])
                st.progress(min(1.0, progress["total_sessions"] / progress["study_goal"]),
                            text=f"{progress['remaining_sessions_to_goal']} session(s) left to reach the goal of "
                                 f"{progress['study_goal']}")
            raw_result(result)


# ---------------- main page ----------------

def main():
    st.markdown(CSS, unsafe_allow_html=True)
    start_logging()
    problem = ollama_problem()
    render_header(problem)

    try:
        registry = shared_registry()
    except Exception as error:
        logger.log_unexpected_error(error)
        st.error(f"Could not load the study tools: {error}")
        st.stop()

    agent = get_agent(registry)
    mock_tools = [name for name in registry.names() if registry.is_mock(name)]
    if mock_tools:
        st.warning("MOCK mode: " + ", ".join(mock_tools) + " return fake placeholder data, not real results.")

    tutor, notes, quiz, planner = st.tabs(["🤖 AI Tutor", "📝 Study Notes", "🧠 Quiz Tracker", "📅 Study Planner"])
    with tutor:
        tutor_tab(agent, problem)
    with notes:
        notes_tab(registry)
    with quiz:
        quiz_tab(registry)
    with planner:
        planner_tab(registry)

    st.caption(f"Model: {config.MODEL_NAME} (local) · Tool activity is logged without student names in logs/ · "
               "Study sessions are simulated.")


main()
