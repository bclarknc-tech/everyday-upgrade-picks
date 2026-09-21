# Everyday Upgrade Picks

Auto-generated Amazon affiliate buying-guide site. Published via GitHub Pages
from `docs/`.

- `content_generator.py` — generates buying-guide articles (genuine "what to
  look for" content, no fake reviews/ratings) using the local Hermes agent,
  renders them as static HTML into `docs/`, and commits+pushes so GitHub
  Pages auto-redeploys.
- Every page carries an Amazon Associates affiliate disclosure per FTC
  guidelines. This site does not fabricate reviews, ratings, or claims of
  personal product use — see the docstring in `content_generator.py`.

## One-time setup (see AFFILIATE-SETUP.md)
1. GitHub Pages already enabled on this repo, serving `docs/` on `main`.
2. Set your Amazon Associates tracking tag:
   `setx AMAZON_ASSOCIATE_TAG "yourtag-20"` (get one at affiliate-program.amazon.com
   — requires an existing site with real content, which this provides).

## Run manually
```
venv\Scripts\python.exe content_generator.py --count 3
```

## Run on a schedule
See the "Jarvis - Affiliate Blog Generator" Windows Scheduled Task.
