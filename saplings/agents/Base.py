from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Optional, Tuple

from agents import ItemHelpers, RunConfig, Runner
from agents.exceptions import MaxTurnsExceeded

from saplings.dtos import Message, Node
from saplings.evaluator import Evaluator
from saplings.prompts import AGENT_PROMPT
from saplings.agents.factories import serialize_messages_for_runner


@dataclass
class Candidate:
    """Container describing a single branch returned by an Agents SDK run."""

    messages: List[Message]
    context_items: List[Any]
    run_result: Any


class BaseAgent(object):
    def __init__(
        self,
        agent_factory: Callable[[str, int], Any],
        model_name: Optional[str] = None,
        evaluator: Optional[Evaluator] = None,
        prompt: str = AGENT_PROMPT,
        b_factor: int = 3,
        max_depth: int = 5,
        threshold: float = 1.0,
        verbose: bool = True,
        parallel_tool_calls: bool = False,
        update_prompt: Optional[callable] = None,
    ):
        self.agent_factory = agent_factory
        self.model_name = model_name
        self.prompt = prompt
        self.update_system_prompt = update_prompt if update_prompt else lambda _: prompt
        self.b_factor = b_factor
        self.max_depth = max_depth
        self.threshold = threshold
        self.verbose = verbose
        self.parallel_tool_calls = parallel_tool_calls
        self.max_tool_call_tokens = 2048
        self.step_max_turns = 2
        self.candidate_temperature = 1.0
        self.evaluator = evaluator if evaluator else Evaluator(
            model_name=model_name,
            prompt=self.prompt,
        )

    # ------------------------------------------------------------------
    # Logging utilities
    # ------------------------------------------------------------------
    def log(self, message: str):
        if not self.verbose:
            return

        bold_yellow = "\033[1;33m"
        reset = "\033[0m"

        print(f"{bold_yellow}SAPLINGS LOG:{reset} {message}")

    # ------------------------------------------------------------------
    # Node classification helpers
    # ------------------------------------------------------------------
    def is_output_node(self, node: Node) -> bool:
        return any(message.role == "assistant" for message in node.messages)

    def is_terminal_node(self, node: Node) -> bool:
        if self.is_solution_node(node):
            return True
        if self.is_output_node(node):
            return True
        if node.depth >= self.max_depth:
            return True
        return False

    def is_solution_node(self, node: Node) -> bool:
        return node.score >= self.threshold and self.is_output_node(node)

    def get_best_node(self, root: Node) -> Node:
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

    def update_prompts(self, trajectory: List[Message]):
        self.prompt = self.update_system_prompt(trajectory)

    # ------------------------------------------------------------------
    # Runner helpers
    # ------------------------------------------------------------------
    def _candidate_key(self, messages: Iterable[Message]) -> Tuple[Any, ...]:
        signature: List[Any] = []
        for message in messages:
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

    def _message_from_assistant(self, item: Any) -> Optional[Message]:
        text = None
        if ItemHelpers:
            try:
                text = ItemHelpers.text_message_output(item)
            except Exception:
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
            if item_type == "message_output_item":
                assistant_message = self._message_from_assistant(item)
                if assistant_message:
                    messages.append(assistant_message)
        return messages

    def _build_agent(self):
        return self.agent_factory(self.prompt, self.max_tool_call_tokens)

    # ------------------------------------------------------------------
    # Search helpers
    # ------------------------------------------------------------------
    def generate_candidates(
        self, node: Node, messages: List[Message], n: Optional[int] = None
    ) -> List[Candidate]:
        sample_count = n if n else self.b_factor
        agent = self._build_agent()
        runner_input = self._prepare_runner_input(node, messages)

        candidates: List[Candidate] = []
        seen: set[Tuple[Any, ...]] = set()
        attempts = max(sample_count * 3, sample_count)

        for _ in range(attempts):
            try:
                run_result = Runner.run_sync(
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

    def evaluate(self, node: Node, messages: List[Message] = []) -> Node:
        trajectory = messages + node.get_trajectory()
        evaluation = self.evaluator.run(trajectory)
        node.set_evaluation(evaluation)
        return node

    def expand(self, node: Node, messages: List[Message], run_eval: bool = True):
        if self.is_terminal_node(node):
            self.log(f"\033[1;31mReached terminal node\033[0m\n\n{node}\n")
            return

        self.log(f"Expanding node\n\n{node}\n")

        trajectory = messages + node.get_trajectory()
        self.update_prompts(trajectory)

        candidates = self.generate_candidates(node, messages)
        if not candidates:
            self.log("No candidates generated by runner.")
            return

        children: List[Node] = []
        for candidate in candidates:
            child = Node(
                candidate.messages,
                parent=node,
                context_items=candidate.context_items,
            )
            children.append(child)

            for message in candidate.messages:
                message.parent_id = node.id
                message.id = child.id
                yield message

        if run_eval:
            for child in children:
                evaluated_child = self.evaluate(child, messages)
                if evaluated_child.messages:
                    final_message = evaluated_child.messages[-1]
                    final_message.score = evaluated_child.score
                    yield final_message

        self.log(
            f"Generated {len(children)} children\n\n"
            + "\n\n".join(str(child) for child in children)
            + "\n"
        )

        node.add_children(children)

    # ------------------------------------------------------------------
    # Execution entrypoints
    # ------------------------------------------------------------------
    def run(
        self, prompt: str, messages: Optional[List[Message]] = None, **kwargs
    ) -> Any:
        last_item = None
        for item in self.run_iter(prompt, messages or [], **kwargs):
            last_item = item
        return last_item

    def run_iter(
        self, prompt: str, messages: Optional[List[Message]] = None, **kwargs
    ) -> Iterable[Any]:
        raise NotImplementedError
