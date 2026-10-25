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
import time

import ollama

from studybuddy import config, logger
from studybuddy.claim_check import add_unverified_warning, find_unverified_claims
from studybuddy.prompts import SYSTEM_PROMPT
from studybuddy.tool_registry import ToolRegistry

NO_ANSWER_TEXT = "Sorry, I couldn't come up with an answer. Please try asking again."
MALFORMED_TOOL_CALL_TEXT = "Sorry, I tried to use a tool but my request came out garbled. Please try asking again."
MAX_STEPS_TEXT = "Sorry, I reached my limit of steps for this question. Please try a simpler question."


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
        logger.log_question(user_text)
        turn_start = len(self.history)
        self.history.append({"role": "user", "content": user_text})
        self.tool_calls_made = []
        try:
            return self._run_agent_loop()
        except BaseException:
            # Any failure (Ollama down, Ctrl+C, ...) removes this unfinished turn,
            # so the history never holds a question without an answer.
            logger.log_turn_rolled_back(len(self.history) - turn_start)
            del self.history[turn_start:]
            raise

    def _run_agent_loop(self):
        tools = self.registry.schemas()

        for step in range(1, self.max_steps + 1):
            is_last_step = step == self.max_steps
            offer_tools = bool(tools) and not is_last_step
            if is_last_step and tools:
                logger.log_max_steps(self.max_steps)

            started = time.time()
            try:
                response = ollama.chat(
                    model=self.model,
                    messages=self.history,
                    tools=tools if offer_tools else None,
                    think=config.THINK,
                )
            except Exception as error:
                logger.log_model_error(step, error)
                raise
            logger.log_model_call(step, self.max_steps, offer_tools, time.time() - started)

            message = response.message
            if response.done_reason == "length":
                logger.log_problem(step, "model reply was cut off (context or length limit reached)")

            if message.tool_calls and not offer_tools:
                # Tools were not offered, so this request cannot be run. Do not add it to the
                # history (a tool request without results would break the conversation).
                logger.log_problem(step, "model requested tools on the final step; request ignored")
                return self._finish(step, MAX_STEPS_TEXT)

            if not message.tool_calls:
                answer = clean_answer(message.content or "")
                if "<tool_call>" in answer:
                    logger.log_problem(step, "model wrote a tool call as plain text instead of a real tool call")
                    answer = MALFORMED_TOOL_CALL_TEXT
                elif not answer:
                    logger.log_problem(step, "model returned an empty answer")
                    answer = NO_ANSWER_TEXT
                return self._finish(step, answer)

            # The model asked for one or more tools. First remember its request...
            self.history.append(_assistant_tool_request(message))
            # ...then run each tool and add a matching result message.
            for call in message.tool_calls:
                name = call.function.name
                arguments = dict(call.function.arguments or {})
                result = self.registry.execute(name, arguments)
                logger.log_tool_call(step, name, arguments, result,
                                     self.registry.is_mock(name), self.registry.is_registered(name))
                self.tool_calls_made.append({"step": step, "name": name, "arguments": arguments, "result": result})
                self.history.append({"role": "tool", "tool_name": name, "content": _tool_result_text(result)})

        # Not reachable: the last step never runs tools. Kept as a safety net.
        return self._finish(self.max_steps, MAX_STEPS_TEXT)

    def _finish(self, step, answer):
        """Save the final answer in the history and return it."""
        # Do not let the answer claim an action (scheduled, saved, recorded)
        # that no tool actually completed while answering this message.
        problems = find_unverified_claims(answer, self.tool_calls_made)
        if problems:
            for problem in problems:
                logger.log_problem(step, f"UNVERIFIED CLAIM: {problem}")
            answer = add_unverified_warning(answer, problems)
        logger.log_final_answer(step, answer)
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


def _tool_result_text(result):
    """Turn a tool result into text for the model, shortened if it is very long."""
    text = json.dumps(result, ensure_ascii=False)
    limit = config.MAX_TOOL_RESULT_CHARS
    if len(text) > limit:
        text = text[:limit] + f"... [result shortened: {len(text) - limit} more characters not shown]"
    return text


def clean_answer(text):
    """Remove any reasoning the model leaked into its answer (text before '</think>')."""
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return text.strip()
