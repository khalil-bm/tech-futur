import os, datetime, re, requests, feedparser
from pathlib import Path
from slugify import slugify

# ---- Sources d'actus Tech & Futur (tu peux en ajouter/retirer) ----
FEEDS = [
    "https://www.futura-sciences.com/rss/actualites.xml",
    "https://www.space.com/feeds/all",
    "https://techcrunch.com/feed/",
    "https://www.science-et-vie.com/rss",
    "https://www.numerama.com/feed/"
]

SITE_DIR = Path(".")
POSTS_DIR = SITE_DIR / "_posts"
POSTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL = os.getenv("LLM_MODEL", "llama3")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
TIMEOUT = 20

def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()

def llm_summarize(title: str, text: str) -> str:
    """Tente un résumé via Ollama si dispo, sinon fallback propre."""
    prompt = f"""Tu es un journaliste futuriste.
Résume de façon captivante et crédible pour un jeune public.
Structure : 1 accroche courte • 4 points clés • 1 phrase qui ouvre sur le futur.
Titre: {title}
Texte:
{text[:7000]}
"""
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=TIMEOUT,
        )
        if r.ok:
            rep = r.json().get("response", "").strip()
            if rep:
                return rep
    except Exception:
        pass
    base = strip_html(text)
    return (
        f"• {title}\n"
        f"{base[:400]}...\n"
        "→ Ce progrès pourrait transformer notre quotidien plus vite qu'on ne le pense."
    )

# ---- Récupération des items (robuste) ----
items = []
for url in FEEDS:
    try:
        d = feedparser.parse(url)
        for e in d.entries[:5]:
            items.append({
                "title": e.get("title", "Sans titre"),
                "link": e.get("link", ""),
                "summary": strip_html(e.get("summary", e.get("description", ""))),
            })
    except Exception:
        continue

if not items:
    items = [{
        "title": "Découverte: l'IA accélère les avancées scientifiques",
        "link": "",
        "summary": "Même si les flux sont indisponibles, on publie une synthèse pour garder le rythme."
    }]

blocks = []
for it in items[:5]:
    synth = llm_summarize(it["title"], it["summary"] or it["title"])
    block = f"### {it['title']}\n\n"
    if it["link"]:
        block += f"Source: {it['link']}\n\n"
    block += f"{synth}\n"
    blocks.append(block)

today = datetime.date.today().strftime("%Y-%m-%d")
post_title = f"Innovations & Futur — {today}"
slug = slugify(post_title)
md = f"""---
layout: post
title: "{post_title}"
date: {today}
---

Bienvenue sur **Tech & Futur** — chaque jour, une découverte qui change le monde.

{'\n\n'.join(blocks)}

_Disclaimer_: ce site peut contenir des liens d’affiliation utiles (gadgets tech, livres, outils IA).
"""

out_path = POSTS_DIR / f"{today}-{slug}.md"
out_path.write_text(md, encoding="utf-8")
print("Article généré:", out_path)
