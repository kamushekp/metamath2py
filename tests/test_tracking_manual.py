import sys
from unittest.mock import MagicMock
from saplings.utils.tracking import CostTracker, BudgetExceededError
from openai.types.completion_usage import CompletionUsage
from openai.types.chat.chat_completion import ChatCompletion
from openai.resources.chat import Completions

def test_manual_tracking():
    tracker = CostTracker()
    tracker.set_limit(0.0001) # Very low limit
    tracker.start_tracking()
    
    print(f"Initial cost: {tracker.get_cost()}")
    
    # Mocking the actual API call since we don't want to make real calls in this test
    # and we want to control usage
    mock_response = MagicMock(spec=ChatCompletion)
    mock_response.usage = CompletionUsage(prompt_tokens=1000, completion_tokens=100, total_tokens=1100)
    mock_response.model = "gpt-4o"
    
    # We need to mock the _original_create because we monkeypatched it
    # But for the test to work with the Patched method, we need to ensure the UNDERLYING call returns our mock
    # The monkeypatch wrapped the _original_create.
    
    # However, since we might fail to actually make a real call without credentials in this env,
    # let's just test the add_cost logic directly primarily, and the patching mechanics secondary.
    
    # Test 1: Direct cost addition
    print("Test 1: Direct cost addition")
    try:
        # 1000 input tokens * $2.50/1M = $0.0025
        # 100 output tokens * $10.00/1M = $0.001
        # Total = ~0.0035, which is > 0.0001 limit
        tracker.add_cost("gpt-4o", 1000, 100) 
        print("FAILED: Should have raised BudgetExceededError")
    except BudgetExceededError as e:
        print(f"SUCCESS: Caught expected error: {e}")
    
    tracker.reset_cost()
    print(f"Cost after reset: {tracker.get_cost()}")
    
    # Test 2: Patching (Mocking the inner call)
    print("\nTest 2: Patching mechanism")
    tracker.set_limit(1.0)
    
    original_func = tracker._original_create
    tracker._original_create = MagicMock(return_value=mock_response)
    
    try:
        # calling the now-patched Completions.create
        Completions.create(model="gpt-4o", messages=[])
        print(f"Cost after mocked call: {tracker.get_cost():.6f}")
        
        if tracker.get_cost() > 0:
            print("SUCCESS: Cost increased")
        else:
            print("FAILED: Cost did not increase")
            
    finally:
        # Restore for safety
        tracker._original_create = original_func
        tracker.stop_tracking()

if __name__ == "__main__":
    test_manual_tracking()
