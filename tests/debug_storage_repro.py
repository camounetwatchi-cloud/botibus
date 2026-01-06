
import numpy as np
import pandas as pd
import pytest
from contextlib import contextmanager
import time

# 1. Test Sanitization (Copy of the new logic to verify it works)
def _sanitize_value(value):
    """Copy of the function from src/data/storage.py for verification"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
        
    # Handle numpy scalars (np.float64, np.int64, etc.)
    if hasattr(value, 'item'):
        return value.item()
        
    # Explicit numpy type checks (fallback)
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
        
    # Handle pandas Timestamp
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
        
    return value

def test_sanitize():
    print("\n--- Testing Sanitization ---")
    val_float = np.float64(1.23)
    sanitized_float = _sanitize_value(val_float)
    print(f"Float Input: {type(val_float)} {val_float}")
    print(f"Float Output: {type(sanitized_float)} {sanitized_float}")
    assert isinstance(sanitized_float, float)
    
    val_int = np.int64(42)
    sanitized_int = _sanitize_value(val_int)
    print(f"Int Input: {type(val_int)} {val_int}")
    print(f"Int Output: {type(sanitized_int)} {sanitized_int}")
    assert isinstance(sanitized_int, int)
    
    print("Sanitization Tests Passed!")

# 2. Test Generator/Context Manager behavior (Simulating the NEW structure)
@contextmanager
def my_context_manager_fixed():
    conn = "CONNECTION_ESTABLISHED"
    
    # Simulate Try Connect Logic
    connect_success = True 
    
    if connect_success:
        # If successful, we yield.
        # We DO NOT wrap this yield in a try/except that catches the query error and tries to re-yield
        try:
            yield conn
        finally:
            print("Closing connection cleanup")

def test_generator_fixed():
    print("\n--- Testing Fixed Generator ---")
    try:
        with my_context_manager_fixed() as conn:
            print(f"Got: {conn}")
            # Simulate a query error happening OUTSIDE the generator's internal try/except
            raise ValueError("Simulated Query Error")
    except ValueError as e:
        print(f"Outer exception caught correctly: {e}")
        # If we reach here without "generator didn't stop" error, it's fixed.
    except RuntimeError as e:
        print(f"FATAL: Generator error: {e}")
        raise e

if __name__ == "__main__":
    test_sanitize()
    test_generator_fixed()
