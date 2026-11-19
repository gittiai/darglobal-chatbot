"""Build data/kb.jsonl: chunks from public articles, manual page saves, and Wasalt sitemap aggregates."""
import json, re
from collections import Counter, defaultdict
from pathlib import Path
import trafilatura

RAW, OUT = Path("raw"), Path("data/kb.jsonl")
docs = [json.loads(l) for f in ["data/public.jsonl", "data/wasalt.jsonl"] if Path(f).exists() for l in open(f)]

# Pages saved manually from a browser (raw/manual/*.html)
for p in sorted((RAW / "manual").glob("**/*.htm*")):
    html = p.read_text(errors="ignore")
    text = trafilatura.extract(html, include_tables=True) or ""
    if len(text) < 200: continue
    m = trafilatura.extract_metadata(html)
    url = (m.url if m and m.url else p.name)
    src = "wasalt" if "wasalt" in (url + p.name).lower() else "darglobal"
    docs.append({"source": src, "url": url, "title": (m.title if m and m.title else p.stem), "text": text})

# Wasalt sitemaps -> aggregate facts
def locs(name): return re.findall(r"<loc>([^<]+)</loc>", (RAW / name).read_text()) if (RAW / name).exists() else []
sale = locs("w_prod.gz")
types, beds, sizes = Counter(), Counter(), defaultdict(list)
for u in sale:
    slug = u.rsplit("/", 1)[-1]
    t = slug.split("-")[0]; types[t] += 1
    if b := re.search(r"(\d+)-bedrooms?", slug): beds[(t, int(b.group(1)))] += 1
    if s := re.search(r"(\d+)-sqm", slug): sizes[t].append(int(s.group(1)))
lines = [f"Wasalt (wasalt.sa) public sitemap lists {len(sale):,} properties for sale (snapshot Nov 2026)."]
lines += [f"- {t}: {n:,} listings" for t, n in types.most_common() if n >= 20]
lines.append("Bedroom breakdown (where stated):")
lines += [f"- {t} with {b} bedrooms: {n:,}" for (t, b), n in sorted(beds.items(), key=lambda x: -x[1])[:20]]
docs.append({"source": "wasalt", "url": "https://wasalt.sa/en", "title": "Wasalt sale listings overview", "text": "\n".join(lines)})

cities = defaultdict(lambda: defaultdict(set))
for u in locs("category_sitemap_en_sa.xml"):
    m = re.search(r"/en/(\w+?)s?-for-(sale|rent)-in-(.+)$", u)
    if not m: continue
    kind, deal, place = m.groups()
    parts = place.split("-")
    if len(parts) > 1 and parts[0] in ("north", "south", "east", "west", "center", "central") and parts[1] in ("riyadh", "jeddah"):
        parts = [parts[1], parts[0]] + parts[2:]  # "south-riyadh-x" -> riyadh / "south x"
    cities[parts[0]][f"{kind.replace('propertie', 'property')} for {deal}"].add(" ".join(parts[1:]) or "(whole city)")
for city, kinds in cities.items():
    body = [f"Wasalt has listing pages in {city.title()} for: " + ", ".join(sorted(kinds)) + "."]
    districts = sorted(set().union(*kinds.values()) - {"(whole city)"})
    if districts: body.append(f"Districts/areas covered in {city.title()} ({len(districts)}): " + ", ".join(d.title() for d in districts[:250]))
    body.append(f"Browse: https://wasalt.sa/en/properties-for-sale-in-{city}")
    docs.append({"source": "wasalt", "url": f"https://wasalt.sa/en/properties-for-sale-in-{city}", "title": f"Wasalt properties in {city.title()}", "text": "\n".join(body)})
rent = locs("rental_pdp_sitemap_en_sa.xml")
rk = Counter(u.rsplit("/", 1)[-1].split("-for-")[0] for u in rent)
docs.append({"source": "wasalt", "url": "https://wasalt.sa/en", "title": "Wasalt daily rentals overview",
             "text": f"Wasalt offers daily rentals (holiday homes): {len(rent):,} listings — " + ", ".join(f"{k}: {n}" for k, n in rk.most_common(8)) + ". Types include apartments, chalets, farms, villas and rest houses."})

# Chunk
n = 0
with OUT.open("w") as f:
    for d in docs:
        paras, buf = [p for p in d["text"].split("\n") if p.strip()], ""
        for p in paras + [None]:
            if p is None or len(buf) + len(p) > 1500:
                if buf.strip():
                    f.write(json.dumps({**{k: d[k] for k in ("source", "url", "title")}, "text": buf.strip()}, ensure_ascii=False) + "\n"); n += 1
                buf = ""
            if p: buf += p + "\n"
print(len(docs), "docs ->", n, "chunks;", len(cities), "cities")
