"""Scrape public Wasalt listing pages (robots.txt allows /property; /search is excluded).
Polite: one page at a time, ~1.5s apart. Output: data/wasalt.jsonl"""
import asyncio, json, random, re, sys
from pathlib import Path
from playwright.async_api import async_playwright

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
SITEMAP = Path("raw/w_prod.gz")  # product_sitemap_en_sa.xml (served uncompressed)
OUT = Path("data/wasalt.jsonl")
NOISE = ("Support", "Post Property", "Get Matched", "Call Now", "See more", "View On Map")

def clean(text: str) -> str:
    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l and l not in NOISE]
    out = "\n".join(lines)
    return out.split("Similar Properties")[0][:4000]

async def main():
    urls = re.findall(r"<loc>([^<]+)</loc>", SITEMAP.read_text())
    random.seed(7); urls = random.sample(urls, min(N * 2, len(urls)))
    done = {json.loads(l)["url"] for l in OUT.read_text().splitlines()} if OUT.exists() else set()
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page()
        with OUT.open("a") as f:
            for u in urls:
                if len(done) >= N: break
                if u in done: continue
                try:
                    await pg.goto(u, timeout=40000, wait_until="load")
                    await pg.wait_for_timeout(4000)
                    title = (await pg.title()).split("|")[0].strip()
                    text = clean(await pg.inner_text("body"))
                    if len(text) < 200 or "Just a moment" in title:
                        print("thin", len(text), title, flush=True); await asyncio.sleep(1.5); continue
                    f.write(json.dumps({"source": "wasalt", "url": u, "title": title, "text": text}, ensure_ascii=False) + "\n"); f.flush()
                    done.add(u); print(len(done), title[:70], flush=True)
                except Exception as e:
                    print("skip", u, str(e)[:80], flush=True)
                await asyncio.sleep(1.5)
        await b.close()

asyncio.run(main())
