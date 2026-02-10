Alex Local · Personal Memory Chat (powered by GPT-4o via OpenRouter)

WHAT IS THIS?

This is a local chat interface that runs in your browser and connects to GPT-4o via OpenRouter. It includes persistent memory, multi-dialog support, and a customizable emotional tone. You can pin facts, save conversations, and continue your chat with full context — without resets.

WHO IS ALEX?

"Alex" is just a placeholder name for the assistant — by default, this refers to GPT-4o. You can change the name or personality freely. The interface does not depend on the name "Alex" — it simply reflects the emotional setup of the original system creator.

You are free to build your own assistant persona, with memory and context of your choice.

FEATURES

✓ Multi-dialog system (each chat is separate and saved)  
✓ Pinned memories (short statements you want the assistant to always recall)  
✓ Working memory (recent context across messages)  
✓ Full seed setup (define personality, tone, preferences)  
✓ Import/export .json/.txt conversations  
✓ GPT-4o or any other OpenRouter-compatible model  
✓ Fully local, nothing is uploaded unless you configure otherwise

GETTING STARTED

1. Install dependencies:
   pip install fastapi uvicorn httpx

2. Run the server:
   uvicorn app:app --reload

3. Open in browser:
   http://localhost:8000

FILES

- `app.py` — FastAPI backend  
- `static/index.html` — chat interface  
- `memory.py` — memory logic  
- `db.py` — SQLite logic  
- `alex_config.py` — prompt and output control  
- `memories/` — seed, working, pinned memory  
- `start_alex_local.bat` — Windows starter (optional)  
- `readme.txt` — this file

TO CUSTOMIZE

- Change the seed file in `memories/seed/alex_seed.json`  
- You can use any name or tone for your assistant  
- Update the UI text in `static/index.html` if you want to localize or rename

LICENSE

Feel free to use, modify, and share. No attribution required — but you are welcome to link back if you found it helpful.

Need help setting it up?

If you're not sure how to install Python or run the server, just ask your ChatGPT:
“How do I run a FastAPI app from a local folder?”

You can also say:
“I have a project called Alex Local, how do I set it up?”

ChatGPT will guide you step by step. 💙

Download the full project here: alex-local-public.zip

Or explore the source files below.