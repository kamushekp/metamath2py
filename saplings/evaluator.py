# Standard library
from statistics import mean
from typing import List, Optional

# Third party
from agents import Runner
from pydantic import BaseModel, Field

# Local
from saplings.dtos import Message, Evaluation
from saplings.prompts import EVAL_PROMPT
from saplings.agents.factories import serialize_messages_for_runner
from saplings.agents.predefined import create_evaluator_agent, EvaluationPayload


class Evaluator(object):
    def __init__(
        self,
        model_name: Optional[str] = None,
        n_samples: int = 1,
        prompt: str = EVAL_PROMPT,
    ):
        self.model_name = model_name
        self.n_samples = n_samples
        self.prompt = prompt
        self.max_output_tokens = 1024
        self.agent = create_evaluator_agent(
            model_name=self.model_name,
            max_output_tokens=self.max_output_tokens,
        )

    async def _run_single(self, trajectory: List[Message]) -> Evaluation:
        runner_input = serialize_messages_for_runner(trajectory)
        result = await Runner.run(self.agent, input=runner_input)
        payload = result.final_output_as(EvaluationPayload)
        normalized = max(0.0, min(payload.score, 10.0)) / 10.0
        return Evaluation(score=normalized, reasoning=payload.reasoning)

    async def run(self, trajectory: List[Message]) -> Evaluation:
        evaluations = []
        for _ in range(max(1, self.n_samples)):
            evaluations.append(await self._run_single(trajectory))

        primary = evaluations[0]
        primary.score = mean(e.score for e in evaluations)
        return primary
