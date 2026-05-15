#!/usr/bin/env python3
"""
Daily blog publisher for jainammehta.in.

What it does:
  1. Finds the configured AWS Bedrock model.
  2. Generates one practical SEO-friendly technical blog post.
  3. Publishes it as a static HTML page under blog/posts/.
  4. Updates blog/index.html and sitemap.xml.
  5. Commits and pushes the changes.

Run manually:
  python generate_blog.py

Run daily on Windows:
  daily_publish_blog.bat

Install startup publishing on Windows:
  install_blog_startup_task.bat
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv
    load_dotenv()


REPO_DIR = Path(__file__).parent.resolve()
BLOG_DIR = REPO_DIR / "blog"
POSTS_DIR = BLOG_DIR / "posts"
SITE_URL = "https://jainammehta.in"
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID")
PREFERRED_BEDROCK_MODELS = [
    "anthropic.claude-3-5-sonnet",
    "anthropic.claude-3-5-haiku",
    "anthropic.claude-3-haiku",
    "mistral.mistral-large-2402",
    "amazon.nova-pro-v1",
    "amazon.titan-text-premier-v1",
]
AUTHOR = "Jainam Mehta"
AUTHOR_FULL = "Jainam Paresh Mehta"

POST_CRITICAL_CSS = """
    body {
      background: #0d1117;
      color: #e6edf3;
      font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    }

    body > header {
      background: rgba(13, 17, 23, 0.92);
      border-bottom: 1px solid rgba(148, 163, 184, 0.16);
      position: sticky;
      top: 0;
      z-index: 20;
    }

    .nav-inner {
      align-items: center;
      display: flex;
      justify-content: space-between;
      margin: 0 auto;
      max-width: 1120px;
      padding: 16px 24px;
    }

    .links {
      align-items: center;
      display: flex;
      gap: 18px;
    }

    .post-wrap {
      margin: 56px auto;
      max-width: 820px;
      padding: 0 24px 88px;
    }

    .back-link {
      color: #2ecc71;
      display: inline-block;
      font-weight: 700;
      margin-bottom: 28px;
    }

    .post-header {
      background: transparent;
      border-bottom: 1px solid rgba(148, 163, 184, 0.16);
      margin-bottom: 32px;
      padding-bottom: 28px;
      position: static;
    }

    .post-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 18px;
    }

    .post-header h1 {
      font-size: clamp(32px, 5vw, 48px);
      letter-spacing: 0;
      line-height: 1.14;
      margin: 0 0 16px;
      max-width: 780px;
    }

    .post-meta {
      color: #9aa4b2;
      display: flex;
      flex-wrap: wrap;
      font-size: 15px;
      gap: 12px;
    }

    .post-body {
      font-size: 18px;
      line-height: 1.82;
    }

    .post-body h2 {
      color: #e6edf3;
      font-size: 28px;
      line-height: 1.25;
      margin: 42px 0 14px;
    }

    .post-body h3 {
      color: #2ecc71;
      font-size: 22px;
      line-height: 1.35;
      margin: 34px 0 10px;
    }

    .post-body p {
      color: #c9d1d9;
      margin: 0 0 20px;
    }

    .post-body ul {
      margin: 0 0 22px;
      padding-left: 22px;
    }

    .post-body li {
      color: #c9d1d9;
      margin-bottom: 10px;
      padding-left: 4px;
    }

    .post-body strong {
      color: #f0f6fc;
    }

    .post-body pre {
      background: #07120d;
      border: 1px solid rgba(46, 204, 113, 0.18);
      border-radius: 8px;
      margin: 24px 0;
      overflow-x: auto;
      padding: 18px;
    }

    .post-body code {
      background: rgba(46, 204, 113, 0.1);
      border-radius: 4px;
      color: #2ecc71;
      font-size: 0.9em;
      padding: 2px 6px;
    }

    .post-body pre code {
      background: transparent;
      color: #d6f5df;
      display: block;
      line-height: 1.6;
      padding: 0;
    }

    .post-footer {
      border-top: 1px solid rgba(148, 163, 184, 0.16);
      color: #9aa4b2;
      font-size: 15px;
      margin-top: 52px;
      padding-top: 28px;
    }

    .post-footer a {
      color: #2ecc71;
    }

    @media (max-width: 720px) {
      .post-wrap {
        margin-top: 36px;
        padding-inline: 18px;
      }

      .post-body {
        font-size: 16px;
        line-height: 1.76;
      }

      .links {
        display: none;
      }
    }
"""

TOPICS: list[dict[str, Any]] = [
    {
        "title": "Why I Prefer NestJS Over Express for Production APIs",
        "slug": "nestjs-vs-express-production",
        "tags": ["Node.js", "NestJS", "Backend"],
        "keywords": "NestJS vs Express, Node.js API framework, production backend, API architecture",
        "prompt_hint": "Compare NestJS and Express for large production APIs. Cover decorators, dependency injection, modules, validation, testing, and project maintainability.",
    },
    {
        "title": "How I Built a RAG System That Actually Works in Production",
        "slug": "rag-system-production-guide",
        "tags": ["AI", "RAG", "LangChain"],
        "keywords": "RAG system, retrieval augmented generation, LangChain production, vector database, AI agents",
        "prompt_hint": "Explain a production RAG architecture: chunking, embeddings, vector search, reranking, guardrails, hallucination reduction, and monitoring.",
    },
    {
        "title": "Next.js App Router: Things Nobody Tells You",
        "slug": "nextjs-app-router-gotchas",
        "tags": ["Next.js", "React", "Frontend"],
        "keywords": "Next.js App Router, React Server Components, Next.js caching, frontend architecture",
        "prompt_hint": "Share practical App Router gotchas: server/client components, layouts, caching, streaming, route handlers, and deployment behaviour.",
    },
    {
        "title": "Shopify Custom App Development: My Complete Workflow",
        "slug": "shopify-custom-app-workflow",
        "tags": ["Shopify", "Ecommerce", "Node.js"],
        "keywords": "Shopify custom app, Shopify API, ecommerce development, Shopify Node.js, Shopify webhooks",
        "prompt_hint": "Cover OAuth, Admin API, Storefront API, webhook reliability, app extensions, sessions, and production deployment.",
    },
    {
        "title": "Microservices Communication: REST vs gRPC vs Message Queues",
        "slug": "microservices-communication-rest-grpc-queues",
        "tags": ["Microservices", "System Design", "Backend"],
        "keywords": "microservices communication, REST vs gRPC, message queue, Kafka, RabbitMQ, backend architecture",
        "prompt_hint": "Give a practical decision guide for synchronous and asynchronous service communication with real tradeoffs.",
    },
    {
        "title": "PostgreSQL Performance Tuning: What I Learned the Hard Way",
        "slug": "postgresql-performance-tuning",
        "tags": ["PostgreSQL", "Database", "Backend"],
        "keywords": "PostgreSQL performance, database optimization, indexes, EXPLAIN ANALYZE, query tuning",
        "prompt_hint": "Explain slow queries, missing indexes, N+1 issues, connection pools, EXPLAIN ANALYZE, and production checks.",
    },
    {
        "title": "Building AI Agents with LangChain: A Practical Guide",
        "slug": "ai-agents-langchain-practical",
        "tags": ["AI", "LangChain", "Agents"],
        "keywords": "AI agents LangChain, autonomous agents, tool calling, LLM agents, agent workflow",
        "prompt_hint": "Cover tools, memory, ReAct loops, failure handling, human approval points, and production observability.",
    },
    {
        "title": "Redis Beyond Caching: How I Use It in Real Projects",
        "slug": "redis-beyond-caching",
        "tags": ["Redis", "Backend", "Architecture"],
        "keywords": "Redis use cases, Redis pub/sub, Redis streams, distributed locks, rate limiting, session storage",
        "prompt_hint": "Explain Redis for queues, pub/sub, streams, distributed locks, rate limits, sessions, and leaderboards.",
    },
    {
        "title": "Docker in Production: Mistakes I Made and How I Fixed Them",
        "slug": "docker-production-mistakes",
        "tags": ["Docker", "DevOps", "Backend"],
        "keywords": "Docker production, Docker best practices, container security, multi-stage builds, Dockerfile",
        "prompt_hint": "Discuss large images, running as root, missing health checks, build caching, secrets, and deployment hygiene.",
    },
    {
        "title": "System Design: How to Handle High Traffic Without Breaking Your App",
        "slug": "system-design-high-traffic",
        "tags": ["System Design", "Architecture", "Backend"],
        "keywords": "system design high traffic, load balancing, horizontal scaling, caching strategy, scalable backend",
        "prompt_hint": "Explain load balancing, caching, read replicas, queues, CDN, rate limiting, database pressure, and incident preparation.",
    },
    {
        "title": "GraphQL vs REST: My Honest Opinion After Using Both",
        "slug": "graphql-vs-rest-honest-opinion",
        "tags": ["GraphQL", "REST", "API Design"],
        "keywords": "GraphQL vs REST, API design, REST API best practices, GraphQL production",
        "prompt_hint": "Compare GraphQL and REST honestly with team size, frontend complexity, caching, debugging, and maintenance tradeoffs.",
    },
    {
        "title": "TypeScript Tips That Genuinely Improved My Code Quality",
        "slug": "typescript-tips-code-quality",
        "tags": ["TypeScript", "JavaScript", "Best Practices"],
        "keywords": "TypeScript best practices, TypeScript strict mode, type safety, JavaScript code quality",
        "prompt_hint": "Cover strict mode, discriminated unions, utility types, generics, type guards, and avoiding unsafe any.",
    },
    {
        "title": "Implementing JWT Auth the Right Way in Node.js",
        "slug": "jwt-auth-nodejs-right-way",
        "tags": ["Node.js", "Security", "Auth"],
        "keywords": "JWT authentication Node.js, refresh tokens, access tokens, auth security, httpOnly cookies",
        "prompt_hint": "Explain access tokens, refresh token rotation, revocation, httpOnly cookies, CSRF, and common security mistakes.",
    },
    {
        "title": "Legacy Code Migration: How I Approach It Without Breaking Everything",
        "slug": "legacy-code-migration-approach",
        "tags": ["Migration", "Architecture", "Backend"],
        "keywords": "legacy code migration, strangler pattern, technical debt, software modernization",
        "prompt_hint": "Explain incremental migration, keeping old and new systems together, test coverage, data safety, and rollout strategy.",
    },
]


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def strip_tags(value: str) -> str:
    return re.sub(r"<.*?>", "", value)


def escape_attr(value: str) -> str:
    return html.escape(strip_tags(value), quote=True)


def import_boto3() -> Any:
    try:
        import boto3
    except ImportError as exc:
        print("boto3 not installed; attempting to bootstrap pip and install it...")
        try:
            import pip  # type: ignore
        except ImportError:
            try:
                import ensurepip
                ensurepip.bootstrap(upgrade=True)
            except Exception:
                raise RuntimeError(
                    "Missing dependency: boto3 is required to use AWS Bedrock. "
                    "Automatic pip bootstrap failed. Install boto3 manually with 'python -m pip install boto3' "
                    "or use a Python environment where boto3 is already installed."
                ) from exc
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "boto3"])
            import boto3
        except subprocess.CalledProcessError as install_exc:
            raise RuntimeError(
                "Missing dependency: boto3 is required to use AWS Bedrock. "
                "Automatic installation failed. Install it manually with 'python -m pip install boto3' "
                "or use a Python environment where boto3 is already installed."
            ) from install_exc
    return boto3


def get_bedrock_model() -> str | None:
    model_id = os.environ.get("BEDROCK_MODEL_ID")
    if model_id:
        return model_id

    boto3 = import_boto3()
    try:
        client = boto3.client("bedrock")
        response = client.list_foundation_models(byOutputModality="TEXT")
        available: list[str] = [
            m["modelId"] for m in response.get("modelSummaries", []) if m.get("modelId")
        ]
    except Exception as exc:
        print(f"Bedrock model lookup failed: {exc}")
        return None

    print(f"Available Bedrock models: {available}")
    for preferred in PREFERRED_BEDROCK_MODELS:
        match = next((m for m in available if m.startswith(preferred)), None)
        if match:
            return match

    return available[0] if available else None


def generate_with_bedrock(model_id: str, topic: dict[str, Any], date_str: str) -> str:
    system_prompt = (
        "You are Jainam Mehta, a senior Indian backend engineer with 8+ years of production experience. "
        "Write like a real engineer, not like AI content. Keep it human sounding, conversational, and practical. "
        "Use Indian English naturally: simple, direct, slightly imperfect, not overly polished. "
        "Use short paragraphs. Avoid corporate tone, marketing language, hype, and generic motivational lines. "
        "Explain production-level backend thinking with practical examples, tradeoffs, and failure cases. "
        "Include Node.js examples when relevant. Include Redis, queues, caching, rate limiting, idempotency, "
        "database pressure, observability, and system design concepts naturally where they fit. "
        "Write 1200 to 1800 words with SEO-friendly ## headings. "
        "The content area is AI + Backend Engineering + Production Systems. "
        "Use target keywords naturally for SEO, but do not stuff keywords. "
        "Do not use the words freelance, freelancer, or freelancing. "
        "Avoid fake stories, fake metrics, and overclaiming. "
        "Format only in Markdown with ## headings, paragraphs, short bullet lists, and fenced code blocks. "
        "End with a ## My Practical Takeaway section."
    )
    user_prompt = (
        f"Write today's technical blog post for {date_str}.\n\n"
        f"Topic: {topic['title']}\n"
        f"Tags: {', '.join(topic['tags'])}\n"
        f"Target keywords: {topic['keywords']}\n"
        f"Angle: {topic['prompt_hint']}\n\n"
        "Make it practical, honest, readable, and useful for backend developers and engineering teams. "
        "Add at least one small Node.js code example and one Redis or system design example. "
        "Keep paragraphs short and avoid overly polished English."
    )
    print(f"Generating post with Bedrock model: {model_id}")

    boto3 = import_boto3()
    try:
        client = boto3.client("bedrock-runtime")
        response = client.converse(
            modelId=model_id,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            inferenceConfig={
                "temperature": 0.68,
                "topP": 0.9,
                "maxTokens": 2600,
            },
        )
    except Exception as exc:
        raise RuntimeError(f"Bedrock generation failed: {exc}") from exc

    try:
        generated = response["output"]["message"]["content"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Bedrock returned unexpected response structure: {response}") from exc

    return generated.strip()


def markdown_to_html(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").split("\n")
    parts: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    code_lines: list[str] = []
    in_code_block = False
    code_language = ""

    def flush_paragraph() -> None:
        if paragraph:
            text = " ".join(paragraph).strip()
            text = html.escape(text)
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
            parts.append(f"<p>{text}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            parts.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items.clear()

    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("```"):
            if in_code_block:
                code = html.escape("\n".join(code_lines))
                lang_class = f' class="language-{html.escape(code_language)}"' if code_language else ""
                parts.append(f"<pre><code{lang_class}>{code}</code></pre>")
                code_lines.clear()
                code_language = ""
                in_code_block = False
            else:
                flush_paragraph()
                flush_list()
                code_language = line[3:].strip().split(" ", 1)[0]
                in_code_block = True
            continue
        if in_code_block:
            code_lines.append(raw_line.rstrip())
            continue
        if not line:
            flush_paragraph()
            flush_list()
            continue
        if line.startswith("## "):
            flush_paragraph()
            flush_list()
            parts.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
            continue
        if line.startswith("### "):
            flush_paragraph()
            flush_list()
            parts.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
            continue
        if line.startswith(("- ", "* ")):
            flush_paragraph()
            item = html.escape(line[2:].strip())
            item = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item)
            item = re.sub(r"`(.+?)`", r"<code>\1</code>", item)
            list_items.append(item)
            continue
        flush_list()
        paragraph.append(line)

    flush_paragraph()
    flush_list()
    if in_code_block:
        code = html.escape("\n".join(code_lines))
        parts.append(f"<pre><code>{code}</code></pre>")
    return "\n".join(parts)


def extract_excerpt(content_html: str, fallback: str) -> str:
    first_paragraph = re.search(r"<p>(.*?)</p>", content_html, flags=re.DOTALL)
    if not first_paragraph:
        return fallback
    excerpt = html.unescape(strip_tags(first_paragraph.group(1)))
    excerpt = re.sub(r"\s+", " ", excerpt).strip()
    return excerpt[:200]


def remove_duplicate_title_heading(content_html: str, title: str) -> str:
    escaped_title = re.escape(html.escape(title))
    pattern = rf"^\s*<h2>{escaped_title}</h2>\s*"
    return re.sub(pattern, "", content_html, count=1)


def create_post_html(topic: dict[str, Any], content_html: str, date_str: str, date_display: str, slug: str) -> str:
    title = topic["title"]
    canonical = f"{SITE_URL}/blog/posts/{slug}.html"
    tags_html = "".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in topic["tags"])
    meta_desc = escape_attr(extract_excerpt(content_html, f"{title} by {AUTHOR}.")[:160])
    keywords = escape_attr(f"{topic['keywords']}, Jainam Mehta blog")
    json_ld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "url": canonical,
        "datePublished": date_str,
        "dateModified": date_str,
        "author": {"@type": "Person", "name": AUTHOR_FULL, "url": f"{SITE_URL}/"},
        "publisher": {"@type": "Person", "name": AUTHOR_FULL},
        "description": html.unescape(meta_desc),
        "keywords": topic["keywords"],
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "image": f"{SITE_URL}/assets/1738839200854.jpeg",
    }

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-XYH3ZYB3G3"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-XYH3ZYB3G3');
  </script>

  <link rel="apple-touch-icon" sizes="180x180" href="/assets/apple-touch-icon.png" />
  <link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32x32.png" />
  <link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon-16x16.png" />
  <link rel="manifest" href="/assets/site.webmanifest" />

  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1" />
  <title>{html.escape(title)} | Jainam Mehta</title>
  <meta name="description" content="{meta_desc}" />
  <meta name="keywords" content="{keywords}" />
  <meta name="author" content="{AUTHOR_FULL}" />

  <meta property="og:type" content="article" />
  <meta property="og:title" content="{html.escape(title)} | Jainam Mehta" />
  <meta property="og:description" content="{meta_desc}" />
  <meta property="og:url" content="{canonical}" />
  <meta property="og:image" content="{SITE_URL}/assets/1738839200854.jpeg" />
  <meta property="article:author" content="{AUTHOR_FULL}" />
  <meta property="article:published_time" content="{date_str}" />

  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{html.escape(title)}" />
  <meta name="twitter:description" content="{meta_desc}" />
  <meta name="twitter:image" content="{SITE_URL}/assets/1738839200854.jpeg" />

  <link rel="canonical" href="{canonical}" />
  <link rel="stylesheet" href="/assets/style.css" />
  <style>{POST_CRITICAL_CSS}</style>
  <script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False)}</script>
</head>
<body>
  <header>
    <nav>
      <div class="nav-inner">
        <a href="/" class="logo">Jainam Mehta</a>
        <div class="links">
          <a href="/#about">About</a>
          <a href="/#services">Services</a>
          <a href="/#projects">Work</a>
          <a href="/blog/" class="accent">Blog</a>
          <a href="/#contact" class="btn">Contact</a>
        </div>
      </div>
    </nav>
  </header>

  <article class="post-wrap" itemscope itemtype="https://schema.org/BlogPosting">
    <a href="/blog/" class="back-link">Back to Blog</a>
    <header class="post-header">
      <div class="post-tags">{tags_html}</div>
      <h1 itemprop="headline">{html.escape(title)}</h1>
      <div class="post-meta">
        <span>By <strong itemprop="author">{AUTHOR}</strong></span>
        <span itemprop="datePublished" content="{date_str}">{date_display}</span>
        <span>7 min read</span>
      </div>
    </header>

    <div class="post-body" itemprop="articleBody">
{content_html}
    </div>

    <footer class="post-footer">
      <p>
        Written by <a href="/">{AUTHOR}</a>, Senior Software Engineer working with Node.js, Next.js,
        AI systems, ecommerce platforms, and backend architecture.
      </p>
      <p>
        <a href="https://www.linkedin.com/in/jainam-mehta/" rel="noopener noreferrer">Connect on LinkedIn</a>
      </p>
    </footer>
  </article>
</body>
</html>
"""


def load_existing_posts_meta() -> list[dict[str, Any]]:
    meta: list[dict[str, Any]] = []
    if not POSTS_DIR.exists():
        return meta

    for html_file in POSTS_DIR.glob("*.html"):
        text = html_file.read_text(encoding="utf-8")
        title_match = re.search(r"<title>\s*(.*?)\s*</title>", text, flags=re.DOTALL)
        date_match = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})"', text)
        desc_match = re.search(
            r'<meta\s+[^>]*name="description"[^>]*content="(.*?)"',
            text,
            flags=re.DOTALL,
        )
        tags = re.findall(r'<span class="tag">\s*(.*?)\s*</span\s*>', text, flags=re.DOTALL)
        if not title_match or not date_match:
            continue
        date = dt.date.fromisoformat(date_match.group(1))
        title = re.sub(r"\s+", " ", html.unescape(title_match.group(1))).strip()
        title = re.sub(r"\s*\|\s*Jainam Mehta$", "", title).strip()
        meta.append(
            {
                "slug": html_file.stem,
                "title": title,
                "date": date.isoformat(),
                "date_display": date.strftime("%B %d, %Y"),
                "excerpt": html.unescape(desc_match.group(1)) if desc_match else "",
                "tags": [re.sub(r"\s+", " ", html.unescape(strip_tags(tag))).strip() for tag in tags[:3]],
            }
        )
    return meta


def update_blog_index(posts_meta: list[dict[str, Any]]) -> None:
    index_path = BLOG_DIR / "index.html"
    content = index_path.read_text(encoding="utf-8")

    cards = ['<div class="blog-grid">']
    for post in sorted(posts_meta, key=lambda item: item["date"], reverse=True):
        tags_html = "".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in post["tags"])
        title = html.escape(post["title"])
        excerpt = html.escape(strip_tags(post["excerpt"]))
        date_display = html.escape(post["date_display"])
        slug = html.escape(post["slug"])
        cards.append(
            f"""  <article class="blog-card">
    <div>{tags_html}</div>
    <h2><a href="/blog/posts/{slug}.html">{title}</a></h2>
    <p class="excerpt">{excerpt}</p>
    <div class="meta">
      <span>{date_display}</span>
      <a href="/blog/posts/{slug}.html" class="read-more">Read</a>
    </div>
  </article>"""
        )
    cards.append("</div>")
    cards_html = "\n".join(cards)

    updated = re.sub(
        r"<!-- POSTS_START -->.*?<!-- POSTS_END -->",
        f"<!-- POSTS_START -->\n{cards_html}\n  <!-- POSTS_END -->",
        content,
        flags=re.DOTALL,
    )
    index_path.write_text(updated, encoding="utf-8")
    print("Updated blog/index.html")


def update_sitemap(posts_meta: list[dict[str, Any]]) -> None:
    today = dt.date.today().isoformat()
    urls = [
        (f"{SITE_URL}/", today, "monthly", "1.0"),
        (f"{SITE_URL}/blog/", today, "daily", "0.9"),
    ]
    for post in sorted(posts_meta, key=lambda item: item["date"], reverse=True):
        urls.append((f"{SITE_URL}/blog/posts/{post['slug']}.html", post["date"], "monthly", "0.7"))

    body = "\n".join(
        f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>"""
        for loc, lastmod, changefreq, priority in urls
    )
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{body}
</urlset>
"""
    (REPO_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    print("Updated sitemap.xml")


def git_command(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    safe_dir = REPO_DIR.as_posix()
    command = ["git", "-c", f"safe.directory={safe_dir}", "-C", str(REPO_DIR), *args]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    if check and result.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(args)}")
    return result


def publish_to_git(date_str: str, slug: str) -> None:
    git_command(
        "add",
        "index.html",
        "blog",
        "sitemap.xml",
        "generate_blog.py",
        "daily_publish_blog.bat",
        "pull_blog_models.bat",
        "install_blog_startup_task.bat",
    )
    status = git_command("status", "--porcelain")
    if not status.stdout.strip():
        print("No git changes to publish.")
        return

    commit = git_command("commit", "-m", f"blog: publish {slug} [{date_str}]")
    if commit.returncode != 0:
        print("Commit did not complete. Push skipped.")
        return

    branch_result = git_command("rev-parse", "--abbrev-ref", "HEAD")
    branch = branch_result.stdout.strip() or "main"
    pushed = git_command("push", "origin", branch)
    if pushed.returncode != 0:
        print("Push did not complete. Check remote/authentication and run git push manually if needed.")


def ensure_daily_task_hint() -> None:
    print("")
    print("For automatic publishing when the laptop opens, run once:")
    print("  install_blog_startup_task.bat")
    print("The task runs at Windows logon. The generator publishes only one post per date.")


def main() -> None:
    today = dt.date.today()
    date_str = today.isoformat()
    date_display = today.strftime("%B %d, %Y")
    topic = TOPICS[today.timetuple().tm_yday % len(TOPICS)]
    slug = f"{date_str}-{slugify(topic['slug'])}"
    post_path = POSTS_DIR / f"{slug}.html"

    if post_path.exists():
        print(f"Today's post already exists: blog/posts/{slug}.html")
        all_posts = load_existing_posts_meta()
        update_blog_index(all_posts)
        update_sitemap(all_posts)
        publish_to_git(date_str, slug)
        return

    model = get_bedrock_model()
    if not model:
        print(
            "ERROR: Could not find an AWS Bedrock model. "
            "Set BEDROCK_MODEL_ID or ensure your AWS Bedrock configuration is correct."
        )
        sys.exit(1)

    raw_content = generate_with_bedrock(model, topic, date_str)
    if len(raw_content) < 400:
        print("ERROR: Bedrock returned content that is too short. Please rerun.")
        sys.exit(1)

    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    content_html = markdown_to_html(raw_content)
    content_html = remove_duplicate_title_heading(content_html, topic["title"])
    post_path.write_text(create_post_html(topic, content_html, date_str, date_display, slug), encoding="utf-8")
    print(f"Created blog/posts/{slug}.html")

    all_posts = load_existing_posts_meta()
    if not any(post["slug"] == slug for post in all_posts):
        all_posts.append(
            {
                "slug": slug,
                "title": topic["title"],
                "date": date_str,
                "date_display": date_display,
                "excerpt": extract_excerpt(content_html, topic["title"]),
                "tags": topic["tags"],
            }
        )

    update_blog_index(all_posts)
    update_sitemap(all_posts)
    publish_to_git(date_str, slug)
    ensure_daily_task_hint()
    print(f"Done: {SITE_URL}/blog/posts/{slug}.html")


if __name__ == "__main__":
    started = time.time()
    try:
        main()
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    finally:
        print(f"Finished in {time.time() - started:.1f}s")
