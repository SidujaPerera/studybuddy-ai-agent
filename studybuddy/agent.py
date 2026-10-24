"""StudyBuddyAgent: talks to the local Ollama model, uses tools, and remembers the conversation.

How one question is answered (the "agent loop"):
  1. The student's message is added to the history.
  2. The model is called with the history and the list of available tools.  <- one step
  3. If the model asks for tools, each tool is run through the ToolRegistry and its
     result is added to the history, then we go back to step 2.
  4. If the model gives a normal answer instead, that answer is returned.
At most config.MAX_STEPS model calls are made. The last call is made without tools,
so the model must answer with the information it already has.
"""

import json

import ollama

from studybuddy import config
from studybuddy.prompts import SYSTEM_PROMPT
from studybuddy.tool_registry import ToolRegistry

NO_ANSWER_TEXT = "Sorry, I couldn't come up with an answer. Please try asking again."


class StudyBuddyAgent:
    def __init__(self, registry=None, model=config.MODEL_NAME, system_prompt=SYSTEM_PROMPT,
                 max_steps=config.MAX_STEPS):
        # An empty registry means plain chat with no tools.
        self.registry = registry if registry is not None else ToolRegistry()
        self.model = model
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.history = []
        self.tool_calls_made = []  # tools used while answering the latest question
        self.reset()

    def reset(self):
        """Forget the conversation and start again with only the system prompt."""
        self.history = [{"role": "system", "content": self.system_prompt}]

    def ask(self, user_text):
        """Answer one student message, using tools if the model asks for them."""
        turn_start = len(self.history)
        self.history.append({"role": "user", "content": user_text})
        self.tool_calls_made = []
        try:
            return self._run_agent_loop()
        except Exception:
            # Remove this unfinished turn so the history stays consistent.
            del self.history[turn_start:]
            raise

    def _run_agent_loop(self):
        tools = self.registry.schemas()

        for step in range(1, self.max_steps + 1):
            is_last_step = step == self.max_steps
            response = ollama.chat(
                model=self.model,
                messages=self.history,
                tools=None if is_last_step or not tools else tools,
                think=config.THINK,
            )
            message = response.message

            if not message.tool_calls:
                answer = clean_answer(message.content or "") or NO_ANSWER_TEXT
                self.history.append({"role": "assistant", "content": answer})
                return answer

            # The model asked for one or more tools. First remember its request...
            self.history.append(_assistant_tool_request(message))
            # ...then run each tool and add a matching result message.
            for call in message.tool_calls:
                name = call.function.name
                arguments = dict(call.function.arguments or {})
                result = self.registry.execute(name, arguments)
                self.tool_calls_made.append({"step": step, "name": name, "arguments": arguments, "result": result})
                self.history.append({"role": "tool", "tool_name": name, "content": json.dumps(result)})

        # Only reached if the final no-tools call still returned tool calls (should not happen).
        answer = "Sorry, I reached my limit of steps for this question. Please try a simpler question."
        self.history.append({"role": "assistant", "content": answer})
        return answer


def _assistant_tool_request(message):
    """Turn the model's tool request into a plain dict for the conversation history."""
    request = {
        "role": "assistant",
        "content": clean_answer(message.content or ""),
        "tool_calls": [
            {"function": {"name": call.function.name, "arguments": dict(call.function.arguments or {})}}
            for call in message.tool_calls
        ],
    }
    if message.thinking:
        # Keep the reasoning so the model remembers why it chose these tools.
        request["thinking"] = message.thinking
    return request


def clean_answer(text):
    """Remove any reasoning the model leaked into its answer (text before '</think>')."""
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return text.strip()
