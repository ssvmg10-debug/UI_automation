"""
Quick start script for Enterprise UI Automation Platform.
Run this to test the platform with a simple example.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.orchestrator import AutomationOrchestrator
from app.telemetry.logger import setup_logging

# Setup logging
setup_logging(log_level="INFO", console=True)


async def main():
    """Run a simple test case."""
    
    print("=" * 60)
    print("  Enterprise UI Automation Platform - Quick Start")
    print("=" * 60)
    print()
    
    # Simple test case
    test_instruction = """
    Navigate to https://example.com
    """
    
    print("Test Case:")
    print(test_instruction)
    print()
    
    # Create orchestrator
    orchestrator = AutomationOrchestrator(
        max_recovery_attempts=2,
        headless=False  # Set to True for headless mode
    )
    
    # Run test
    print("Executing test...")
    print("-" * 60)
    
    result = await orchestrator.run(test_instruction)
    
    print("-" * 60)
    print()
    
    # Display results
    if result["success"]:
        print("✅ TEST PASSED")
    else:
        print("❌ TEST FAILED")
        print(f"Error: {result.get('error')}")
    
    print()
    print(f"Steps Executed: {result['steps_executed']}/{result['total_steps']}")
    print()
    
    # Show step details
    print("Step Details:")
    for i, step_result in enumerate(result["results"], 1):
        status = "✓" if step_result["success"] else "✗"
        print(f"  Step {i}: {status}")
        if step_result.get("error"):
            print(f"    Error: {step_result['error']}")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
