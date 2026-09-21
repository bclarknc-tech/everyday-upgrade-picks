"""
Affiliate Buying-Guide Content Generator
==========================================
Generates genuine, disclosed Amazon-affiliate buying-guide articles (NOT fake
reviews, NOT user-generated-content forgery) and publishes them as a free
static site on GitHub Pages.

Why this shape and not something else:
- No seller/creator account or identity verification anywhere in this
  pipeline (unlike Etsy/Printify's Stripe KYC) — GitHub account signup is
  just an email, and Amazon Associates approval just needs a working site
  with real content, which is what this produces.
- It writes honest "what to look for" buying-guide content with NO fake
  star ratings, NO fabricated customer quotes, and NO claims of personal
  use — those would be review fraud (illegal under FTC rules, ToS
  violations everywhere). Every page carries a clear affiliate disclosure.
  This is legitimate, disclosed affiliate marketing, nothing more.
- Links point at Amazon SEARCH RESULTS for a product category (with the
  affiliate tag attached), not fabricated reviews of specific unverified
  products.

Pipeline per article:
1. Pick an evergreen buying-guide topic from TOPICS.
2. Ask the local Hermes agent for genuine buying-guide copy: what to look
   for, 3-5 feature call-outs, who it's good for. Falls back to a simple
   templated draft if Hermes isn't reachable.
3. Render a static HTML page (Jinja-free, just string templates — no new
   dependency) with an Amazon Associates disclosure banner and a
   category-search affiliate link for each call-out.
4. Rebuild site/index.html linking every article ever generated.
5. Commit + push the site/ folder to the GitHub Pages repo, which
   auto-deploys within a minute or two — no manual publish step.

Needs, one time from Brian (see AFFILIATE-SETUP.md in this folder):
- A GitHub repo with Pages enabled (this script assumes it already exists
  and this folder is already `git remote`-linked to it — see setup doc).
- An Amazon Associates tag, set via:  setx AMAZON_ASSOCIATE_TAG "yourtag-20"
  Until that's set, articles still generate and publish, just with a
  placeholder affiliate tag - fine for content review, not for earning yet.

Run manually:
    venv\\Scripts\\python.exe content_generator.py --count 3

Run on a schedule: see the "Jarvis - Affiliate Blog Generator" scheduled task.
"""

from __future__ import annotations

import argparse
import datetime
import html
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

_USER_HOME = Path(os.environ.get("USERPROFILE", str(Path.home())))

SITE_DIR = Path(__file__).parent / "docs"
ARTICLES_DIR = SITE_DIR / "articles"
MANIFEST_PATH = Path(__file__).parent / "articles_manifest.json"

HERMES_PYTHON = _USER_HOME / "AppData" / "Local" / "hermes" / "hermes-agent" / "venv" / "Scripts" / "python.exe"
HERMES_ENTRY = _USER_HOME / "AppData" / "Local" / "hermes" / "hermes-agent" / "hermes"

SITE_TITLE = "Everyday Upgrade Picks"
SITE_TAGLINE = "Practical buying guides for everyday gear — what to actually look for before you buy."

# Evergreen, broadly-searched buying-guide topics. Each entry is
# (topic, [3-5 feature/product-type call-outs to search Amazon for]).
TOPICS: dict[str, list[str]] = {
    "Kitchen Gadgets Worth Buying": [
        "electric kitchen scale", "silicone baking mats", "immersion blender",
        "digital meat thermometer", "garlic press",
    ],
    "Home Office Upgrades": [
        "monitor arm mount", "ergonomic keyboard", "under-desk footrest",
        "cable management box", "adjustable laptop stand",
    ],
    "Camping & Outdoors Essentials": [
        "portable camping stove", "inflatable sleeping pad", "headlamp flashlight",
        "collapsible water container", "camping hammock",
    ],
    "Pet Owner Must-Haves": [
        "automatic pet feeder", "no-pull dog harness", "interactive cat toy",
        "pet hair vacuum attachment", "orthopedic dog bed",
    ],
    "Home Fitness on a Budget": [
        "adjustable dumbbells", "resistance bands set", "yoga mat with alignment lines",
        "foam roller", "jump rope with counter",
    ],
    "Small-Space Gardening Gear": [
        "self-watering planter", "indoor grow light", "compact garden tool set",
        "raised garden bed kit", "moisture meter",
    ],
    "Coffee Setup Upgrades": [
        "burr coffee grinder", "gooseneck kettle", "milk frother",
        "coffee scale with timer", "reusable pour-over filter",
    ],
    "Travel Gear That Earns Its Space": [
        "packing cubes set", "portable luggage scale", "universal travel adapter",
        "compression toiletry bag", "neck pillow with storage",
    ],
}

DISCLOSURE_HTML = (
    "<p class=\"disclosure\">As an Amazon Associate, this site earns from "
    "qualifying purchases made through the links below, at no extra cost to "
    "you. Products are not personally tested or reviewed — this page is a "
    "buying guide describing features worth looking for, not a specific "
    "product endorsement.</p>"
)

PAGE_CSS = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:760px;
margin:0 auto;padding:24px 16px;line-height:1.6;color:#222;background:#fafafa}
h1{font-size:1.8rem} h2{font-size:1.25rem;margin-top:2rem}
.disclosure{font-size:.85rem;color:#666;border-left:3px solid #ccc;padding:8px 12px;
background:#fff;margin:1.5rem 0}
.callout{background:#fff;border:1px solid #e2e2e2;border-radius:8px;padding:14px 16px;
margin:12px 0}
.callout a{color:#0a5;font-weight:600;text-decoration:none}
.callout a:hover{text-decoration:underline}
footer{margin-top:3rem;font-size:.8rem;color:#888;text-align:center}
nav a{margin-right:12px}
"""


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "article"


def _affiliate_tag() -> str:
    return os.environ.get("AMAZON_ASSOCIATE_TAG", "PLACEHOLDER-20")


def _amazon_search_url(query: str) -> str:
    encoded = urllib.parse.quote_plus(query)
    return f"https://www.amazon.com/s?k={encoded}&tag={_affiliate_tag()}"


def generate_guide_copy(topic: str, call_outs: list[str]) -> str:
    """Ask the local Hermes agent for genuine buying-guide copy (what to look
    for, no fake reviews/ratings/testimonials). Falls back to a simple
    templated draft if Hermes isn't reachable."""
    items = ", ".join(call_outs)
    prompt = (
        f"Write a short, genuinely useful buying-guide article (not a fake "
        f"review) titled '{topic}'. It should briefly introduce the topic, "
        f"then for EACH of these {len(call_outs)} items give a 2-3 sentence "
        f"paragraph explaining what features actually matter when choosing "
        f"one (not a review of a specific product, no star ratings, no "
        f"claims of personal use): {items}. "
        f"Plain text only. Start each item's paragraph with the item name "
        f"followed by a colon, on its own line."
    )
    if HERMES_PYTHON.exists() and HERMES_ENTRY.exists():
        try:
            result = subprocess.run(
                [str(HERMES_PYTHON), str(HERMES_ENTRY), "-z", prompt],
                cwd=str(HERMES_ENTRY.parent),
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=120,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            print(f"[content] Hermes returned nonzero/empty, using fallback. stderr: {result.stderr[:300]}")
        except Exception as exc:
            print(f"[content] Hermes call failed ({exc}), using fallback")

    lines = [f"Choosing the right gear for '{topic.lower()}' comes down to a "
             f"handful of features that actually matter more than brand name."]
    for item in call_outs:
        lines.append(f"\n{item.title()}:")
        lines.append(f"When shopping for a {item}, focus on build quality, "
                      f"the specific features that match how you'll actually use "
                      f"it, and reviews from verified buyers on the listing "
                      f"itself rather than marketing copy.")
    return "\n".join(lines)


def _parse_guide_into_sections(guide_text: str, call_outs: list[str]) -> list[tuple[str, str]]:
    """Best-effort split of the generated text into (item_name, paragraph)
    pairs matching call_outs, in order. Falls back to one big paragraph per
    item if the split doesn't line up (still safe, just less polished)."""
    sections: list[tuple[str, str]] = []
    lower_text = guide_text
    markers = []
    for item in call_outs:
        idx = lower_text.lower().find(item.lower() + ":")
        markers.append((idx, item))
    markers = [m for m in markers if m[0] != -1]
    markers.sort()
    for i, (idx, item) in enumerate(markers):
        start = idx + len(item) + 1
        end = markers[i + 1][0] if i + 1 < len(markers) else len(lower_text)
        para = lower_text[start:end].strip()
        sections.append((item, para or f"Look for solid build quality and features that fit how you'll use a {item}."))
    if not sections:
        for item in call_outs:
            sections.append((item, f"Look for solid build quality and features that fit how you'll use a {item}."))
    return sections


def render_article(topic: str, call_outs: list[str], guide_text: str, date_str: str) -> tuple[str, str]:
    slug = _slugify(topic)
    sections = _parse_guide_into_sections(guide_text, call_outs)

    intro_end = guide_text.lower().find(call_outs[0].lower() + ":") if call_outs else -1
    intro = guide_text[:intro_end].strip() if intro_end > 0 else guide_text.split("\n")[0]
    # Hermes sometimes echoes the topic as its own leading line/heading —
    # strip it so it doesn't duplicate the <h1> right above it.
    intro_lines = [ln for ln in intro.splitlines() if ln.strip().lower() != topic.strip().lower()]
    intro = "\n".join(intro_lines).strip()

    callouts_html = ""
    for item, para in sections:
        url = _amazon_search_url(item)
        callouts_html += (
            f'<div class="callout"><h2>{html.escape(item.title())}</h2>'
            f'<p>{html.escape(para)}</p>'
            f'<p><a href="{url}" rel="nofollow sponsored" target="_blank">'
            f'See current options on Amazon →</a></p></div>\n'
        )

    page_html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(topic)} — {SITE_TITLE}</title>
<style>{PAGE_CSS}</style></head>
<body>
<nav><a href="../index.html">← All guides</a></nav>
<h1>{html.escape(topic)}</h1>
<p><em>Updated {date_str}</em></p>
{DISCLOSURE_HTML}
<p>{html.escape(intro)}</p>
{callouts_html}
<footer>{SITE_TITLE} — {html.escape(SITE_TAGLINE)}</footer>
</body></html>
"""
    return slug, page_html


def rebuild_index(all_articles: list[dict]) -> None:
    items_html = ""
    for a in sorted(all_articles, key=lambda x: x["date"], reverse=True):
        items_html += (
            f'<div class="callout"><h2><a href="articles/{a["slug"]}.html">'
            f'{html.escape(a["topic"])}</a></h2>'
            f'<p><em>{a["date"]}</em></p></div>\n'
        )
    index_html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{SITE_TITLE}</title>
<style>{PAGE_CSS}</style></head>
<body>
<h1>{SITE_TITLE}</h1>
<p>{html.escape(SITE_TAGLINE)}</p>
{DISCLOSURE_HTML}
{items_html}
<footer>{SITE_TITLE}</footer>
</body></html>
"""
    (SITE_DIR / "index.html").write_text(index_html, encoding="utf-8")


def _load_manifest() -> list[dict]:
    import json
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return []


def _save_manifest(articles: list[dict]) -> None:
    import json
    MANIFEST_PATH.write_text(json.dumps(articles, indent=2), encoding="utf-8")


def git_publish(commit_message: str) -> bool:
    """Commit + push the site/ folder. Never raises - a publish failure just
    means the run log shows it and Brian can push manually."""
    repo_root = Path(__file__).parent
    if not (repo_root / ".git").exists():
        print("[publish] no git repo here yet - run the one-time setup "
              "(see AFFILIATE-SETUP.md) before this will auto-publish.")
        return False
    try:
        subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=repo_root, capture_output=True, text=True,
        )
        if result.returncode != 0 and "nothing to commit" not in (result.stdout + result.stderr).lower():
            print(f"[publish] commit failed: {result.stderr[:300]}")
            return False
        push = subprocess.run(["git", "push"], cwd=repo_root, capture_output=True, text=True)
        if push.returncode != 0:
            print(f"[publish] push failed: {push.stderr[:300]}")
            return False
        print("[publish] pushed to GitHub - Pages will redeploy within a minute or two.")
        return True
    except Exception as exc:
        print(f"[publish] git publish failed ({exc})")
        return False


def run(count: int, publish: bool) -> int:
    import random
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

    all_articles = _load_manifest()
    existing_topics = {a["topic"] for a in all_articles}
    remaining = [t for t in TOPICS if t not in existing_topics]
    if len(remaining) < count:
        remaining = list(TOPICS.keys())  # cycle back through once everything's covered
    random.shuffle(remaining)
    picks = remaining[:count]

    date_str = datetime.date.today().isoformat()
    print(f"[content] generating {len(picks)} article(s): {picks}")

    for topic in picks:
        call_outs = TOPICS[topic]
        print(f"[content] writing '{topic}'...")
        guide_text = generate_guide_copy(topic, call_outs)
        slug, page_html = render_article(topic, call_outs, guide_text, date_str)
        (ARTICLES_DIR / f"{slug}.html").write_text(page_html, encoding="utf-8")

        all_articles = [a for a in all_articles if a["topic"] != topic]
        all_articles.append({"topic": topic, "slug": slug, "date": date_str})
        print(f"    -> docs/articles/{slug}.html")

    rebuild_index(all_articles)
    _save_manifest(all_articles)
    print(f"[content] site rebuilt: {SITE_DIR / 'index.html'} ({len(all_articles)} articles total)")

    if publish:
        git_publish(f"Add/update {len(picks)} buying guide(s) — {date_str}")
    else:
        print("[content] --no-publish set, skipping git push")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=2, help="Number of new/refreshed articles to generate")
    parser.add_argument("--no-publish", action="store_true", help="Skip git commit/push (generate only)")
    args = parser.parse_args()
    sys.exit(run(args.count, publish=not args.no_publish))
