"""Command-line interface: lets a student chat with Study Buddy in the terminal."""

import sys

import ollama

from studybuddy import config, logger, register_tools
from studybuddy.agent import StudyBuddyAgent

HELP_TEXT = """Commands:
  /help   Show this list of commands
  /tools  Show the study tools available to Study Buddy
  /reset  Forget the conversation and start again
  /exit   Close Study Buddy
Anything else you type is sent to Study Buddy as a question."""

MOCK_WARNING = "NOTE: using TEMPORARY MOCK tools - tool results are fake placeholder data."

OLLAMA_UNAVAILABLE_TEXT = """Could not connect to Ollama.
Make sure the Ollama app is running (or run `ollama serve` in another terminal),
then try again."""

MODEL_MISSING_TEXT = f"""The model '{config.MODEL_NAME}' is not installed in Ollama.
Download it with: ollama pull {config.MODEL_NAME}"""

NOT_SAVED_TEXT = "Your question was not saved, so you can simply ask it again."


def use_utf8_output():
    """Make printing emojis and other Unicode safe on Windows.

    When output goes to a pipe or an IDE console, Windows Python uses the old
    cp1252 encoding, which crashes on characters such as emojis.
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        # Some environments replace or remove the standard streams; leave those alone.
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def check_ollama():
    """Return None if Ollama is running and has our model, otherwise an error message."""
    try:
        installed = [m.model for m in ollama.list().models]
    except ConnectionError:
        return OLLAMA_UNAVAILABLE_TEXT
    except Exception as error:
        logger.log_unexpected_error(error)
        return f"Ollama is not responding correctly ({type(error).__name__}). Try restarting the Ollama app."

    if config.MODEL_NAME not in installed:
        return MODEL_MISSING_TEXT
    return None


def handle_command(command, agent):
    """Run a /command. Return False if the program should exit, otherwise True."""
    command = command.lower()

    if command == "/exit":
        print("Goodbye, and good luck with your studies!")
        return False
    if command == "/help":
        print(HELP_TEXT)
    elif command == "/tools":
        show_tools(agent)
    elif command == "/reset":
        agent.reset()
        print("Conversation cleared. Let's start fresh!")
    else:
        print(f"Unknown command '{command}'. Type /help to see the commands.")
    return True


def show_tools(agent):
    """Print the tools the agent can use."""
    if register_tools.USE_MOCK_TOOLS:
        print(MOCK_WARNING)
    print("Study tools:")
    for name in agent.registry.names():
        print(f"  {name}: {agent.registry.description(name)}")


def ask_agent(agent, question):
    """Send a question to the agent and print the answer or a friendly error."""
    print("Study Buddy is thinking... (this can take a few minutes on CPU)")
    try:
        answer = agent.ask(question)
    except ConnectionError:
        print(OLLAMA_UNAVAILABLE_TEXT)
        print(NOT_SAVED_TEXT)
        return
    except ollama.ResponseError as error:
        if error.status_code == 404:
            print(MODEL_MISSING_TEXT)
        else:
            print(f"Ollama reported a problem: {error.error}")
        print(NOT_SAVED_TEXT)
        return
    except Exception as error:
        # For example the Ollama connection dropping in the middle of a reply.
        logger.log_unexpected_error(error)
        print(f"Something went wrong while talking to the model ({type(error).__name__}).")
        print("If Ollama was closed or restarted, start it again. Details are in the log file.")
        print(NOT_SAVED_TEXT)
        return

    for call in agent.tool_calls_made:
        status = "ok" if call["result"]["ok"] else "error: " + call["result"]["error"]
        print(f"  [step {call['step']}] used tool {call['name']}({call['arguments']}) -> {status}")
    print(f"\nStudy Buddy: {answer}")


def run_cli():
    """Main loop: read what the student types and respond until they exit."""
    use_utf8_output()
    log_file = logger.setup_logging()
    print("=== Study Buddy - your AI study assistant ===")
    print(f"Model: {config.MODEL_NAME}. Type /help for commands.")
    print(f"Tool calls are logged to {log_file}")

    problem = check_ollama()
    if problem:
        print(problem)
        return

    try:
        registry = register_tools.build_registry()
    except Exception as error:
        # For example a tool whose schema does not match its Python function.
        logger.log_unexpected_error(error)
        print(f"Could not load the study tools: {error}")
        return

    agent = StudyBuddyAgent(registry=registry)
    logger.log_session_start(config.MODEL_NAME, registry.names(), register_tools.USE_MOCK_TOOLS)
    if register_tools.USE_MOCK_TOOLS:
        print(MOCK_WARNING)
    try:
        while True:
            user_text = input("\nYou: ").strip()

            if not user_text:
                print("Please type a question, or /help to see the commands.")
            elif user_text.startswith("/"):
                if not handle_command(user_text, agent):
                    return
            else:
                ask_agent(agent, user_text)
    except (EOFError, KeyboardInterrupt):
        # Ctrl+C (even while Study Buddy is thinking), or the end of piped input,
        # closes the program cleanly instead of showing an error.
        print("\nGoodbye!")
