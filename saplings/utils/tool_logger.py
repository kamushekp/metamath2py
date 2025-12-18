import functools
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# Configure a specific logger for tools
logger = logging.getLogger("tool_usage")
logger.setLevel(logging.INFO)

# Ensure the log file exists
LOG_FILE = Path("logs/tool_usage.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# File handler for JSONL logging
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(file_handler)


def log_tool_call(func: Callable) -> Callable:
    """
    Decorator to log tool inputs, outputs, and execution time to a JSONL file.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        tool_name = func.__name__
        
        # Capture inputs (convert to string/dict where possible)
        inputs = {
            "args": [str(a) for a in args],
            "kwargs": {k: str(v) for k, v in kwargs.items()}
        }

        error = None
        result = None
        
        try:
            result = await func(*args, **kwargs)
            # Try to serialize result, fallback to string
            try:
                # If it's a Pydantic model or similar, it might have .dict() or .model_dump()
                if hasattr(result, "model_dump"):
                    serialized_result = result.model_dump()
                elif hasattr(result, "dict"):
                    serialized_result = result.dict()
                else:
                    serialized_result = result
                
                # Test JSON serialization
                json.dumps(serialized_result)
                output_log = serialized_result
            except (TypeError, OverflowError):
                output_log = str(result)
                
        except Exception as e:
            error = str(e)
            raise e
        finally:
            duration = time.time() - start_time
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "duration_seconds": duration,
                "inputs": inputs,
                "output": output_log if error is None else None,
                "error": error,
                "success": error is None
            }
            
            logger.info(json.dumps(log_entry))
            
        return result

    return wrapper
