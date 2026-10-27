from pathlib import Path

def load_agent_context() -> str:
    """Loads the AGENT_CONTEXT.md file contents dynamically."""
    context_file = Path(__file__).parent / "AGENT_CONTEXT.md"
    if context_file.exists():
        content = context_file.read_text(encoding="utf-8")
        # In ADK, inject_session_state attempts to resolve {var_name} from session state.
        # Replace template placeholders to prevent KeyErrors during instruction compilation.
        return content.replace("{lat}", "<lat>").replace("{long}", "<long>")
    return ""
