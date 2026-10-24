"""Settings for the StudyBuddy agent. Change values here, not inside the code."""

# Local Ollama model used by the agent (must appear in `ollama list`).
MODEL_NAME = "qwen3:4b"

# Maximum number of model calls the agent may make for one user message.
# Used by the tool-calling loop (Milestone 5).
MAX_STEPS = 10

# qwen3 always reasons before answering. True keeps that reasoning in a
# separate field (response.message.thinking) so it never appears in the answer.
THINK = True
