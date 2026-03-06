from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional
import openai
from openai.resources.chat import Completions

LOGGER = logging.getLogger(__name__)

# Pricing per million tokens (input, output)
# Approximate as of late 2024/early 2025
PRICING_PER_1M: Dict[str, tuple[float, float]] = {
    # GPT-4o
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-2024-08-06": (2.50, 10.00),
    "gpt-4o-2024-05-13": (5.00, 15.00),
    
    # GPT-4o mini
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o-mini-2024-07-18": (0.15, 0.60),

    # GPT-4 Turbo
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4-turbo-2024-04-09": (10.00, 30.00),
    
    # GPT-3.5 Turbo
    "gpt-3.5-turbo-0125": (0.50, 1.50),
    "gpt-3.5-turbo": (0.50, 1.50),

    # o1
    "o1-preview": (15.00, 60.00),
    "o1-mini": (3.00, 12.00),
    
    # Aliases
    "gpt-5.2": (2.50, 10.00), # Assuming alias for gpt-4o class model in this project
    "gpt-5-mini": (0.15, 0.60), # Assuming alias for gpt-4o-mini class model
    "gpt-5-pro": (15.00, 60.00), # Assuming alias for o1 class model
}
DEFAULT_PRICING = (5.00, 15.00) # Conservative default

class BudgetExceededError(Exception):
    """Raised when the cost limit is exceeded."""
    pass

class CostTracker:
    _instance: Optional[CostTracker] = None
    _lock = threading.Lock()

    def __new__(cls) -> CostTracker:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self.total_cost: float = 0.0
        self.limit: float = 5.0
        self._tracking_active: bool = False
        self._original_create: Optional[Any] = None

    def set_limit(self, limit: float) -> None:
        self.limit = limit
        LOGGER.info(f"OpenAI cost limit set to ${self.limit:.2f}")

    def get_cost(self) -> float:
        return self.total_cost
    
    def reset_cost(self) -> None:
        with self._lock:
            self.total_cost = 0.0

    def check_budget(self) -> None:
        if self.total_cost >= self.limit:
            msg = f"OpenAI API budget exceeded: ${self.total_cost:.4f} >= ${self.limit:.2f}"
            LOGGER.error(msg)
            raise BudgetExceededError(msg)

    def add_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        price_in, price_out = PRICING_PER_1M.get(model, DEFAULT_PRICING)
        
        # Fallback for exact model versions not in dict (e.g. "gpt-4o-2024-08-06")
        if model not in PRICING_PER_1M:
             # Try prefix matching
            for key, (pi, po) in PRICING_PER_1M.items():
                if model.startswith(key):
                    price_in, price_out = pi, po
                    break

        cost = (input_tokens / 1_000_000) * price_in + (output_tokens / 1_000_000) * price_out
        
        with self._lock:
            self.total_cost += cost
            try:
                self.check_budget()
            except BudgetExceededError:
                # We raise here to stop immediately, but the cost is already added
                raise
        
        return cost

    def start_tracking(self) -> None:
        with self._lock:
            if self._tracking_active:
                return
            
            LOGGER.info("Starting OpenAI cost tracking")
            self._original_create = Completions.create
            
            def patched_create(*args, **kwargs):
                # Check budget before request
                self.check_budget()
                
                # Execute request
                response = self._original_create(*args, **kwargs)
                
                # Calculate cost from usage
                try:
                    usage = response.usage
                    if usage:
                        model = response.model
                        self.add_cost(
                            model, 
                            usage.prompt_tokens, 
                            usage.completion_tokens
                        )
                        LOGGER.info(f"OpenAI Call: {model} | Cost: ${self.total_cost:.4f} / ${self.limit:.2f}")
                except Exception as e:
                    LOGGER.warning(f"Failed to track cost for request: {e}")
                
                return response

            Completions.create = patched_create
            self._tracking_active = True

    def stop_tracking(self) -> None:
        with self._lock:
            if not self._tracking_active or not self._original_create:
                return
            
            Completions.create = self._original_create
            self._original_create = None
            self._tracking_active = False
            LOGGER.info("Stopped OpenAI cost tracking")

# Convenience implementation
tracker = CostTracker()
