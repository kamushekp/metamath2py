from __future__ import annotations

import os

from agents import Agent, ModelSettings

from saplings.dtos.tasks.patches.patch_set import PatchSetList
from saplings.tools.metamath_tools import search_tool

THEOREM_BOOTSTRAP_INSTRUCTIONS = (
    "You bootstrap a formal theorem state from natural-language goal text. "
    "Input is JSON with top-level keys 'requested_patch_sets' and 'trajectory'. "
    "Output must be PatchSetList with theorem_ops only (no proof_ops yet). "
    "When theorem is empty, build a coherent theorem state in one patch candidate: "
    "set label, floating args, essential arg names, premises, and assertion. "
    "Strict schema rules: "
    "AddFloating.value must be ONLY variable name (e.g., ph), not 'wff ph'. "
    "AddEssential.value must be ONLY essential key name (e.g., essential_1). "
    "AddPremise.left must reference an essential key; AddPremise.right must be a full formula starting with '|-'. "
    "ReplaceAssertion.new_assertion must start with '|-'. "
    "Use search_tool for related theorems/patterns but never invent malformed syntax. "
    "If confidence is low, still return best structured draft instead of looping."
)


def create_theorem_bootstrap_agent(model: str | None = None) -> Agent:
    selected_model = (model or os.getenv("SAPLINGS_BOOTSTRAP_MODEL") or "gpt-5-mini").strip()
    settings = ModelSettings(tool_choice="auto")
    return Agent(
        name="Theorem Bootstrap",
        instructions=THEOREM_BOOTSTRAP_INSTRUCTIONS,
        model=selected_model,
        tools=[search_tool],
        output_type=PatchSetList,
        model_settings=settings,
        reset_tool_choice=True,
    )
