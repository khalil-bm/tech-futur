import os
import datetime
import re
import requests
import feedparser
from pathlib import Path
from slugify import slugify

# ---- Sources d'actualités Tech & Futur ----
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

# ------------------ utilitaires ------------------
def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()

def llm_summarize(title: str, text: str) -> str:
    prompt = (
        "Tu es un journaliste futuriste.\n"
        "Résume de façon captivante et crédible pour un jeune public.\n"
        "Structure : 1 accroche courte • 4 points clés • 1 phrase qui ouvre sur le futur.\n"
        "Titre: {title}\nTexte:\n{chunk}\n"
    ).format(title=title, chunk=(text[:7000] if text else ""))

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
        "• {title}\n{body}...\n→ Ce progrès pourrait transformer notre quotidien plus vite qu'on ne le pense."
    ).format(title=title, body=base[:400])

# ------------------ collecte ------------------
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

# ------------------ rendu markdown ------------------
blocks = []
for it in items[:5]:
    synth = llm_summarize(it["title"], it["summary"] or it["title"])
    block = "### {t}\n\n".format(t=it["title"])
    if it["link"]:
        block += "Source: {u}\n\n".format(u=it["link"])
    block += synth + "\n"
    blocks.append(block)

today = datetime.date.today().strftime("%Y-%m-%d")
post_title = "Innovations & Futur — {d}".format(d=today)
slug = slugify(post_title)
content_blocks = "\n\n".join(blocks)

md = """---
layout: post
title: "{post_title}"
date: {today}
---

Bienvenue sur **Tech & Futur** — chaque jour, une découverte qui change le monde.

{content_blocks}

_Disclaimer_: ce site peut contenir des liens d’affiliation utiles (gadgets tech, livres, outils IA).
""".format(post_title=post_title, today=today, content_blocks=content_blocks)

out_path = POSTS_DIR / "{date}-{slug}.md".format(date=today, slug=slug)
out_path.write_text(md, encoding="utf-8")
print("✅ Article généré :", out_path)
