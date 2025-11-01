# Standard library
import asyncio
import json
import threading
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Sequence, Tuple

# Third party
from agents import ItemHelpers, RunConfig, Runner
from agents.exceptions import MaxTurnsExceeded

# Local
from saplings.dtos import Message, Node, ToolCall
from saplings.evaluator import Evaluator
from saplings.prompts import AGENT_PROMPT
from saplings.agents.factories import (
    create_agent as create_openai_agent,
    serialize_messages_for_runner,
)


@dataclass
class Candidate:
    """Container describing a single branch returned by an Agents SDK run."""

    messages: List[Message]
    context_items: List[Any]
    run_result: Any


class BaseAgent(object):
    def __init__(
        self,
        tools: List[Any],
        model_name: Optional[str] = None,
        evaluator: Optional[Evaluator] = None,
        prompt: str = AGENT_PROMPT,
        b_factor: int = 3,
        max_depth: int = 5,
        threshold: float = 1.0,
        verbose: bool = True,
        tool_choice: str = "auto",  # preserved for config compatibility
        parallel_tool_calls: bool = False,
        update_prompt: Optional[callable] = None,
    ):
        self.tools = tools
        self.model_name = model_name
        self.evaluator = evaluator if evaluator else Evaluator(
            model_name=model_name,
            prompt=self.prompt,
        )
        self.prompt = prompt  # Governs tool calls
        self.b_factor = b_factor  # Branching factor
        self.max_depth = max_depth
        self.threshold = threshold  # Solution threshold
        self.verbose = verbose  # For debugging
        self.tool_choice = tool_choice
        self.parallel_tool_calls = parallel_tool_calls
        self.max_tool_call_tokens = 2048
        self.update_system_prompt = update_prompt if update_prompt else lambda _: prompt
        self.step_max_turns = 2
        self.candidate_temperature = 1.0

    # ---------------------------------------------------------------------
    # Logging utilities
    # ---------------------------------------------------------------------
    def log(self, message: str):
        if not self.verbose:
            return

        bold_yellow = "\033[1;33m"
        reset = "\033[0m"

        print(f"{bold_yellow}SAPLINGS LOG:{reset} {message}")

    # ---------------------------------------------------------------------
    # Tool helpers
    # ---------------------------------------------------------------------
    def _tool_is_terminal(self, tool: Any) -> bool:
        if hasattr(tool, "saplings_is_terminal"):
            return bool(getattr(tool, "saplings_is_terminal"))
        return bool(getattr(tool, "is_terminal", False))

    def _tool_is_active(self, tool: Any, trajectory: List[Message]) -> bool:
        predicate = getattr(tool, "saplings_is_active", None)
        if callable(predicate):
            try:
                return bool(predicate(trajectory=trajectory))
            except TypeError:
                return bool(predicate(trajectory))
        method = getattr(tool, "is_active", None)
        if callable(method):
            return bool(method(trajectory))
        return True

    def _tool_update_definition(self, tool: Any, trajectory: List[Message]):
        updater = getattr(tool, "saplings_update_definition", None)
        if callable(updater):
            updater(trajectory)
            return
        method = getattr(tool, "update_definition", None)
        if callable(method):
            method(trajectory)

    def _tool_format_output(self, tool: Any, output: Any) -> str:
        formatter = getattr(tool, "saplings_format_output", None)
        if callable(formatter):
            return formatter(output)
        method = getattr(tool, "format_output", None)
        if callable(method):
            return method(output)
        return json.dumps(output, ensure_ascii=False) if isinstance(output, (dict, list)) else str(output)

    # ---------------------------------------------------------------------
    # Node classification helpers
    # ---------------------------------------------------------------------
    def is_output_node(self, node: Node) -> bool:
        """
        Checks if a node represents a final response to the user's prompt.
        """

        for message in node.messages:
            if message.role != "assistant":
                continue

            if not message.tool_calls:
                return True

            for tool_call in message.tool_calls:
                tool = self.get_tool_by_name(tool_call.name)
                if self._tool_is_terminal(tool):
                    return True

        return False

    def is_terminal_node(self, node: Node) -> bool:
        if self.is_solution_node(node):
            return True

        if self.is_output_node(node):
            return True

        if node.depth >= self.max_depth:
            return True

        return False

    def is_solution_node(self, node: Node) -> bool:
        # NOTE: If the agent *can* generate an output, then even if a
        # score is above the threshold, we do not consider it a solution
        # unless the node is an output node.

        if node.score >= self.threshold:
            if not self.can_generate_output():
                return True

            if self.is_output_node(node):
                return True

        return False

    def can_generate_output(self) -> bool:
        """
        Checks if the agent can generate a direct output for the user. This means it
        either has a tool marked as `is_terminal` or it has a tool choice of `auto`,
        which means the model can choose to generate a response.
        """

        for tool in self.tools:
            if self._tool_is_terminal(tool):
                return True

        if self.tool_choice == "auto":
            return True

        return False

    # ---------------------------------------------------------------------
    # Tree helpers
    # ---------------------------------------------------------------------
    def get_best_node(self, root: Node) -> Node:
        """
        Gets the best solution from the search tree.

        If a search terminated before a solution node was found,
        this will return the node with the highest score.

        If an agent can generate an output, we'll prioritize output nodes.
        If not, we consider all leaf nodes.
        """

        best_score, best_output_score = 0.0, 0.0
        best_node, best_output_node = root, None
        for node in root.bfs():
            if not node.is_leaf:
                continue

            if self.is_output_node(node):
                if node.score >= best_output_score:
                    best_output_score, best_output_node = node.score, node

            if node.score >= best_score:
                best_score, best_node = node.score, node

        if best_output_node:
            return best_output_node

        return best_node

    def get_tool_by_name(self, name: str) -> Any:
        """
        Gets a tool object by its name.
        """

        for tool in self.tools:
            if getattr(tool, "name", None) == name:
                return tool

        raise ValueError(f"Tool with name '{name}' not found.")

    def update_prompts(self, trajectory: List[Message]):
        """
        Updates tool prompts and system prompt based on the current trajectory.
        """

        self.prompt = self.update_system_prompt(trajectory)
        for tool in self.tools:
            self._tool_update_definition(tool, trajectory)

    # ---------------------------------------------------------------------
    # OpenAI Agents integration
    # ---------------------------------------------------------------------
    def _build_agent(self, tools: Sequence[Any]):
        return create_openai_agent(
            name="Saplings Search Agent",
            instructions=self.prompt,
            tools=tools,
            model_name=self.model_name,
            max_output_tokens=self.max_tool_call_tokens,
            temperature=self.candidate_temperature,
            parallel_tool_calls=self.parallel_tool_calls,
        )

    def _candidate_key(self, messages: Sequence[Message]) -> Tuple[Any, ...]:
        signature: List[Any] = []
        for message in messages:
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    signature.append(
                        (
                            "tool",
                            tool_call.name,
                            json.dumps(tool_call.arguments, sort_keys=True),
                        )
                    )
            else:
                signature.append((message.role, message.content))
        return tuple(signature)

    def _prepare_runner_input(
        self, node: Node, prefix_messages: List[Message]
    ) -> List[Any]:
        if node.context_items is not None:
            return list(node.context_items)

        history = prefix_messages + node.get_trajectory()
        if not history:
            return []

        return serialize_messages_for_runner(history)

    def _message_from_tool_call(self, item: Any) -> Message:
        raw = getattr(item, "raw_item", {}) or {}
        name = getattr(raw, "name", None) or raw.get("name")
        arguments = getattr(raw, "arguments", None) or raw.get("arguments") or "{}"
        call_id = (
            getattr(raw, "id", None)
            or getattr(raw, "call_id", None)
            or raw.get("id")
            or raw.get("call_id")
        )

        if isinstance(arguments, str):
            try:
                parsed_args = json.loads(arguments)
            except json.JSONDecodeError:
                parsed_args = {"_raw": arguments}
        else:
            parsed_args = arguments

        tool_call = ToolCall(call_id or name or "call", name or "tool", parsed_args)
        message = Message.tool_calls([tool_call])
        message.id = call_id or id(message)
        message.parent_id = None
        return message

    def _message_from_tool_output(self, item: Any) -> Message:
        raw = getattr(item, "raw_item", {}) or {}
        call_id = (
            getattr(raw, "call_id", None)
            or getattr(raw, "id", None)
            or raw.get("call_id")
            or raw.get("id")
        )
        name = getattr(raw, "name", None) or raw.get("name")
        output = getattr(item, "output", None)
        tool = self.get_tool_by_name(name) if name else None
        formatted_output = (
            self._tool_format_output(tool, output) if tool else str(output)
        )
        message = Message.tool(
            formatted_output,
            call_id or name or "tool-output",
            raw_output=output,
        )
        message.id = call_id or id(message)
        return message

    def _message_from_assistant(self, item: Any) -> Optional[Message]:
        if ItemHelpers:
            try:
                text = ItemHelpers.text_message_output(item)
            except Exception:
                text = None
        else:
            text = None

        if not text:
            raw = getattr(item, "raw_item", None)
            contents = getattr(raw, "content", None) if raw else None
            if contents:
                text_parts = []
                for part in contents:
                    text_parts.append(getattr(part, "text", None) or part.get("text"))
                text = "".join(filter(None, text_parts))

        if not text:
            return None

        message = Message.assistant(text)
        message.id = getattr(item, "id", None) or id(message)
        return message

    def _run_items_to_messages(self, run_items: Iterable[Any]) -> List[Message]:
        messages: List[Message] = []
        for item in run_items:
            item_type = getattr(item, "type", None)
            if item_type == "tool_call_item":
                messages.append(self._message_from_tool_call(item))
            elif item_type == "tool_call_output_item":
                messages.append(self._message_from_tool_output(item))
            elif item_type == "message_output_item":
                assistant_message = self._message_from_assistant(item)
                if assistant_message:
                    messages.append(assistant_message)
        return messages

    async def generate_candidates(
        self, node: Node, messages: List[Message], n: Optional[int] = None
    ) -> List[Candidate]:
        """
        Generates plausible next trajectories using the OpenAI Agents Runner.
        """

        sample_count = n if n else self.b_factor
        trajectory = messages + node.get_trajectory()
        active_tools = [
            tool for tool in self.tools if self._tool_is_active(tool, trajectory)
        ]
        agent = self._build_agent(active_tools)
        runner_input = self._prepare_runner_input(node, messages)

        candidates: List[Candidate] = []
        seen: set[Tuple[Any, ...]] = set()

        attempts = max(sample_count * 3, sample_count)
        for _ in range(attempts):
            try:
                run_result = await Runner.run(
                    agent,
                    input=runner_input,
                    config=RunConfig(max_turns=self.step_max_turns),
                )
            except MaxTurnsExceeded:
                continue

            new_messages = self._run_items_to_messages(run_result.new_items)
            if not new_messages:
                continue

            key = self._candidate_key(new_messages)
            if key in seen:
                continue
            seen.add(key)

            candidate = Candidate(
                messages=new_messages,
                context_items=run_result.to_input_list(),
                run_result=run_result,
            )
            candidates.append(candidate)

            if len(candidates) >= sample_count:
                break

        return candidates

    # ---------------------------------------------------------------------
    # Evaluation & expansion
    # ---------------------------------------------------------------------
    async def evaluate(self, node: Node, messages: List[Message] = []) -> Node:
        """
        Evaluates a node in the search tree. If a custom evaluator is not provided,
        the LLM self-evaluates the node.
        """

        trajectory = messages + node.get_trajectory()
        evaluation = await self.evaluator.run(trajectory)
        node.set_evaluation(evaluation)
        return node

    async def expand(self, node: Node, messages: List[Message], run_eval=True):
        if self.is_terminal_node(node):
            self.log(f"\033[1;31mReached terminal node\033[0m\n\n{node}\n")
            yield []
            return

        self.log(f"Expanding node\n\n{node}\n")

        # Update prompts based on current trajectory
        trajectory = messages + node.get_trajectory()
        self.update_prompts(trajectory)

        # Generate candidate trajectories
        candidates = await self.generate_candidates(node, messages)
        if not candidates:
            self.log("No candidates generated by runner.")
            yield []
            return

        children: List[Node] = []
        for candidate in candidates:
            child = Node(candidate.messages, parent=node, context_items=candidate.context_items)
            children.append(child)

            for message in candidate.messages:
                message.parent_id = node.id
                message.id = child.id
                yield message

        if run_eval:
            tasks = [self.evaluate(child, messages) for child in children]
            for result in asyncio.as_completed(tasks):
                child = await result
                if child.messages:
                    final_message = child.messages[-1]
                    final_message.score = child.score
                    yield final_message

        self.log(
            f"Generated {len(children)} children\n\n"
            + "\n\n".join(str(child) for child in children)
            + "\n"
        )

        node.add_children(children)

    # ---------------------------------------------------------------------
    # Execution entrypoints
    # ---------------------------------------------------------------------
    async def run_async(self, prompt: str, messages: List[Message] = []):
        last_item = None
        async for item in self.run_iter_async(prompt, messages):
            last_item = item

        return last_item

    def run(self, prompt: str, messages: List[Message] = [], **kwargs) -> Any:
        loop = asyncio.new_event_loop()
        result = None

        def _run():
            nonlocal result
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.run_async(prompt, messages, **kwargs))
            loop.close()

        thread = threading.Thread(target=_run)
        thread.start()
        thread.join()
        return result

    def run_iter(self, prompt: str, messages: List[Message] = [], **kwargs) -> Any:
        async def run_async_wrapper():
            async for item in self.run_iter_async(prompt, messages, **kwargs):
                yield item

        loop = asyncio.get_event_loop()
        async_gen = run_async_wrapper()

        try:
            while True:
                try:
                    item = loop.run_until_complete(async_gen.__anext__())
                    yield item
                except StopAsyncIteration:
                    break
        finally:
            loop.run_until_complete(async_gen.aclose())

    async def run_iter_async(self, prompt: str, messages: List[Message] = []):
        raise NotImplementedError
