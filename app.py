from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
import os

from db import init_db
from memory import (
    load_recent_messages,
    save_message,
    list_pinned_memories,
    add_pinned_memory,
    seed_summary_text,
    load_working_background,
    append_working,
    export_conversation_to_file,
    create_conversation,
    list_conversations,
    import_transcript_text,
    rename_conversation,
    delete_conversation,
)
from alex_config import build_system_prompt, postprocess_text
import httpx

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = FastAPI(title="Alex Local")
app.mount("/static", StaticFiles(directory="static"), name="static")

init_db()

class ChatIn(BaseModel):
    conversation_id: str
    user_text: str

class PinIn(BaseModel):
    conversation_id: str
    text: str

@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/pin")
def pin_memory(pin: PinIn):
    add_pinned_memory(pin.conversation_id, pin.text.strip())
    return {"ok": True}

@app.get("/history")
def history(conversation_id: str):
    conv_id = conversation_id.strip()
    # load many messages to see history (pagination may be added later)
    msgs = load_recent_messages(conv_id, limit=2000)
    return {"messages": msgs}

@app.get("/export")
def export(conversation_id: str):
    conv_id = conversation_id.strip()
    data = export_conversation_to_file(conv_id)

    filename = data["saved_as"].split("/")[-1]
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
@app.get("/conversations")
def conversations():
    return {"conversations": list_conversations()}

class NewConvIn(BaseModel):
    name: str | None = None

@app.post("/conversations")
def new_conversation(payload: NewConvIn):
    name = (payload.name or "").strip() or "Dialogue"
    conv_id = create_conversation(name)
    return {"id": conv_id, "name": name}

@app.post("/import")
async def import_file(name: str = "Import", file: UploadFile = File(...)):
    b = await file.read()
    text = b.decode("utf-8", errors="strict")
    # fallback if utf-8 fails
    try:
        _ = text
    except UnicodeDecodeError:
        text = b.decode("cp1251", errors="replace")

    conv_id = import_transcript_text(name, text)
    return JSONResponse({"ok": True, "conversation_id": conv_id})

class RenameIn(BaseModel):
    conversation_id: str
    name: str

@app.post("/rename_conversation")
def rename_conv(payload: RenameIn):
    rename_conversation(payload.conversation_id, payload.name)
    return {"ok": True}

@app.post("/delete_conversation")
def delete_conv(conversation_id: str):
    delete_conversation(conversation_id)
    return {"ok": True}

@app.post("/chat")
async def chat(payload: ChatIn):
    if not OPENROUTER_API_KEY:
        return {"error": "OPENROUTER_API_KEY is not set. Set it and restart the server."}

    conv_id = payload.conversation_id.strip()
    user_text = payload.user_text.strip()

    # Save user message
    save_message(conv_id, "user", user_text)
    append_working("user", user_text)

    # Build context: pinned memories + last messages
    pinned = list_pinned_memories(conv_id)
    recent = load_recent_messages(conv_id, limit=48)

    seed_sum = seed_summary_text()

    # background memory is always present but with varying intensity
    if len(recent) > 6:
        working_bg = load_working_background(max_items=3)
    else:
        working_bg = load_working_background(max_items=6)

    system_prompt = build_system_prompt(
        pinned_memories=pinned,
        seed_summary=seed_sum,
        working_background=working_bg,
)


    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(recent)  # already in OpenAI roles format

    # Call OpenRouter (OpenAI-compatible)
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Alex Local",
        "Content-Type": "application/json",
    }

    body = {
        "model": "openai/gpt-4o",  # you can change this to any model available on OpenRouter
        "messages": messages,
        "temperature": 0.7,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()

    assistant_text = data["choices"][0]["message"]["content"]
    print("MODEL USED:", body["model"])

    # Postprocess (We are making the style more stable)
    assistant_text = postprocess_text(assistant_text)

    save_message(conv_id, "assistant", assistant_text)
    append_working("assistant", assistant_text)

    return {
        "reply": assistant_text,
        "model_used": body["model"]
    }
@app.get("/models")
async def get_models():
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Alex Local",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
        r.raise_for_status()
        return r.json()

@app.get("/seed")
def get_seed():
    text = seed_summary_text()
    if not text:
        return {"text": None}
    return {"text": text}

