"""DarGlobal & Wasalt assistant: BM25 retrieval over scraped public data + free OpenRouter model."""
import json, os, re
from pathlib import Path
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from rank_bm25 import BM25Okapi

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODELS = [m for m in [os.environ.get("OPENROUTER_MODEL", ""), "baidu/ernie-5.5-flash-preview:free",
          "nvidia/nemotron-3-ultra-550b-a55b:free", "nvidia/nemotron-3.5-super-vl:free", "openrouter/free"] if m]
MODELS = list(dict.fromkeys(MODELS))

CHUNKS = [json.loads(l) for l in open(ROOT / "data/kb.jsonl")]
tok = lambda s: re.findall(r"\w+", s.lower())
BM25 = BM25Okapi([tok(c["title"] + " " + c["text"]) for c in CHUNKS])

SYSTEM = """You are the DarGlobal & Wasalt assistant. Answer questions about DarGlobal (Dar Global PLC, the LSE-listed international luxury developer, part of the Dar Al Arkan group) and Wasalt (Saudi real-estate portal, a Dar Al Arkan / Quara Holding joint venture).
Rules:
- Use ONLY the numbered context below. If it doesn't contain the answer, say so briefly and suggest darglobal.co.uk or wasalt.sa.
- Be concise and specific: names, locations, figures, dates. Use short bullet lists when listing projects.
- Cite sources inline as [1], [2] matching the context numbers.
- If figures conflict between sources, give the most recent and mention the difference.
- Reply in the user's language (English or Arabic)."""

PROFILES = [c for c in CHUNKS if c["title"].endswith("company profile")]  # always in context

def retrieve(q: str, k: int = 5):
    scores = BM25.get_scores(tok(q))
    idx = sorted(range(len(CHUNKS)), key=lambda i: -scores[i])[:k + len(PROFILES)]
    hits = [CHUNKS[i] for i in idx if scores[i] > 0 and CHUNKS[i] not in PROFILES][:k]
    return PROFILES + hits

class Msg(BaseModel):
    role: str
    content: str = Field(max_length=4000)

class ChatReq(BaseModel):
    messages: list[Msg] = Field(min_length=1, max_length=20)

app = FastAPI(title="DarGlobal & Wasalt Assistant")

@app.get("/health")
def health(): return {"ok": True, "chunks": len(CHUNKS)}

@app.post("/api/chat")
async def chat(req: ChatReq):
    if not KEY: raise HTTPException(500, "OPENROUTER_API_KEY not set")
    history = [m for m in req.messages if m.role in ("user", "assistant")][-8:]
    user_q = history[-1].content
    prev_q = " ".join(m.content for m in history[:-1] if m.role == "user")[-300:]
    ctx = retrieve(user_q) or retrieve(prev_q + " " + user_q)
    context = "\n\n".join(f"[{i+1}] {c['title']} ({c['url']})\n{c['text']}" for i, c in enumerate(ctx))
    msgs = [{"role": "system", "content": SYSTEM + "\n\nContext:\n" + (context or "(no matching documents)")}]
    msgs += [{"role": m.role, "content": m.content} for m in history]
    last_err = None
    async with httpx.AsyncClient(timeout=90) as c:
        for model in MODELS:
            try:
                r = await c.post("https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {KEY}", "X-Title": "DarGlobal Wasalt Assistant"},
                    json={"model": model, "messages": msgs, "temperature": 0.2, "max_tokens": 4000, "reasoning": {"effort": "low", "exclude": True}})
                d = r.json()
                if r.status_code == 200 and d.get("choices") and d["choices"][0]["message"].get("content"):
                    return {"answer": d["choices"][0]["message"]["content"].strip(), "model": d.get("model", model),
                            "sources": [{"n": i+1, "title": c_["title"], "url": c_["url"]} for i, c_ in enumerate(ctx)]}
                last_err = d.get("error", {}).get("message") or f"{model}: HTTP {r.status_code}, empty reply"
            except Exception as e:
                last_err = str(e)
    raise HTTPException(503, f"All free models are busy right now, please retry. ({last_err})")

@app.post("/api/chat/stream")
async def chat_stream(req: ChatReq):
    """Streams NDJSON: {"sources":[...]} then {"delta":"..."} lines, then {"done":true,"model":...}."""
    if not KEY: raise HTTPException(500, "OPENROUTER_API_KEY not set")
    history = [m for m in req.messages if m.role in ("user", "assistant")][-8:]
    user_q = history[-1].content
    prev_q = " ".join(m.content for m in history[:-1] if m.role == "user")[-300:]
    ctx = retrieve(user_q) or retrieve(prev_q + " " + user_q)
    context = "\n\n".join(f"[{i+1}] {c['title']} ({c['url']})\n{c['text']}" for i, c in enumerate(ctx))
    msgs = [{"role": "system", "content": SYSTEM + "\n\nContext:\n" + (context or "(no matching documents)")}]
    msgs += [{"role": m.role, "content": m.content} for m in history]
    sources = [{"n": i+1, "title": c["title"], "url": c["url"]} for i, c in enumerate(ctx)]

    async def gen():
        yield json.dumps({"sources": sources}) + "\n"
        async with httpx.AsyncClient(timeout=httpx.Timeout(90, connect=10)) as c:
            for model in MODELS:
                got = False
                try:
                    async with c.stream("POST", "https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {KEY}", "X-Title": "DarGlobal Wasalt Assistant"},
                        json={"model": model, "messages": msgs, "temperature": 0.2, "max_tokens": 4000, "stream": True,
                              "reasoning": {"effort": "low", "exclude": True}}) as r:
                        if r.status_code != 200: continue
                        async for line in r.aiter_lines():
                            if not line.startswith("data: ") or line == "data: [DONE]": continue
                            try: d = json.loads(line[6:])
                            except ValueError: continue
                            if d.get("error"): break
                            delta = (d.get("choices") or [{}])[0].get("delta", {}).get("content")
                            if delta:
                                got = True
                                yield json.dumps({"delta": delta}) + "\n"
                except Exception:
                    pass
                if got:
                    yield json.dumps({"done": True, "model": model}) + "\n"; return
        yield json.dumps({"error": "All free models are busy right now — please try again in a moment."}) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")

app.mount("/static", StaticFiles(directory=ROOT / "app/static"), name="static")

@app.get("/")
def index(): return FileResponse(ROOT / "app/static/index.html")
