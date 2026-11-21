#!/usr/bin/env python3
"""Build the OpenMobilityData site from catalogue.toml and content/about.md.

    python3 build.py                 write the pages at the repository root
    python3 build.py --check-links   also check that every linked file exists
                                     (sibling clones under the parent folder;
                                     `gh` for repositories not cloned here)

Standard library only (Python 3.11 or later, for tomllib). The pages are
plain HTML with relative links, so the site also opens from a local folder.
"""
from __future__ import annotations

import html
import re
import subprocess
import sys
import tomllib
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLONES = ROOT.parent
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

STATUS = {
    "record": ("Record, as issued", "record"),
    "checked": ("Transcript, checked by ear", "checked"),
    "machine-draft": ("Machine draft, unchecked", "warn"),
    "analysis": ("Analysis", "analysis"),
    "preliminary": ("Preliminary, not peer reviewed", "warn"),
    "draft": ("Draft", "warn"),
    "data": ("Data", "data"),
    "app": ("Web application", "data"),
    "tool": ("Tool", "data"),
}


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def show_date(d: str | None) -> str:
    """'2026-11-12' -> 'November 12, 2026'; '2026-06' -> 'June 2026'; '2023' -> '2023'."""
    if not d:
        return ""
    parts = d.split("-")
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{MONTHS[int(parts[1]) - 1]} {parts[0]}"
    return f"{MONTHS[int(parts[1]) - 1]} {int(parts[2])}, {parts[0]}"


def sort_key(d: str | None) -> str:
    """Pad a partial date so that '2023' < '2023-06' < '2023-06-01'."""
    return ((d or "0000") + "-00-00")[:10]


class Site:
    def __init__(self) -> None:
        self.cat = tomllib.loads((ROOT / "catalogue.toml").read_text(encoding="utf-8"))
        self.site = self.cat["site"]
        self.org = self.site["org"]
        self.pages_repos = set(self.site["pages_repos"])
        self.topics = self.cat["topic"]
        self.entries = self.cat["entry"]
        self.problems: list[str] = []
        self.by_date = {f"{t['id']}/{s[0]}" for t in self.topics for s in t["sections"]
                        if len(s) > 3 and s[3] == "by-date"}
        self.validate()

    # ---------------------------------------------------------------- data

    def validate(self) -> None:
        places = {f"{t['id']}/{s[0]}" for t in self.topics for s in t["sections"]}
        seen: set[str] = set()
        for e in self.entries:
            if e["id"] in seen:
                self.problems.append(f"duplicate id: {e['id']}")
            seen.add(e["id"])
            for at in [e["at"], *e.get("also", [])]:
                if at not in places:
                    self.problems.append(f"{e['id']}: unknown place {at}")
            if e["status"] not in STATUS:
                self.problems.append(f"{e['id']}: unknown status {e['status']}")

    def in_place(self, place: str) -> list[dict]:
        own = [e for e in self.entries if e["at"] == place]
        more = [e for e in self.entries if place in e.get("also", [])]
        if place in self.by_date:
            return sorted(own + more, key=lambda e: sort_key(e.get("date")))
        return own + more

    def in_topic(self, topic: dict) -> list[dict]:
        ids: dict[str, dict] = {}
        for s in topic["sections"]:
            for e in self.in_place(f"{topic['id']}/{s[0]}"):
                ids[e["id"]] = e
        return list(ids.values())

    # ---------------------------------------------------------------- urls

    def folder_url(self, e: dict) -> str:
        base = f"https://github.com/{self.org}/{e['repo']}"
        if e.get("no_readme"):
            return base
        if e.get("path"):
            return f"{base}/blob/main/{e['path']}/README.md"
        return f"{base}/blob/main/README.md"

    def file_url(self, repo: str, path: str) -> str:
        if repo in self.pages_repos:
            return f"https://{self.site['domain']}/{repo}/{path}"
        return f"https://github.com/{self.org}/{repo}/blob/main/{path}"

    def links(self, e: dict) -> list[tuple[str, str]]:
        out = []
        for ln in e.get("links", []):
            url = ln["url"] if "url" in ln else self.file_url(e["repo"], ln["path"])
            out.append((ln["label"], url))
        return out

    def main_url(self, e: dict) -> str:
        ls = self.links(e)
        return ls[0][1] if ls else self.folder_url(e)

    # ------------------------------------------------------------- checking

    def check_links(self) -> None:
        def exists(repo: str, path: str) -> bool | None:
            clone = CLONES / repo
            if clone.is_dir():
                return (clone / path).exists()
            try:
                r = subprocess.run(
                    ["gh", "api", f"repos/{self.org}/{repo}/contents/{path}", "--silent"],
                    capture_output=True, timeout=30)
                return r.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                return None

        for e in self.entries:
            targets = []
            if not e.get("no_readme"):
                targets.append((e.get("path", "") + "/README.md").lstrip("/"))
            targets += [ln["path"] for ln in e.get("links", []) if "path" in ln]
            for t in targets:
                ok = exists(e["repo"], t)
                if ok is False:
                    self.problems.append(f"{e['id']}: missing {e['repo']}/{t}")
                elif ok is None:
                    self.problems.append(f"{e['id']}: could not check {e['repo']}/{t}")

    # ------------------------------------------------------------ fragments

    def chip(self, e: dict) -> str:
        label, cls = STATUS[e["status"]]
        return f'<span class="chip chip-{cls}">{esc(label)}</span>'

    def card(self, e: dict) -> str:
        links = self.links(e)
        items = [f'<a href="{esc(u)}">{esc(lab)}</a>' for lab, u in links]
        items.append(f'<a class="src" href="{esc(self.folder_url(e))}">Folder and sources</a>')
        when = f'<span class="when">{esc(show_date(e.get("date")))}</span>' if e.get("date") else ""
        return (
            f'<article class="card" id="{esc(e["id"])}">'
            f'<div class="meta">{self.chip(e)}{when}</div>'
            f'<h3><a href="{esc(self.main_url(e))}">{esc(e["title"])}</a></h3>'
            f'<p>{esc(e["summary"])}</p>'
            f'<p class="links">{" ".join(items)}</p>'
            f'</article>')

    def page(self, name: str, title: str, body: str, current: str = "") -> None:
        nav = [("index.html", "Home", "home")]
        nav += [(f"{t['id']}.html", t.get("nav", t["title"]), t["id"]) for t in self.topics]
        nav += [("all.html", "All documents", "all"), ("about.html", "About", "about")]
        nav_html = "".join(
            f'<a href="{href}"{" aria-current=\"page\"" if key == current else ""}>{esc(label)}</a>'
            for href, label, key in nav)
        full_title = self.site["name"] if current == "home" else f"{title} · {self.site['name']}"
        doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(self.site['tagline'])}">
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
<a class="skip" href="#main">Skip to the content</a>
<header class="top">
<div class="wrap">
<a class="brand" href="index.html"><span class="brand-name">{esc(self.site['name'])}</span><span class="brand-tag">{esc(self.site['tagline'])}</span></a>
<nav aria-label="Sections">{nav_html}</nav>
</div>
</header>
<main id="main" class="wrap">
{body}
</main>
<footer class="foot">
<div class="wrap">
<p>Rick Hoge, PhD. A data analysis from public records, done on the author's own initiative; see <a href="about.html">About</a>.</p>
<p>Corrections are welcome through the issue tracker of the repository concerned, on <a href="https://github.com/{esc(self.org)}">GitHub</a>. Page generated on {esc(show_date(date.today().isoformat()))}.</p>
</div>
</footer>
<script src="assets/site.js" defer></script>
</body>
</html>
"""
        (ROOT / name).write_text(doc, encoding="utf-8")

    # ---------------------------------------------------------------- pages

    def build_home(self) -> None:
        intro = "".join(f"<p>{esc(p.strip())}</p>" for p in self.site["intro"].strip().split("\n\n"))
        cards = []
        for t in self.topics:
            n = len(self.in_topic(t))
            secs = " · ".join(esc(s[1]) for s in t["sections"])
            cards.append(
                f'<a class="topic" href="{t["id"]}.html"><h3>{esc(t["title"])}</h3>'
                f'<p>{esc(t["lede"])}</p><p class="secs">{secs}</p>'
                f'<p class="count">{n} {"entry" if n == 1 else "entries"}</p></a>')
        start = "".join(self.card(e) for e in self.in_place("terrebonne/start"))
        dated = [e for e in self.entries if len(e.get("date", "")) == 10]
        latest = sorted(dated, key=lambda e: e["date"], reverse=True)[:8]
        rows = "".join(
            f'<li><span class="when">{esc(show_date(e["date"]))}</span>'
            f'<a href="{esc(self.main_url(e))}">{esc(e["title"])}</a>{self.chip(e)}</li>'
            for e in latest)
        ask = (f'https://github.com/{self.org}/.github/blob/main/ASK_AN_AI_en.md')
        body = f"""
<section class="intro">
<h1>{esc(self.site['tagline'])}</h1>
{intro}
</section>
<section>
<h2>Topics</h2>
<div class="topics">{''.join(cards)}</div>
</section>
<section>
<h2>Start here</h2>
<div class="cards">{start}</div>
</section>
<section>
<h2>Most recent</h2>
<p class="blurb">By the date of the document or of the analysis.</p>
<ul class="latest">{rows}</ul>
<p><a href="all.html">All {len(self.entries)} entries</a></p>
</section>
<section class="note">
<h2>Ask an AI assistant</h2>
<p>To search these records with an AI assistant that can read web pages, copy the <a href="{esc(ask)}">ready-made preamble</a>, add your question, and check the pages it cites.</p>
</section>
"""
        self.page("index.html", self.site["name"], body, "home")

    def build_topic(self, t: dict) -> None:
        jump = "".join(f'<a href="#{s[0]}">{esc(s[1])}</a>' for s in t["sections"])
        parts = []
        for sid, stitle, blurb, *_ in t["sections"]:
            es = self.in_place(f"{t['id']}/{sid}")
            if not es:
                continue
            b = f'<p class="blurb">{esc(blurb)}</p>' if blurb else ""
            parts.append(
                f'<section id="{sid}"><h2>{esc(stitle)}</h2>{b}'
                f'<div class="cards">{"".join(self.card(e) for e in es)}</div></section>')
        body = f"""
<section class="intro">
<h1>{esc(t['title'])}</h1>
<p>{esc(t['lede'])}</p>
<nav class="jump" aria-label="On this page">{jump}</nav>
</section>
{''.join(parts)}
"""
        self.page(f"{t['id']}.html", t["title"], body, t["id"])

    def build_all(self) -> None:
        topic_title = {t["id"]: t["title"] for t in self.topics}
        opts = "".join(f'<option value="{k}">{esc(v[0])}</option>' for k, v in STATUS.items())
        rows = []
        for e in sorted(self.entries, key=lambda e: sort_key(e.get("date")), reverse=True):
            tid = e["at"].split("/")[0]
            text = " ".join([e["title"], e["summary"], topic_title[tid], e["repo"]]).lower()
            rows.append(
                f'<tr data-status="{e["status"]}" data-text="{esc(text)}">'
                f'<td><a href="{esc(self.main_url(e))}">{esc(e["title"])}</a>'
                f'<span class="sub">{esc(e["summary"])}</span></td>'
                f'<td>{self.chip(e)}</td>'
                f'<td class="nowrap">{esc(show_date(e.get("date")))}</td>'
                f'<td><a href="{tid}.html#{e["id"]}">{esc(topic_title[tid])}</a></td></tr>')
        body = f"""
<section class="intro">
<h1>All documents</h1>
<p>Every entry of the catalogue, newest first. Type to filter by word; the list narrows as you type.</p>
<form class="filter" role="search" onsubmit="return false">
<label>Filter <input id="q" type="search" placeholder="for example: counter, parking, transcript" autocomplete="off"></label>
<label>Kind <select id="kind"><option value="">All</option>{opts}</select></label>
<span id="n" aria-live="polite"></span>
</form>
</section>
<div class="tablewrap">
<table class="all">
<thead><tr><th>Document</th><th>Kind</th><th>Date</th><th>Topic</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</div>
"""
        self.page("all.html", "All documents", body, "all")

    def build_about(self) -> None:
        body = '<section class="prose">' + markdown((ROOT / "content" / "about.md").read_text(encoding="utf-8")) + "</section>"
        self.page("about.html", "About", body, "about")

    def build_404(self) -> None:
        body = ('<section class="intro"><h1>Page not found</h1>'
                '<p>The address may have changed. The <a href="/all.html">list of all documents</a> '
                'and the <a href="/index.html">home page</a> are the two ways back in.</p></section>')
        self.page("404.html", "Page not found", body)
        p = ROOT / "404.html"   # a 404 page is served from any depth: absolute asset links
        p.write_text(p.read_text(encoding="utf-8")
                     .replace('href="assets/', 'href="/assets/').replace('src="assets/', 'src="/assets/')
                     .replace('href="index.html"', 'href="/index.html"'), encoding="utf-8")

    def build(self) -> None:
        self.build_home()
        for t in self.topics:
            self.build_topic(t)
        self.build_all()
        self.build_about()
        self.build_404()


def markdown(src: str) -> str:
    """A small subset: #/##/### headings, paragraphs, '- ' lists, [text](url), **bold**, `code`."""
    def inline(s: str) -> str:
        s = esc(s)
        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)

    out: list[str] = []
    for block in re.split(r"\n\s*\n", src.strip()):
        lines = block.strip().split("\n")
        m = re.match(r"(#{1,3}) (.*)", lines[0])
        if m and len(lines) == 1:
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        elif all(ln.startswith("- ") for ln in lines):
            out.append("<ul>" + "".join(f"<li>{inline(ln[2:])}</li>" for ln in lines) + "</ul>")
        else:
            out.append(f"<p>{inline(' '.join(lines))}</p>")
    return "\n".join(out)


def main() -> int:
    s = Site()
    if "--check-links" in sys.argv:
        s.check_links()
    if s.problems:
        print("\n".join(s.problems), file=sys.stderr)
        return 1
    s.build()
    print(f"{len(s.entries)} entries, {len(s.topics)} topics: pages written to {ROOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
