from pathlib import Path

def load_agent_context() -> str:
    """Loads the AGENT_CONTEXT.md file contents dynamically."""
    context_file = Path(__file__).parent / "AGENT_CONTEXT.md"
    if context_file.exists():
        return context_file.read_text(encoding="utf-8")
    return ""
