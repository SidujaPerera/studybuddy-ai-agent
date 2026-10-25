# Study Buddy AI Agent

A local AI-powered study assistant developed for the university assignment **Building an AI Agent with Ollama**. Students can chat with a tutor, search sample study notes, manage quizzes and scores, look up Wikipedia articles, and record simulated study sessions. The application offers both a Streamlit web interface and a terminal interface.

## Project repository

https://github.com/SidujaPerera/studybuddy-ai-agent

## Technology

- Python 3.13.7 (development environment)
- Ollama with local `qwen3:4b`
- `ollama==0.6.3`, `httpx==0.28.1`, `streamlit==1.66.1`
- Local JSON files for quiz results and study sessions

Claude Code was used to assist development; **Claude is not the application's runtime language model**.

## Setup on Windows

1. Install Python and [Ollama](https://ollama.com/download).
2. Clone this repository and open a terminal in the project root:

   ```powershell
   git clone https://github.com/SidujaPerera/studybuddy-ai-agent.git
   cd studybuddy-ai-agent
   ```

3. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use the environment's Python directly for the following commands instead of changing system-wide security settings.

4. Install packages:

   ```powershell
   python -m pip install -r requirements.txt
   ```

5. Download the model and verify it is available:

   ```powershell
   ollama pull qwen3:4b
   ollama list
   ```

   Ensure the Ollama service is running before starting Study Buddy.

## Run the application

**Web interface (recommended):**

```powershell
python -m streamlit run streamlit_app.py
```

Open the local address shown in the terminal (usually `http://localhost:8501`). Use the AI Tutor, Study Notes, Quiz Tracker, Study Planner, and Wikipedia sections.

**Terminal interface:**

```powershell
python main.py
```

Terminal commands: `/help`, `/tools`, `/reset`, and `/exit`.

## Three example prompts

1. **Simple tutoring:** “Explain Python loops in three simple sentences, then give one example.”
2. **Study notes:** “Use search_notes to find photosynthesis in my local notes and summarize the key points.”
3. **Multi-step task:** “First use search_notes to search my notes for photosynthesis. Then use schedule_study_session to record a 45-minute photosynthesis session on 2026-10-27. Only confirm it if the scheduling tool succeeds.”

The model can be slow on CPU-only laptops. In development, multi-step responses sometimes took many minutes. Allow the answer to finish and verify the tool trace before treating an action as complete.

## How the agent works

1. The student sends a message through Streamlit or the CLI.
2. `StudyBuddyAgent` sends the conversation and available tool definitions to local Ollama.
3. If the model requests a tool, `ToolRegistry` checks its name and arguments, executes the registered Python function, and returns the result to the model.
4. The loop repeats until the model answers, or the maximum of 10 model calls is reached.
5. Session conversation history is retained until reset. Tool calls and errors are logged locally.

The registry exposes four tools: `search_notes`, `quiz_tracker`, `wikipedia_search`, and `schedule_study_session`. The real implementations are in `studybuddy/tools/`.

## Main files

| Path | Purpose |
| --- | --- |
| `streamlit_app.py` | Web interface |
| `main.py` | Terminal entry point |
| `studybuddy/agent.py` | Agent loop and session history |
| `studybuddy/tool_registry.py` | Tool validation and execution |
| `studybuddy/register_tools.py` | Tool name and function mapping |
| `studybuddy/prompts.py` | Tutor instructions |
| `studybuddy/claim_check.py` | Warnings for unverified completed-action claims |
| `studybuddy/logger.py` | Local tool-call logging |
| `studybuddy/tools/` | Notes, quiz, Wikipedia and scheduler functions |
| `notes/` | Fictional demonstration notes |

## Data and privacy

- Quiz and simulated session records are stored locally in `study_buddy_data/`, which is excluded from Git.
- Log files are stored locally and excluded from Git. The logger redacts selected sensitive fields.
- The study scheduler **does not create real calendar invitations**.
- Wikipedia answers distinguish live data from mock data when applicable.
- The project does not implement secure student authentication. Use **fictional students and sample data only**.
- Conversation memory is in-process and is cleared when the session resets or ends.

## Verification and known limitations

- During development, Claude Code reported **339 passing offline checks** for the integrated agent and tools, and **58 passing Streamlit UI checks**. These are development checks, not a substitute for independent final QA.
- A real local Ollama multi-tool request initially executed only notes search and falsely claimed scheduling had succeeded. An explicit retry did execute both tools and persist the mock session. A subsequent prompt-and-code safeguard warns about some unsupported completion claims; it was verified offline, not rerun end-to-end with Ollama.
- A live Wikipedia request succeeded after correcting the project's User-Agent identifier.
- Qwen3 4B can be slow or occasionally choose the wrong tool on limited hardware. The completion-claim checker is wording-based and cannot catch every possible false claim.
- The quiz history is not protected by student login. Do not use real personal learning records.

## Team contributions

| Member | Contribution |
| --- | --- |
| **Siduja Perera** | Agent and orchestration architecture, Ollama integration, memory, registry, CLI, logging, action-confirmation safeguard, debugging of tool issues after handoff, final integration, and Streamlit UI |
| **Mehansa** | Original development of the notes, quiz, Wikipedia and scheduler tools and their data-handling logic |
| **Radeesha** | Testing, final documentation, report and demonstration preparation (to be verified and updated by the team) |

The Git history retains Mehansa's original tool commit separately from later repair and integration commits.

## Submission note

The team should attach the final technical report and demo video separately. Confirm the final submission evidence and any tests performed after this README was drafted on **25 October 2026**.
