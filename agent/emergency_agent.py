"""
emergency_agent.py - Main Emergency Response & Evacuation Coordinator Agent.
"""
from typing import TYPE_CHECKING

def __getattr__(name: str):
    if name == "emergency_agent":
        from .agent import emergency_agent
        return emergency_agent
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
