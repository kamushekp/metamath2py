# Standard library
from typing import Any, Callable, List, Optional

# Local
from saplings.agents.Base import BaseAgent
from saplings.dtos import Node, Message
from saplings.prompts import AGENT_PROMPT


class COTAgent(BaseAgent):
    def __init__(
        self,
        agent_factory: Callable[[str, int], Any],
        model_name: Optional[str] = None,
        prompt: str = AGENT_PROMPT,
        max_depth: int = 5,
        verbose: bool = True,
        parallel_tool_calls: bool = False,
        update_prompt: Optional[callable] = None,
    ):
        super().__init__(
            agent_factory,
            model_name,
            evaluator=None,
            prompt=prompt,
            b_factor=1,
            max_depth=max_depth,
            threshold=1.0,
            verbose=verbose,
            parallel_tool_calls=parallel_tool_calls,
            update_prompt=update_prompt,
        )

    def should_terminate(self, node: Node) -> bool:
        return self.is_terminal_node(node)

    def run_iter(self, prompt: str, messages: List[Message] | None = None):
        messages = list(messages or [])
        self.log(f"Running a ReAct sequence (no search)\n\n\033[37m{prompt}\033[0m\n")

        curr_node = Node([Message.user(prompt)])
        while not self.should_terminate(curr_node):
            for item in self.expand(curr_node, messages, run_eval=False):
                yield item

            curr_node = curr_node.children[0]

        trajectory = curr_node.get_trajectory()
        score = curr_node.score
        is_solution = self.is_solution_node(curr_node)

        self.log(
            f"\033[1;32mFinal trajectory:\033[0m\n\n"
            + "\n".join(str(m) for m in trajectory)
        )

        yield (trajectory, score, is_solution)
