"""
antigravity_adk_integration.py - Integration with Google Antigravity Python SDK (google-antigravity).
Demonstrates launching the Sentinel agent within the Antigravity local agent runtime.
"""

import asyncio
import sys
from typing import Dict, Any

# Google Antigravity Python SDK imports
# pip install google-antigravity
try:
    from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
except ImportError:
    # Fallback dummy for development/linting outside installed runtime
    Agent = None
    LocalAgentConfig = None
    CapabilitiesConfig = None

from sentinel_agent import SKEPTIC_SYSTEM_INSTRUCTIONS
from schemas import CheckShelterReadinessInput, HazardType


async def run_antigravity_sentinel():
    """Runs the Sentinel Agent using the official Google Antigravity Python SDK."""
    if Agent is None:
        print("[NOTICE] To run with live Antigravity binary, install: pip install google-antigravity")
        return

    config = LocalAgentConfig(
        system_instructions=SKEPTIC_SYSTEM_INSTRUCTIONS,
        capabilities=CapabilitiesConfig(
            # Enable tool execution capabilities
            allow_custom_tools=True,
            allow_network=True
        ),
    )

    prompt = (
        "Run an evacuation readiness grounding audit for County FIPS 12086 "
        "under hurricane hazard conditions with min_vulnerability_score 0.20. "
        "Validate physical ground-truth and last-mile accessibility."
    )

    print(f"Spawning Antigravity Agent with Skeptic Sentinel instructions...")
    async with Agent(config) as agent:
        response = await agent.chat(prompt)

        # Stream thoughts
        async for thought in response.thoughts:
            print(f"[Sentinel Thinking] {thought}")

        # Stream tool invocations
        async for call in response.tool_calls:
            print(f"[Sentinel Tool Call] {call.name} -> {call.args}")

        # Stream generated output tokens
        print("\n--- FINAL READINESS BRIEF ---")
        async for token in response:
            sys.stdout.write(token)
            sys.stdout.flush()
        print()


if __name__ == "__main__":
    asyncio.run(run_antigravity_sentinel())
