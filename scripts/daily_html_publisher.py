#!/usr/bin/env python3
import os, json, pathlib, re, datetime, random, html
from typing import List
from slugify import slugify
from tenacity import retry, stop_after_attempt, wait_exponential
import glob


# -------- Settings --------
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SITE_URL = os.getenv("SITE_URL", "https://jainammehta.in")
BLOG_DIR = os.getenv("BLOG_DIR", "blog")
BLOG_INDEX = os.getenv("BLOG_INDEX", f"{BLOG_DIR}/index.html")
MEMORY_FILE = os.getenv("MEMORY_FILE", ".post_memory.json")
SITEMAP_PATH = os.getenv("SITEMAP_PATH", "sitemap.xml")  # <- NEW
MAX_TAGS = 8
TARGET_WORDS = int(os.getenv("TARGET_WORDS", "1200"))
HOME_INDEX_PATH = os.getenv("HOME_INDEX_PATH", "index.html")

TOPIC_BUCKETS = [
    "AI agents & tool-use patterns",
    "Next.js performance tips",
    "NestJS + DynamoDB patterns",
    "Rust + gRPC microservices",
    "GraphQL production recipes",
    "PostgreSQL tuning for SaaS",
]

BANNED_KEYWORDS = {"casino", "adult", "hate", "piracy"}

# -------- OpenAI client --------
from openai import OpenAI
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SYSTEM = """You are a precise senior technical writer.
Write an original, accurate longform technical article with headings, code examples, steps, pitfalls, and a short TL;DR.
No marketing fluff. If something is uncertain, state assumptions.
Return strictly JSON as instructed by the user.
"""

def pick_topic() -> str:
    seed = datetime.date.today().toordinal()
    random.seed(seed)
    bucket = random.choice(TOPIC_BUCKETS)
    angles = ["from-scratch guide", "production checklist", "pitfalls and fixes",
              "architecture patterns", "hands-on tutorial"]
    return f"{bucket}: {random.choice(angles)}"

def blocked(topic: str) -> bool:
    t = topic.lower()
    return any(b in t for b in BANNED_KEYWORDS)

def load_memory() -> dict:
    p = pathlib.Path(MEMORY_FILE)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}

def save_memory(m: dict):
    pathlib.Path(MEMORY_FILE).write_text(json.dumps(m, indent=2))

def ensure_unique_slug(base: str, blog_dir: pathlib.Path) -> str:
    s = slugify(base)
    if not (blog_dir / f"{s}.html").exists():
        return s
    i = 2
    while (blog_dir / f"{s}-{i}.html").exists():
        i += 1
    return f"{s}-{i}"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def generate_article(topic: str) -> dict:
    """Returns dict: {title, slug, description, tags[], html_body}"""
    user = f"""
Topic: {topic}

Return JSON with:
- title: string (unique, specific)
- slug: string (url-safe, short; no date)
- description: string (<=150 chars, SEO meta description)
- tags: string[] (<=8)
- html_body: string (the full HTML of the article body ONLY, no <html> or <head>):
  - starts with a <p><strong>TL;DR:</strong> ...</p>
  - uses <h2>/<h3>, <p>, <pre><code> for code, <ul>/<ol>
  - include "Key Takeaways" at the end as a list
Target length: ~{TARGET_WORDS} words.
NO markdown, return pure HTML in html_body.
"""
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.6,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": user}]
    )
    data = json.loads(resp.choices[0].message.content)

    data["title"] = data.get("title", "").strip()
    data["slug"] = slugify(data.get("slug") or data["title"])
    data["description"] = (data.get("description") or "").strip()[:150]
    data["tags"] = [t.strip() for t in (data.get("tags") or [])][:MAX_TAGS]
    data["html_body"] = data.get("html_body", "")
    return data

def render_page(site_url: str, slug: str, title: str, description: str, tags: List[str], body_html: str) -> str:
    canonical = f"{site_url.rstrip('/')}/blog/{slug}.html"
    tags_meta = ", ".join(tags) if tags else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)} • Jainam Mehta</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{html.escape(description)}">
  <meta name="keywords" content="{html.escape(tags_meta)}">
  <link rel="canonical" href="{canonical}">
  <link rel="stylesheet" href="/blog/styles.css">
  <meta property="og:title" content="{html.escape(title)}">
  <meta property="og:description" content="{html.escape(description)}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical}">
</head>
<body>
  <header class="container">
    <nav><a href="/">← Home</a> · <a href="/blog/">Blog</a></nav>
    <h1>{html.escape(title)}</h1>
    <p class="desc">{html.escape(description)}</p>
    {"".join(f'<span class="tag">{html.escape(t)}</span>' for t in tags)}
    <hr>
  </header>
  <main class="container">
    {body_html}
  </main>
  <footer class="container">
    <hr>
    <p>© {datetime.date.today().year} Jainam Mehta</p>
  </footer>
</body>
</html>
"""

def rebuild_home_latest(home_index_path: pathlib.Path, blog_dir: pathlib.Path, max_items: int = 5):
    """
    Rebuild the <li> list between <!-- LATEST_POSTS_START --> and <!-- LATEST_POSTS_END -->
    using the most recent blog/*.html files (by mtime desc). Reads titles from each post's <title>.
    """
    if not home_index_path.exists():
        return
    posts = []
    for p in sorted(blog_dir.glob("*.html"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.name in ("index.html", "styles.css"):  # skip index/style
            continue
        try:
            html_text = p.read_text(encoding="utf-8", errors="ignore")
            # <title>Your Title • Jainam Mehta</title>
            m = re.search(r"<title>(.*?)</title>", html_text, flags=re.IGNORECASE|re.DOTALL)
            title = m.group(1).replace(" • Jainam Mehta", "").strip() if m else p.stem
            posts.append((p.stem, title))
        except Exception:
            posts.append((p.stem, p.stem))
        if len(posts) >= max_items:
            break

    li_html = "\n          " + "\n          ".join(
        f'<li><a href="/blog/{slug}.html">{html.escape(title)}</a></li>' for slug, title in posts
    ) + "\n        "

    home_html = home_index_path.read_text(encoding="utf-8")
    start_marker = "<!-- LATEST_POSTS_START -->"
    end_marker = "<!-- LATEST_POSTS_END -->"
    if start_marker in home_html and end_marker in home_html:
        pattern = re.compile(rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.DOTALL)
        replacement = f"{start_marker}{li_html}{end_marker}"
        updated = pattern.sub(replacement, home_html, count=1)
        home_index_path.write_text(updated, encoding="utf-8")


def ensure_blog_index(index_path: pathlib.Path):
    if index_path.exists():
        return
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Blog • Jainam Mehta</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="/blog/styles.css">
</head>
<body>
  <header class="container">
    <nav><a href="/">← Home</a> · <a href="/blog/">Blog</a></nav>
    <h1>Blog</h1>
    <p>Articles auto-published daily.</p>
    <hr>
  </header>
  <main class="container">
    <ul id="posts">
      <!-- posts will be prepended here -->
    </ul>
  </main>
</body>
</html>
""", encoding="utf-8")

def prepend_link_to_index(index_path: pathlib.Path, slug: str, title: str):
    html_text = index_path.read_text(encoding="utf-8")
    link = f'\n      <li><a href="/blog/{slug}.html">{html.escape(title)}</a> <small>— {datetime.date.today().isoformat()}</small></li>'
    updated = re.sub(r'(<ul id="posts">)', r'\1' + link, html_text, count=1, flags=re.IGNORECASE)
    index_path.write_text(updated, encoding="utf-8")

def ensure_styles(styles_path: pathlib.Path):
    if styles_path.exists():
        return
    styles_path.write_text(""".container{max-width:820px;margin:0 auto;padding:16px}
h1{margin-bottom:0}
.desc{color:#555}
.tag{display:inline-block;background:#f1f1f1;border-radius:12px;padding:2px 10px;margin-right:6px;font-size:12px}
pre{overflow:auto;padding:12px;background:#f7f7f7;border-radius:8px}
code{font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace}
hr{border:none;border-top:1px solid #eee;margin:24px 0}
ul#posts{list-style:disc}
""", encoding="utf-8")

# ----------------- SITEMAP SUPPORT (NEW) -----------------
def today_iso():
    # YYYY-MM-DD in IST
    ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    return ist.date().isoformat()

def update_sitemap(sitemap_path: pathlib.Path, site_url: str, slug: str):
    """
    Ensure sitemap.xml exists and contains:
      <url>
        <loc>https://jainammehta.in/blog/<slug>.html</loc>
        <lastmod>YYYY-MM-DD</lastmod>
        <priority>0.7</priority>
      </url>
    If it exists, update <lastmod> if the entry is already there; otherwise append.
    """
    import xml.etree.ElementTree as ET
    from xml.dom import minidom

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    ET.register_namespace("", ns["sm"])
    urlset_tag = f"{{{ns['sm']}}}urlset"
    url_tag = f"{{{ns['sm']}}}url"
    loc_tag = f"{{{ns['sm']}}}loc"
    lastmod_tag = f"{{{ns['sm']}}}lastmod"
    priority_tag = f"{{{ns['sm']}}}priority"

    loc_value = f"{site_url.rstrip('/')}/blog/{slug}.html"
    lastmod_value = today_iso()

    if sitemap_path.exists():
        try:
            tree = ET.parse(sitemap_path)
            root = tree.getroot()
        except ET.ParseError:
            # Recreate if malformed
            root = ET.Element(urlset_tag)
            tree = ET.ElementTree(root)
    else:
        root = ET.Element(urlset_tag)
        tree = ET.ElementTree(root)
        # Seed with homepage if empty
        home_url = ET.SubElement(root, url_tag)
        ET.SubElement(home_url, loc_tag).text = site_url.rstrip("/") + "/"
        ET.SubElement(home_url, lastmod_tag).text = lastmod_value
        ET.SubElement(home_url, priority_tag).text = "1.0"

    # Look for existing entry
    found = None
    for u in root.findall(f".//{url_tag}"):
        loc_el = u.find(loc_tag)
        if loc_el is not None and (loc_el.text or "").strip() == loc_value:
            found = u
            break

    if found is None:
        # Append new entry
        u = ET.SubElement(root, url_tag)
        ET.SubElement(u, loc_tag).text = loc_value
        ET.SubElement(u, lastmod_tag).text = lastmod_value
        ET.SubElement(u, priority_tag).text = "0.7"
    else:
        # Update lastmod
        lm = found.find(lastmod_tag)
        if lm is None:
            lm = ET.SubElement(found, lastmod_tag)
        lm.text = lastmod_value

    # Pretty print
    rough = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    sitemap_path.write_bytes(pretty)

# --------------------------------------------------------

def main():
    blog_dir = pathlib.Path(BLOG_DIR)
    blog_dir.mkdir(parents=True, exist_ok=True)
    index_path = pathlib.Path(BLOG_INDEX)
    styles_path = blog_dir / "styles.css"
    sitemap_path = pathlib.Path(SITEMAP_PATH)

    ensure_blog_index(index_path)
    ensure_styles(styles_path)

    mem = load_memory()
    topic = pick_topic()
    if blocked(topic):
        raise SystemExit(f"Blocked topic: {topic}")

    data = generate_article(topic)
    base_slug = data["slug"] or slugify(data["title"])
    final_slug = ensure_unique_slug(base_slug, blog_dir)

    # write page
    page_html = render_page(
        site_url=SITE_URL,
        slug=final_slug,
        title=data["title"],
        description=data["description"],
        tags=data["tags"],
        body_html=data["html_body"],
    )
    (blog_dir / f"{final_slug}.html").write_text(page_html, encoding="utf-8")

    # update blog index
    prepend_link_to_index(index_path, final_slug, data["title"])

    # update sitemap.xml (NEW)
    update_sitemap(sitemap_path, SITE_URL, final_slug)

    # memory
    today = datetime.date.today().isoformat()
    mem.setdefault("published", {})
    mem["published"].setdefault(today, [])
    mem["published"][today].append(final_slug)
    save_memory(mem)

    print(f"Published: /blog/{final_slug}.html and updated sitemap.xml")

if __name__ == "__main__":
    main()
    rebuild_home_latest(pathlib.Path(HOME_INDEX_PATH), blog_dir)
