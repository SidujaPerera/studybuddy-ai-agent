"""Command-line interface: lets a student chat with Study Buddy in the terminal."""

import sys

import ollama

from studybuddy import config, register_tools
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


def use_utf8_output():
    """Make printing emojis and other Unicode safe on Windows.

    When output goes to a pipe or an IDE console, Windows Python uses the old
    cp1252 encoding, which crashes on characters such as emojis.
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")


def check_ollama():
    """Return None if Ollama is running and has our model, otherwise an error message."""
    try:
        installed = [m.model for m in ollama.list().models]
    except ConnectionError:
        return OLLAMA_UNAVAILABLE_TEXT

    if config.MODEL_NAME not in installed:
        return (
            f"The model '{config.MODEL_NAME}' is not installed in Ollama.\n"
            f"Download it with: ollama pull {config.MODEL_NAME}"
        )
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
        return
    except ollama.ResponseError as error:
        print(f"Ollama returned an error: {error.error}")
        return

    for call in agent.tool_calls_made:
        status = "ok" if call["result"]["ok"] else "error: " + call["result"]["error"]
        print(f"  [step {call['step']}] used tool {call['name']}({call['arguments']}) -> {status}")
    print(f"\nStudy Buddy: {answer}")


def run_cli():
    """Main loop: read what the student types and respond until they exit."""
    use_utf8_output()
    print("=== Study Buddy - your AI study assistant ===")
    print(f"Model: {config.MODEL_NAME}. Type /help for commands.")

    problem = check_ollama()
    if problem:
        print(problem)
        return

    agent = StudyBuddyAgent(registry=register_tools.build_registry())
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
