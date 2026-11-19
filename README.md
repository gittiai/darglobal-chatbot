# DarGlobal & Wasalt Assistant

An AI chatbot that answers questions about **DarGlobal** (LSE-listed luxury developer) and **Wasalt** (Saudi real-estate portal) using publicly available data, powered by a free model on **OpenRouter**.

## How it works
1. **Data collection** (`scraper/`)
   - `public_sources.py` – downloads public press releases, LSE regulatory announcements (FY2024 & FY2025 results, business updates) and news coverage about both companies.
   - Wasalt public sitemaps (60,000 sale listings, 8,600+ city/district pages, 2,700 daily rentals) → aggregated into facts per city and property type.
   - `wasalt.py` – polite listing-page scraper (robots.txt-compliant, rate-limited).
   - `build_kb.py` – cleans, merges and chunks everything into `data/kb.jsonl` (~500 chunks).
   - Both sites' bot protection (Imperva / Cloudflare) was respected, not bypassed; pages saved manually from a browser can be dropped into `raw/manual/` and are picked up by `build_kb.py`.
2. **Retrieval** – BM25 keyword search over the chunks (fast, no paid embeddings).
3. **Generation** – top chunks + chat history sent to a free OpenRouter model, with automatic fallback across free models if one is rate-limited. Answers cite numbered sources, shown as links in the UI.
4. **Serving** – FastAPI backend + single-page chat UI, containerised with Docker.

## Run locally
```bash
echo "OPENROUTER_API_KEY=sk-or-..." > .env
docker build -t darglobal-chatbot .
docker run -p 7860:7860 --env-file .env darglobal-chatbot
# open http://localhost:7860
```

## Refresh data
```bash
uv sync && uv run playwright install chromium
uv run python scraper/public_sources.py
uv run python scraper/build_kb.py
```

## Environment
| Var | Default |
|---|---|
| `OPENROUTER_API_KEY` | required |
| `OPENROUTER_MODEL` | first model tried; falls back to `nvidia/nemotron-3-ultra-550b-a55b:free`, `nvidia/nemotron-3.5-super-vl:free`, `openrouter/free` |
| `PORT` | `7860` |
