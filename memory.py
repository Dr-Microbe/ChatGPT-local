import sqlite3
from db import DB_PATH

def save_message(conversation_id: str, role: str, content: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conversation_id, role, content),
    )
    con.commit()
    con.close()

def load_recent_messages(conversation_id: str, limit: int = 48):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        """
        SELECT role, content FROM messages
        WHERE conversation_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (conversation_id, limit),
    )
    rows = cur.fetchall()
    con.close()

    rows = list(reversed(rows))
    return [{"role": r, "content": c} for (r, c) in rows]

def add_pinned_memory(conversation_id: str, content: str):
    if not content:
        return
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO pinned_memories (conversation_id, content) VALUES (?, ?)",
        (conversation_id, content),
    )
    con.commit()
    con.close()

def list_pinned_memories(conversation_id: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        """
        SELECT content FROM pinned_memories
        WHERE conversation_id = ?
        ORDER BY id ASC
        """,
        (conversation_id,),
    )
    rows = cur.fetchall()
    con.close()
    return [r[0] for r in rows]

import json
import os
from pathlib import Path

MEM_ROOT = Path("memories")
SEED_FILE = MEM_ROOT / "seed" / "alex_seed.json"
WORKING_FILE = MEM_ROOT / "working" / "buffer.json"

def _ensure_dirs():
    (MEM_ROOT / "seed").mkdir(parents=True, exist_ok=True)
    (MEM_ROOT / "working").mkdir(parents=True, exist_ok=True)
    (MEM_ROOT / "exports").mkdir(parents=True, exist_ok=True)
    (MEM_ROOT / "pinned").mkdir(parents=True, exist_ok=True)

def load_seed() -> dict | None:
    _ensure_dirs()
    if not SEED_FILE.exists():
        return None

    try:
        raw = SEED_FILE.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        raw = SEED_FILE.read_text(encoding="cp1251").strip()
        SEED_FILE.write_text(raw, encoding="utf-8")

    if not raw:
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None

def save_seed(seed: dict):
    _ensure_dirs()
    SEED_FILE.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")

def seed_summary_text() -> str | None:
    seed = load_seed()
    if not seed:
        return None
    # seed can be anything, but we expect a 'summary' field
    return seed.get("summary") or None

def load_working_background(max_items: int = 12) -> str | None:
    _ensure_dirs()
    if not WORKING_FILE.exists():
        return None
    try:
        raw = WORKING_FILE.read_text(encoding="utf-8")
    except UnicodeDecodeError:
    # try Windows encoding and normalize file
        raw = WORKING_FILE.read_text(encoding="cp1251")
        WORKING_FILE.write_text(raw, encoding="utf-8")

    data = json.loads(raw)
    
    items = data.get("items", [])[-max_items:]
    if not items:
        return None
    # format gently without commands
    lines = []
    for it in items:
        who = 'You' if it.get("role") == "user" else "Алекс"
        lines.append(f"{who}: {it.get('content','')}".strip())
    return "\n".join(lines).strip()

def append_working(role: str, content: str, max_keep: int = 24):
    _ensure_dirs()
    data = {"items": []}
    if WORKING_FILE.exists():
        data = json.loads(WORKING_FILE.read_text(encoding="utf-8"))
    items = data.get("items", [])
    items.append({"role": role, "content": content})
    data["items"] = items[-max_keep:]
    WORKING_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

from datetime import datetime

def load_all_messages(conversation_id: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        """
        SELECT role, content FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
        """,
        (conversation_id,),
    )
    rows = cur.fetchall()
    con.close()
    return [{"role": r, "content": c} for (r, c) in rows]

def export_conversation_to_file(conversation_id: str) -> dict:
    _ensure_dirs()

    messages = load_all_messages(conversation_id)
    pinned = list_pinned_memories(conversation_id)

    payload = {
        "schema": "alex-local.conversation.v1",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "conversation_id": conversation_id,
        "pinned_memories": pinned,
        "messages": messages,
    }

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    short = conversation_id[:8]
    out = MEM_ROOT / "exports" / f"{ts}_{short}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    payload["saved_as"] = str(out)
    return payload

# memory.py (add the to end)
import re
import uuid
from datetime import datetime

def create_conversation(name: str) -> str:
    conv_id = str(uuid.uuid4())
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO conversations (id, name) VALUES (?, ?)",
        (conv_id, name.strip() or "Dialogue"),
    )
    con.commit()
    con.close()
    return conv_id

def list_conversations():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT id, name, created_at
        FROM conversations
        ORDER BY datetime(created_at) DESC
    """)
    rows = cur.fetchall()
    con.close()
    return [{"id": r[0], "name": r[1], "created_at": r[2]} for r in rows]

def _decode_bytes(b: bytes) -> str:
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("cp1251", errors="replace")

def _parse_transcript(text: str):
    """
    Supported formats:
    - You said: ... / ChatGPT said: ...
    - Alex: ... / Assistant: ...
    - Text may also follow on the next line.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    def flush(buf_role, buf):
        content = "\n".join(buf).strip()
        if content:
            out.append({"role": buf_role, "content": content})

    out = []
    role = None
    buf = []

    # start-of-turn markers
    you_mark = re.compile(r"^\s*You said:\s*$", re.IGNORECASE)
    gpt_mark = re.compile(r"^\s*(ChatGPT said:|Assistant said:)\s*$", re.IGNORECASE)
    alex_mark = re.compile(r"^\s*Alex:\s*$", re.IGNORECASE)

    for ln in lines:
        s = ln.rstrip()

        if you_mark.match(s):
            if role:
                flush(role, buf)
            role, buf = "user", []
            continue

        if gpt_mark.match(s) or alex_mark.match(s):
            if role:
                flush(role, buf)
            role, buf = "assistant", []
            continue
            continue

        # ignore empty headers like 'Alex:' if no role is defined yet
        if role is None and not s.strip():
            continue

        # normal content line
        if role is None:
            # if the file has no markers, treat everything as a single user message
            role = "user"
        buf.append(s)

    if role:
        flush(role, buf)

    return out

def import_transcript_text(name: str, raw_text: str) -> str:
    msgs = _parse_transcript(raw_text)
    conv_id = create_conversation(name)

    # save messages to messages table
    for m in msgs:
        save_message(conv_id, m["role"], m["content"])

    return conv_id

def rename_conversation(conv_id: str, new_name: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "UPDATE conversations SET name = ? WHERE id = ?",
        (new_name.strip(), conv_id),
    )
    con.commit()
    con.close()

def delete_conversation(conv_id: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
    cur.execute("DELETE FROM pinned_memories WHERE conversation_id = ?", (conv_id,))
    cur.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    con.commit()
    con.close()

