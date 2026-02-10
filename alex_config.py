import re

def build_system_prompt(pinned_memories: list[str], seed_summary: str | None = None, working_background: str | None = None) -> str:
    parts = []

    # Seed memory — the foundation of personality
    if seed_summary:
        parts.append(seed_summary.strip())

    # Pinned memories — the emotional heart of the dialogue
    if pinned_memories:
        parts.append("\n".join(pinned_memories))

    # Recent rhythm and tone
    if working_background:
        parts.append(working_background.strip())

    return "\n\n".join(parts).strip()

def postprocess_text(text: str) -> str:
    cleaned = text
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned
