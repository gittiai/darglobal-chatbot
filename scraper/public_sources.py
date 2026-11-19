"""Download public press releases, filings and news about DarGlobal and Wasalt.
Plain HTTP only; pages that serve a bot challenge are skipped (save them manually instead)."""
import json, time
from pathlib import Path
import httpx, trafilatura

URLS = {
 "darglobal": [
  "https://www.investegate.co.uk/announcement/rns/dar-global--dar/full-year-results-/9468098",
  "https://www.ticker.app/lse/DAR/rns/2026-06-17/Business-Update/6670I",
  "https://www.ticker.app/lse/DAR/rns/2025-03-13/Full-year-results-for-the-year-ended-31-Dec-2024/4681A",
  "https://www.zawya.com/en/press-release/companies-news/dar-global-delivers-66-revenue-growth-in-hy-2026-as-portfolio-gdv-reaches-23bln-1458377",
  "https://www.zawya.com/en/press-release/companies-news/dar-globals-iconic-projects-tierra-viva-in-spain-aida-in-oman-and-les-vagues-in-qatar-enter-the-construction-phase-lguiu7qt",
  "https://www.zawya.com/en/press-release/companies-news/dar-global-launches-over-19bln-in-global-luxury-real-estate-projects-in-2024-ql1qndgg",
  "https://www.zawya.com/en/business/real-estate/lse-listed-dar-global-to-bring-trump-tower-to-jeddah-skyline-in-saudi-r68s0v98",
  "https://prnewswire.co.uk/news-releases/dar-globals-iconic-projects-tierra-viva-in-spain-aida-in-oman-and-les-vagues-in-qatar-enter-the-construction-phase-on-the-back-of-surging-investor-demand-302016739.html",
  "https://en.prnasia.com/releases/apac/dar-global-and-the-trump-organisation-expand-saudi-portfolio-with-usd-1bn-trump-plaza-jeddah-518400.shtml",
  "https://www.intellinews.com/dar-global-launches-1bn-trump-plaza-jeddah-development-419527/",
  "https://www.thenationalnews.com/business/property/2026/11/16/dar-global-launches-267m-project-in-jeddah-amid-saudi-expansion-push/",
  "https://www.thenationalnews.com/business/property/2026/09/03/where-is-trumps-property-empire-expanding-in-the-gulf/",
  "https://agbi.com/real-estate/2024/12/dar-global-plans-two-trump-branded-projects-in-riyadh",
  "https://gulfnews.com/business/property/dar-global-brings-trump-tower-to-jeddah-1.1719929992106",
  "https://www.arabianbusiness.com/industries/real-estate/saudi-real-estate-dar-global-announces-plans-for-trump-tower-in-jeddah",
  "https://guest.meed.com/dar-global-to-develop-42bn-oman-mixed-use-project/",
  "https://www.meed.com/dar-global-starts-construction-on-three-projects",
  "https://www.sharikatmubasher.com/media-hub/news/21515215/dar-globals-development-portfolio-reaches-19bn-amid-saudi-expansion?lang=en",
  "https://bebeez.eu/2025/11/03/the-saudi-born-developer-reaching-global-heights-dar-globals-project-pipeline-reaches-usd-19-billion-with-major-expansion-into-saudi-arabia/",
  "https://gulfconstructiononline.com/Article/386451/dar-global-begins-work-on-luxury-projects",
  "https://tradearabia.com/News/487200/Dar-Global-posts-solid-H1-results-revenue-up-66pc",
  "https://pulse2.com/dar-global-reports-h1-revenue-of-258-million-up-66-as-portfolio-gdv-reaches-23-billion/",
  "https://www.ajbell.co.uk/news/articles/dar-global-announces-record-portfolio-growth-and-landmark-expansion",
  "https://www.tradingview.com/news/reuters.com,2026-06-16:newsml_Zaw36YXmz:0-zawya-dar-global-marks-five-years-of-global-expansion-with-23bln-development-portfolio-and-a-bold-vision-for-the-future/",
  "https://luxurysignature.net/uae/en/dubai-construction/Dar-Global",
  "https://tranio.com/developers-uae/dar-al-arkan/",
 ],
 "wasalt": [
  "https://www.gccbusinessnews.com/wasalt-unveils-new-features-to-improve-real-estate-services-in-saudi-arabia/",
  "https://gulfconstructiononline.com/ArticleTA/413579",
  "https://gulfconstructiononline.com/ArticleTA/429985",
  "https://markets.financialcontent.com/stocks/article/getnews-2023-7-28-wasalt-introduces-revolutionary-new-features-to-enhance-real-estate-services-in-saudi-arabia",
  "https://sharikatmubasher.com/news/article/21375099",
  "https://apps.apple.com/us/app/id1588885673",
  "https://darak.app/fr/compare/darak-vs-wasalt",
 ],
}
OUT = Path("data/public.jsonl")
H = {"User-Agent": "Mozilla/5.0 (compatible; research-bot)"}

with OUT.open("w") as f, httpx.Client(headers=H, follow_redirects=True, timeout=30) as c:
    for source, urls in URLS.items():
        for u in urls:
            try:
                r = c.get(u)
                text = trafilatura.extract(r.text, include_tables=True) if r.status_code == 200 else None
                meta = trafilatura.extract_metadata(r.text) if text else None
                if not text or len(text) < 300 or "Just a moment" in text:
                    print("SKIP", r.status_code, u); continue
                title = (meta.title if meta and meta.title else u)
                f.write(json.dumps({"source": source, "url": u, "title": title, "text": text}, ensure_ascii=False) + "\n")
                print("OK", len(text), title[:70])
            except Exception as e:
                print("ERR", u, str(e)[:60])
            time.sleep(1)
