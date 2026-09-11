#!/usr/bin/env python3
"""
Deck Craft local library dashboard — personal metrics + organised deck links.

Usage:
    python3 dashboard.py              # serve on the first free port from 8791
    python3 dashboard.py --launch     # start/reuse background server, then open browser
    python3 dashboard.py --restart    # force-restart the background server
    python3 dashboard.py --stop       # stop the background server
    python3 dashboard.py --port 9000  # pin a specific port
    python3 dashboard.py --no-open    # don't launch browser
    python3 dashboard.py --register path/to/deck.html [path/to/deck.md]
    python3 dashboard.py --import-dir ~/Decks   # scan existing local deck folders
    python3 dashboard.py --json       # print metrics + deck list as JSON and exit

Data is read from ~/.deck-craft/library.json (written by build.py). Nothing leaves
this machine — bind address is 127.0.0.1 only. An /api/ping marker identifies our
own server, so an unrelated local app on the same port is never opened by mistake.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError
from urllib.parse import unquote, urlparse
from urllib.request import ProxyHandler, build_opener

# Corporate HTTP(S)_PROXY must not apply to loopback health checks.
_LOOPBACK_OPENER = build_opener(ProxyHandler({}))

SELF_DIR = os.path.dirname(os.path.abspath(__file__))
if SELF_DIR not in sys.path:
    sys.path.insert(0, SELF_DIR)

from library import (  # noqa: E402
    decks_grouped,
    import_directory,
    library_path,
    load_library,
    metrics,
    prune_missing,
    register_existing,
)

DEFAULT_PORT = 8791
PORT_SCAN_LIMIT = 12  # ports tried after the default before giving up
APP_ID = "deck-craft-dashboard"


def _rel_home(path):
    home = os.path.expanduser("~")
    if path.startswith(home + os.sep):
        return "~" + path[len(home):]
    return path


def _fmt_when(iso):
    if not iso:
        return "—"
    try:
        s = iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt.astimezone().strftime("%d %b %Y · %H:%M")
    except ValueError:
        return iso


def library_payload():
    lib, removed = prune_missing()
    m = metrics(lib)
    groups = []
    for parent, decks in decks_grouped(lib):
        groups.append({
            "parent": parent,
            "parent_display": _rel_home(parent),
            "folder": os.path.basename(parent) or parent,
            "decks": [{
                "id": d["id"],
                "title": d.get("title") or "Untitled",
                "subtitle": d.get("subtitle") or "",
                "classification": d.get("classification") or "",
                "slide_count": d.get("slide_count", 0),
                "build_count": d.get("build_count", 0),
                "updated_at": d.get("updated_at") or "",
                "updated_display": _fmt_when(d.get("updated_at")),
                "created_display": _fmt_when(d.get("created_at")),
                "html": d.get("html") or "",
                "source": d.get("source") or "",
                "html_display": _rel_home(d.get("html") or ""),
                "open_url": "/open/%s" % d["id"],
                "exists": os.path.isfile(d.get("html") or ""),
            } for d in decks],
        })
    recent = sorted(lib.get("builds", []), key=lambda b: b.get("at") or "", reverse=True)[:12]
    return {
        "metrics": m,
        "groups": groups,
        "recent_builds": [{
            "title": b.get("title") or "Untitled",
            "at": b.get("at") or "",
            "at_display": _fmt_when(b.get("at")),
            "slides": b.get("slides", 0),
            "deck_id": b.get("deck_id") or "",
        } for b in recent],
        "library_path": library_path(),
        "library_path_display": _rel_home(library_path()),
        "import_roots": [_rel_home(r) for r in lib.get("import_roots", [])],
        "pruned": removed,
    }


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Deck Craft · Library</title>
<style>
:root {
  --ink: #101114;
  --ink-soft: #3c4048;
  --muted: #8a9099;
  --line: #e7e9ee;
  --bg: #f6f7f9;
  --surface: #ffffff;
  --accent: #4b6bff;
  --accent-soft: rgba(75, 107, 255, 0.1);
  --font: "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif;
  --display: "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif;
  --radius: 14px;
  --shadow: 0 10px 40px rgba(16, 17, 20, 0.06);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  font-family: var(--font);
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(75,107,255,0.08), transparent 60%),
    radial-gradient(900px 500px at 100% 0%, rgba(0,194,199,0.06), transparent 55%),
    var(--bg);
  color: var(--ink);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}
.topbar { height: 4px; background: var(--accent); }
.wrap { max-width: 1080px; margin: 0 auto; padding: 36px 28px 80px; }
header {
  display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between;
  gap: 20px; margin-bottom: 36px;
}
.brand { display: flex; flex-direction: column; gap: 8px; }
.brand .eyebrow {
  font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--muted); font-weight: 600;
}
.brand h1 {
  font-family: var(--display); font-size: clamp(28px, 4vw, 40px);
  font-weight: 700; letter-spacing: -0.02em; line-height: 1.1;
}
.brand p { color: var(--ink-soft); font-size: 15px; max-width: 42ch; line-height: 1.45; }
.meta-chip {
  font-size: 12px; color: var(--muted); background: var(--surface);
  border: 1px solid var(--line); border-radius: 999px; padding: 8px 14px;
  font-variant-numeric: tabular-nums;
}
.metrics {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px;
  margin-bottom: 28px;
}
@media (max-width: 820px) { .metrics { grid-template-columns: repeat(2, 1fr); } }
.metric {
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 18px 20px; box-shadow: var(--shadow);
}
.metric .label { font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--muted); font-weight: 600; margin-bottom: 8px; }
.metric .value { font-size: 32px; font-weight: 700; letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums; }
.metric .hint { margin-top: 4px; font-size: 13px; color: var(--ink-soft); }

.toolbar {
  display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
  margin-bottom: 22px;
}
.toolbar input[type="search"] {
  flex: 1; min-width: 200px; border: 1px solid var(--line); border-radius: 12px;
  padding: 12px 16px; font: inherit; font-size: 15px; background: var(--surface);
  outline: none; transition: border-color .15s, box-shadow .15s;
}
.toolbar input[type="search"]:focus {
  border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft);
}
.seg {
  display: inline-flex; background: var(--surface); border: 1px solid var(--line);
  border-radius: 12px; padding: 3px; gap: 2px;
}
.seg button {
  border: none; background: transparent; padding: 8px 14px; border-radius: 9px;
  font: inherit; font-size: 13px; font-weight: 600; color: var(--ink-soft);
  cursor: pointer;
}
.seg button[aria-pressed="true"] {
  background: var(--accent); color: #fff;
}

.layout { display: grid; grid-template-columns: 1fr 280px; gap: 22px; }
@media (max-width: 900px) { .layout { grid-template-columns: 1fr; } }

.view-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px; margin-bottom: 16px;
}
.view-head h2 { font-size: 22px; letter-spacing: -0.02em; }
.view-head .count { font-size: 13px; color: var(--muted); }
.back {
  display: inline-flex; align-items: center; gap: 7px; border: 1px solid var(--line);
  border-radius: 10px; background: var(--surface); color: var(--ink-soft);
  padding: 8px 12px; font: inherit; font-size: 13px; font-weight: 650; cursor: pointer;
}
.back:hover { border-color: var(--accent); color: var(--accent); }
.folder-path {
  color: var(--muted); font-size: 12px; margin: -9px 0 16px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.folder-grid {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px;
}
@media (max-width: 680px) { .folder-grid { grid-template-columns: 1fr; } }
.folder-tile {
  position: relative; width: 100%; text-align: left; border: 1px solid var(--line);
  border-radius: var(--radius); background: var(--surface); color: inherit;
  padding: 20px; font: inherit; cursor: pointer; box-shadow: var(--shadow);
  transition: border-color .15s, transform .15s, box-shadow .15s;
  overflow: hidden;
}
.folder-tile::before {
  content: ""; position: absolute; inset: 0 auto 0 0; width: 4px;
  background: var(--accent); opacity: .85;
}
.folder-tile:hover {
  border-color: var(--accent); transform: translateY(-2px);
  box-shadow: 0 16px 38px rgba(75, 107, 255, 0.13);
}
.folder-tile:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.folder-icon {
  width: 40px; height: 32px; border-radius: 6px; background: var(--accent-soft);
  margin-bottom: 14px; position: relative;
}
.folder-icon::before {
  content: ""; position: absolute; width: 17px; height: 6px; left: 3px; top: -4px;
  background: var(--accent-soft); border-radius: 4px 4px 0 0;
}
.folder-name {
  font-size: 18px; font-weight: 700; letter-spacing: -0.015em;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.folder-path-small {
  font-size: 11px; color: var(--muted); margin-top: 5px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.folder-stats {
  display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px;
  padding-top: 13px; border-top: 1px solid var(--line); color: var(--ink-soft);
  font-size: 12px; font-variant-numeric: tabular-nums;
}
.folder-preview {
  color: var(--muted); font-size: 12px; line-height: 1.45; margin-top: 10px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.deck-list { display: flex; flex-direction: column; gap: 8px; }
.deck {
  display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: center;
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 16px 18px; text-decoration: none; color: inherit;
  transition: border-color .15s, transform .15s, box-shadow .15s;
  box-shadow: var(--shadow);
}
.deck:hover {
  border-color: var(--accent); transform: translateY(-1px);
  box-shadow: 0 14px 36px rgba(75, 107, 255, 0.12);
}
.deck:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.deck .title { font-size: 17px; font-weight: 650; letter-spacing: -0.01em; }
.deck .sub { margin-top: 3px; font-size: 13px; color: var(--ink-soft);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 52ch; }
.deck .path { margin-top: 6px; font-size: 11px; color: var(--muted);
  font-variant-numeric: tabular-nums; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.deck .right { text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
.pill {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600; color: var(--accent);
  background: var(--accent-soft); border-radius: 999px; padding: 5px 10px;
}
.stats-row { font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }

.side {
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 18px; box-shadow: var(--shadow); height: fit-content;
  position: sticky; top: 20px;
}
.side h3 {
  font-size: 12px; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--muted); font-weight: 700; margin-bottom: 14px;
}
.activity { list-style: none; display: flex; flex-direction: column; gap: 12px; }
.activity li { display: grid; grid-template-columns: 8px 1fr; gap: 10px; align-items: start; }
.activity .dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--accent);
  margin-top: 5px;
}
.activity .t { font-size: 14px; font-weight: 600; line-height: 1.25; }
.activity .m { font-size: 12px; color: var(--muted); margin-top: 2px; }

.empty {
  text-align: center; padding: 56px 24px; background: var(--surface);
  border: 1px dashed var(--line); border-radius: var(--radius);
}
.empty h2 { font-size: 20px; margin-bottom: 8px; }
.empty p { color: var(--ink-soft); font-size: 14px; line-height: 1.5; max-width: 42ch; margin: 0 auto 18px; }
.empty code {
  display: inline-block; background: var(--bg); border: 1px solid var(--line);
  border-radius: 8px; padding: 8px 12px; font-size: 13px; color: var(--ink);
}
.note {
  margin-top: 28px; font-size: 12px; color: var(--muted); line-height: 1.5;
}
.hidden { display: none !important; }
</style>
</head>
<body>
<div class="topbar"></div>
<div class="wrap">
  <header>
    <div class="brand">
      <div class="eyebrow">Deck Craft</div>
      <h1>Your library</h1>
      <p>Local metrics and every deck built on this machine. Nothing is uploaded.</p>
    </div>
    <div class="meta-chip" id="lib-path"></div>
  </header>

  <section class="metrics" id="metrics" aria-label="Usage metrics"></section>

  <div class="toolbar">
    <input type="search" id="q" placeholder="Search decks by title, folder, or path…" autocomplete="off"/>
    <div class="seg" role="group" aria-label="Sort">
      <button type="button" data-sort="recent" aria-pressed="true">Recent</button>
      <button type="button" data-sort="title" aria-pressed="false">A–Z</button>
      <button type="button" data-sort="builds" aria-pressed="false">Most built</button>
    </div>
  </div>

  <div class="layout">
    <main id="main"></main>
    <aside class="side">
      <h3>Recent builds</h3>
      <ul class="activity" id="activity"></ul>
    </aside>
  </div>

  <p class="note">
    Index: <span id="lib-path-foot"></span>. Rebuild a deck with
    <code>python3 build.py deck.md</code> to add it. Import an existing folder with
    <code>python3 dashboard.py --import-dir ~/Decks</code>. LLM cost is not tracked locally.
  </p>
</div>
<script>
const state = { data: null, sort: "recent", q: "", selectedParent: null };

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => (
    ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" })[c]
  ));
}

function renderMetrics(m) {
  const items = [
    { label: "Decks", value: m.deck_count, hint: "unique HTML outputs" },
    { label: "Builds", value: m.build_count, hint: `${m.builds_7d} in last 7 days` },
    { label: "Avg slides", value: m.avg_slides, hint: `${m.slide_total} slides total` },
    { label: "30-day builds", value: m.builds_30d, hint: `${m.avg_builds_per_deck} builds / deck avg` },
  ];
  document.getElementById("metrics").innerHTML = items.map(it => `
    <div class="metric">
      <div class="label">${esc(it.label)}</div>
      <div class="value">${esc(it.value)}</div>
      <div class="hint">${esc(it.hint)}</div>
    </div>`).join("");
}

function allDecks(data) {
  const out = [];
  for (const g of data.groups) {
    for (const d of g.decks) out.push({ ...d, parent: g.parent, parent_display: g.parent_display, folder: g.folder });
  }
  return out;
}

function matches(d, q) {
  if (!q) return true;
  const hay = [d.title, d.subtitle, d.folder, d.parent_display, d.html_display, d.classification]
    .join(" ").toLowerCase();
  return hay.includes(q);
}

function sortDecks(decks, sort) {
  const arr = decks.slice();
  if (sort === "title") arr.sort((a,b) => a.title.localeCompare(b.title));
  else if (sort === "builds") arr.sort((a,b) => (b.build_count||0) - (a.build_count||0) || (b.updated_at||"").localeCompare(a.updated_at||""));
  else arr.sort((a,b) => (b.updated_at||"").localeCompare(a.updated_at||""));
  return arr;
}

function folderMatches(g, q) {
  if (!q) return true;
  const folderText = [g.folder, g.parent_display].join(" ").toLowerCase();
  return folderText.includes(q) || g.decks.some(d => matches({
    ...d, folder: g.folder, parent_display: g.parent_display,
  }, q));
}

function folderSummary(g) {
  const decks = g.decks || [];
  return {
    deckCount: decks.length,
    slides: decks.reduce((n, d) => n + Number(d.slide_count || 0), 0),
    builds: decks.reduce((n, d) => n + Number(d.build_count || 0), 0),
    updated: decks.reduce((latest, d) =>
      (d.updated_at || "") > latest ? (d.updated_at || "") : latest, ""),
    preview: decks.slice(0, 3).map(d => d.title).join(" · "),
  };
}

function sortedFolders(groups) {
  const arr = groups.slice();
  if (state.sort === "title") {
    arr.sort((a, b) => (a.folder || "").localeCompare(b.folder || ""));
  } else if (state.sort === "builds") {
    arr.sort((a, b) => folderSummary(b).builds - folderSummary(a).builds);
  } else {
    arr.sort((a, b) => folderSummary(b).updated.localeCompare(folderSummary(a).updated));
  }
  return arr;
}

function renderFolders(data, main) {
  const groups = sortedFolders(data.groups.filter(g => folderMatches(g, state.q)));
  if (!groups.length) {
    main.innerHTML = `<div class="empty"><h2>No matching folders</h2><p>Try a different search.</p></div>`;
    return;
  }
  main.innerHTML = `
    <div class="view-head">
      <h2>Folders</h2>
      <span class="count">${groups.length} folder${groups.length === 1 ? "" : "s"}</span>
    </div>
    <div class="folder-grid">
      ${groups.map(g => {
        const s = folderSummary(g);
        const index = data.groups.indexOf(g);
        return `
          <button class="folder-tile" type="button" data-folder-index="${index}">
            <div class="folder-icon" aria-hidden="true"></div>
            <div class="folder-name">${esc(g.folder || "Decks")}</div>
            <div class="folder-path-small">${esc(g.parent_display || g.parent)}</div>
            <div class="folder-stats">
              <span>${s.deckCount} deck${s.deckCount === 1 ? "" : "s"}</span>
              <span>${s.slides} slides</span>
              <span>${s.builds} builds</span>
            </div>
            ${s.preview ? `<div class="folder-preview">${esc(s.preview)}</div>` : ""}
          </button>`;
      }).join("")}
    </div>`;
}

function renderFolder(data, main) {
  const group = data.groups.find(g => g.parent === state.selectedParent);
  if (!group) {
    state.selectedParent = null;
    renderFolders(data, main);
    return;
  }
  const decks = sortDecks(group.decks.filter(d => matches({
    ...d, folder: group.folder, parent_display: group.parent_display,
  }, state.q)), state.sort);
  main.innerHTML = `
    <div class="view-head">
      <div>
        <button class="back" type="button" id="back-folders">← All folders</button>
      </div>
      <span class="count">${decks.length} deck${decks.length === 1 ? "" : "s"}</span>
    </div>
    <h2 style="font-size:22px;margin-bottom:12px">${esc(group.folder || "Decks")}</h2>
    <div class="folder-path">${esc(group.parent_display || group.parent)}</div>
    ${decks.length ? `
      <div class="deck-list">
        ${decks.map(d => `
          <a class="deck" href="${esc(d.open_url)}" target="_blank" rel="noopener">
            <div>
              <div class="title">${esc(d.title)}</div>
              ${d.subtitle ? `<div class="sub">${esc(d.subtitle)}</div>` : ""}
              <div class="path">${esc(d.html_display)}</div>
            </div>
            <div class="right">
              <span class="pill">Open →</span>
              <div class="stats-row">${esc(d.slide_count)} slides · ${esc(d.build_count)} builds · ${esc(d.updated_display)}</div>
            </div>
          </a>`).join("")}
      </div>` :
      `<div class="empty"><h2>No matching decks</h2><p>Try a different search.</p></div>`}`;
}

function renderMain(data) {
  const main = document.getElementById("main");
  if (!data.groups.length) {
    main.innerHTML = `
      <div class="empty">
        <h2>No decks indexed yet</h2>
        <p>Build a deck to start your local library, or import an existing folder.</p>
        <code>python3 dashboard.py --import-dir ~/Decks</code>
      </div>`;
    return;
  }
  if (state.selectedParent) renderFolder(data, main);
  else renderFolders(data, main);
}

function renderActivity(data) {
  const el = document.getElementById("activity");
  if (!data.recent_builds.length) {
    el.innerHTML = `<li><span class="dot"></span><div><div class="t">No builds yet</div></div></li>`;
    return;
  }
  el.innerHTML = data.recent_builds.map(b => `
    <li>
      <span class="dot"></span>
      <div>
        <div class="t">${esc(b.title)}</div>
        <div class="m">${esc(b.at_display)} · ${esc(b.slides)} slides</div>
      </div>
    </li>`).join("");
}

async function boot() {
  const res = await fetch("/api/library");
  const data = await res.json();
  state.data = data;
  document.getElementById("lib-path").textContent = data.library_path_display || data.library_path;
  document.getElementById("lib-path-foot").textContent = data.library_path_display || data.library_path;
  renderMetrics(data.metrics);
  renderMain(data);
  renderActivity(data);
}

document.getElementById("q").addEventListener("input", e => {
  state.q = e.target.value.trim().toLowerCase();
  if (state.data) renderMain(state.data);
});
document.getElementById("main").addEventListener("click", e => {
  const tile = e.target.closest("[data-folder-index]");
  if (tile && state.data) {
    const group = state.data.groups[Number(tile.dataset.folderIndex)];
    if (group) {
      state.selectedParent = group.parent;
      state.q = "";
      document.getElementById("q").value = "";
      document.getElementById("q").placeholder = `Search decks in ${group.folder}…`;
      renderMain(state.data);
      window.scrollTo({ top: 260, behavior: "smooth" });
    }
    return;
  }
  if (e.target.closest("#back-folders")) {
    state.selectedParent = null;
    state.q = "";
    document.getElementById("q").value = "";
    document.getElementById("q").placeholder = "Search folders or decks…";
    renderMain(state.data);
  }
});
document.querySelectorAll(".seg button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".seg button").forEach(b => b.setAttribute("aria-pressed", "false"));
    btn.setAttribute("aria-pressed", "true");
    state.sort = btn.dataset.sort;
    if (state.data) renderMain(state.data);
  });
});
boot();
</script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "DeckCraftDashboard/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def _send(self, code, body, content_type="text/html; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj), "application/json; charset=utf-8")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path in ("/", "/index.html"):
            self._send(200, DASHBOARD_HTML)
            return

        if path == "/api/ping":
            self._json(200, {"app": APP_ID, "schema": 1, "build": build_signature()})
            return

        if path == "/api/library":
            self._json(200, library_payload())
            return

        if path.startswith("/open/"):
            did = path[len("/open/"):].strip("/")
            lib = load_library()
            entry = lib["decks"].get(did)
            if not entry:
                self._send(404, "Deck not found or file missing.\n",
                           "text/plain; charset=utf-8")
                return
            # Path-traversal guard: only ever serve a file that is exactly one
            # of the HTML outputs recorded in the trusted local index, and only
            # an .html/.htm file. The path handed to open() is validated against
            # this allowlist — it is never derived from the request URL.
            allowed = {os.path.realpath(d["html"])
                       for d in lib["decks"].values() if d.get("html")}
            html_path = os.path.realpath(entry.get("html", ""))
            if (html_path not in allowed
                    or not html_path.lower().endswith((".html", ".htm"))
                    or not os.path.isfile(html_path)):
                self._send(404, "Deck not found or file missing.\n",
                           "text/plain; charset=utf-8")
                return
            # Stream the deck HTML; rewrite is unnecessary — decks are
            # self-contained (images base64-embedded).
            try:
                with open(html_path, "rb") as fh:
                    data = fh.read()
            except OSError as e:
                self._send(500, "Cannot read deck: %s\n" % e,
                           "text/plain; charset=utf-8")
                return
            ctype = mimetypes.guess_type(html_path)[0] or "text/html"
            self._send(200, data, ctype + "; charset=utf-8")
            return

        self._send(404, "Not found\n", "text/plain; charset=utf-8")


def build_signature():
    """Short hash of the served UI + server code.

    Lets a running background server be recognised as stale after an update,
    so `--launch` restarts it instead of reusing the old one.
    """
    digest = hashlib.sha256()
    digest.update(DASHBOARD_HTML.encode("utf-8"))
    for module in (__file__, os.path.join(SELF_DIR, "library.py")):
        try:
            with open(module, "rb") as fh:
                digest.update(fh.read())
        except OSError:
            pass
    return digest.hexdigest()[:12]


def pid_path(port):
    return os.path.join(os.path.dirname(library_path()), "dashboard-%d.pid" % port)


def _write_pid(port):
    try:
        os.makedirs(os.path.dirname(pid_path(port)) or ".", exist_ok=True)
        with open(pid_path(port), "w", encoding="utf-8") as fh:
            fh.write(str(os.getpid()))
    except OSError:
        pass


def _clear_pid(port):
    try:
        os.unlink(pid_path(port))
    except OSError:
        pass


def _read_pid(port):
    try:
        with open(pid_path(port), encoding="utf-8") as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None


def stop_server(port, timeout=5.0):
    """Terminate a background dashboard on this port. Returns True if stopped."""
    if not server_is_running(port):
        _clear_pid(port)
        return False
    pid = _read_pid(port)
    if pid is None:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        _clear_pid(port)
        return False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not server_is_running(port):
            _clear_pid(port)
            return True
        time.sleep(0.1)
    return False


def run_server(port, open_browser=True):
    # Bind loopback only — personal local data must not be exposed on LAN.
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    except OSError as e:
        print("Could not bind 127.0.0.1:%d: %s" % (port, e), file=sys.stderr)
        print("Try: python3 dashboard.py --port %d" % (port + 1), file=sys.stderr)
        return 1
    url = "http://127.0.0.1:%d/" % port
    print("Deck Craft library → %s" % url)
    print("Index file: %s" % library_path())
    print("Ctrl+C to stop.")
    _write_pid(port)
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
        _clear_pid(port)
    return 0


def dashboard_url(port):
    return "http://127.0.0.1:%d/" % port


def _tcp_open(port, timeout=0.35):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def server_ping(port, timeout=0.5):
    """Return the /api/ping payload from our dashboard, else None.

    Verifies an app-specific marker so an unrelated local service listening on
    the same port is never mistaken for the dashboard.
    """
    if not _tcp_open(port, timeout=min(timeout, 0.35)):
        return None
    try:
        with _LOOPBACK_OPENER.open(dashboard_url(port) + "api/ping",
                                   timeout=timeout) as response:
            if not 200 <= getattr(response, "status", 200) < 300:
                return None
            payload = json.loads(response.read(4096).decode("utf-8", "replace"))
    except (OSError, URLError, TimeoutError, ValueError):
        return None
    if isinstance(payload, dict) and payload.get("app") == APP_ID:
        return payload
    return None


def server_is_running(port, timeout=0.5):
    return server_ping(port, timeout=timeout) is not None


def server_is_current(port, timeout=0.5):
    """True when a running dashboard serves the same code we would serve."""
    payload = server_ping(port, timeout=timeout)
    return bool(payload) and payload.get("build") == build_signature()


def port_is_free(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def resolve_port(port, explicit):
    """Pick a usable port: reuse our own server, else the first free port.

    With an explicit --port we never shift, so the user keeps control.
    """
    if explicit:
        return port
    # Prefer a port already serving our dashboard so updates replace it.
    for candidate in range(port, port + PORT_SCAN_LIMIT):
        if server_is_running(candidate):
            return candidate
    for candidate in range(port, port + PORT_SCAN_LIMIT):
        if port_is_free(candidate):
            return candidate
    return port


def _tail_file(path, lines=40):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            content = fh.read().splitlines()
    except OSError:
        return ""
    return "\n".join(content[-lines:])


def launch_dashboard(port, open_browser=True, force_restart=False):
    """Start the dashboard in the background, or reuse the existing server.

    A server left running from an older version is restarted so `--launch`
    never silently serves stale UI after an update.
    """
    url = dashboard_url(port)
    if server_is_running(port):
        if not force_restart and server_is_current(port):
            print("Deck Craft library already running → %s" % url)
            if open_browser:
                webbrowser.open(url)
            return 0
        reason = "Restarting" if force_restart else "Restarting outdated server"
        print("%s on port %d…" % (reason, port))
        if not stop_server(port):
            print("Could not stop the server on port %d." % port, file=sys.stderr)
            print("Stop it manually, then relaunch:", file=sys.stderr)
            print("  python3 dashboard.py --stop --port %d" % port, file=sys.stderr)
            return 1

    if not port_is_free(port):
        print("Port %d is in use by another application." % port, file=sys.stderr)
        print("Try: python3 dashboard.py --launch --port %d" % (port + 1),
              file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(library_path()) or ".", exist_ok=True)
    log_path = os.path.join(os.path.dirname(library_path()), "dashboard.log")
    command = [
        sys.executable,
        os.path.abspath(__file__),
        "--port", str(port),
        "--no-open",
    ]
    with open(log_path, "a", encoding="utf-8") as log:
        log.write("\n--- launch %s ---\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
        log.flush()
        subprocess.Popen(
            command,
            cwd=SELF_DIR,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )

    deadline = time.monotonic() + 6.0
    while time.monotonic() < deadline:
        if server_is_running(port):
            print("Deck Craft library launched → %s" % url)
            if open_browser:
                webbrowser.open(url)
            return 0
        time.sleep(0.1)

    print("Dashboard did not start; see %s" % log_path, file=sys.stderr)
    tail = _tail_file(log_path)
    if tail:
        print("--- log tail ---", file=sys.stderr)
        print(tail, file=sys.stderr)
    print("Try opening %s in your browser," % url, file=sys.stderr)
    print("or run foreground: python3 dashboard.py --port %d" % port,
          file=sys.stderr)
    return 1


def _extract_meta(html_path, source_path):
    """Best-effort title/slide count from sibling Markdown source."""
    meta, slide_count = {}, 0
    if source_path and source_path.endswith(".md") and os.path.isfile(source_path):
        try:
            import build as build_mod
            with open(source_path, encoding="utf-8") as fh:
                meta, slides = build_mod.parse_deck(fh.read())
            slide_count = len(slides)
        except Exception:
            meta = {"title": os.path.splitext(os.path.basename(source_path))[0]}
    else:
        meta = {"title": os.path.splitext(os.path.basename(html_path))[0]}
        # Rough slide count + title from generated HTML
        try:
            import re
            with open(html_path, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            slide_count = text.count('class="slide')
            m = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
            if m:
                title = re.sub(r"\s+", " ", m.group(1)).strip()
                if title:
                    meta["title"] = title
        except OSError:
            pass
    return meta, slide_count


def cmd_register(html_path, source_path=None):
    meta, slide_count = _extract_meta(
        os.path.abspath(html_path),
        os.path.abspath(source_path) if source_path else None,
    )
    src = source_path
    if src is None:
        guess = os.path.splitext(os.path.abspath(html_path))[0] + ".md"
        if os.path.isfile(guess):
            src = guess
    did = register_existing(html_path, source_path=src, meta=meta,
                            slide_count=slide_count)
    print("Registered %s  (id %s)" % (os.path.abspath(html_path), did))
    return 0


def cmd_import_dir(root, recursive=True):
    expanded = os.path.abspath(os.path.expanduser(root))
    if not os.path.isdir(expanded):
        print("Not a folder: %s" % expanded, file=sys.stderr)
        print("Quote paths containing spaces, e.g.:", file=sys.stderr)
        print('  python3 dashboard.py --import-dir "~/Auggie Output/Decks"',
              file=sys.stderr)
        return 1
    result = import_directory(expanded, recursive=recursive,
                              extract_meta=_extract_meta)
    print("Imported from %s" % result["root"])
    print("  found:   %d Deck Craft HTML file(s)" % result["total_found"])
    print("  added:   %d" % len(result["added"]))
    print("  updated: %d" % len(result["updated"]))
    if result["total_found"] == 0:
        print("  (no files matched Deck Craft HTML — need #stage + .slide markup)")
        return 1
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", type=int, default=None,
                   help="Port to serve on (default: first free from %d)" % DEFAULT_PORT)
    p.add_argument("--no-open", action="store_true", help="Do not open a browser")
    p.add_argument("--launch", action="store_true",
                   help="Start/reuse a background server, open it, then exit")
    p.add_argument("--json", action="store_true", help="Print library JSON and exit")
    p.add_argument("--register", nargs="+", metavar="PATH",
                   help="Register an existing deck.html [deck.md] and exit")
    p.add_argument("--import-dir", metavar="DIR",
                   help="Scan a folder of existing decks into the local library")
    p.add_argument("--no-recursive", action="store_true",
                   help="With --import-dir, only scan the top-level folder")
    p.add_argument("--restart", action="store_true",
                   help="Force-restart the background server, then open it")
    p.add_argument("--stop", action="store_true",
                   help="Stop a background dashboard server and exit")
    args = p.parse_args(argv)

    if args.register:
        html = args.register[0]
        src = args.register[1] if len(args.register) > 1 else None
        return cmd_register(html, src)

    if args.import_dir:
        return cmd_import_dir(args.import_dir, recursive=not args.no_recursive)

    if args.json:
        print(json.dumps(library_payload(), indent=2))
        return 0

    port = resolve_port(args.port or DEFAULT_PORT, explicit=args.port is not None)

    if args.stop:
        # Prefer the resolved/explicit port, then scan nearby ports for leftovers.
        candidates = []
        for candidate in range(DEFAULT_PORT, DEFAULT_PORT + PORT_SCAN_LIMIT):
            if candidate not in candidates:
                candidates.append(candidate)
        if port not in candidates:
            candidates.insert(0, port)
        # Also check the original default used before we moved off 8765.
        for legacy in (8765, 8766, 8767, 8768, 8769, 8770):
            if legacy not in candidates:
                candidates.append(legacy)

        stopped = []
        for candidate in candidates:
            if stop_server(candidate):
                stopped.append(candidate)
        if stopped:
            print("Stopped Deck Craft library on port(s): %s"
                  % ", ".join(str(p) for p in stopped))
            return 0
        print("No Deck Craft library server found on ports %d–%d (or legacy 8765+)."
              % (DEFAULT_PORT, DEFAULT_PORT + PORT_SCAN_LIMIT - 1))
        print("Find leftovers with: lsof -nP -iTCP -sTCP:LISTEN | grep python")
        return 1

    if args.launch or args.restart:
        return launch_dashboard(port, open_browser=not args.no_open,
                                force_restart=args.restart)

    return run_server(port, open_browser=not args.no_open)


if __name__ == "__main__":
    sys.exit(main())
