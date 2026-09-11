#!/usr/bin/env python3
"""
Local Deck Craft library index — no network, no phone-home.

Stores build history under ~/.deck-craft/library.json so the dashboard can show
personal metrics and link to every deck you've built on this machine.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone

# Prefer library_dir() / library_path() — these defaults exist for importers
# that still read module attributes.
LIBRARY_DIR = os.path.expanduser("~/.deck-craft")
LIBRARY_PATH = os.path.join(LIBRARY_DIR, "library.json")
SCHEMA_VERSION = 1
MAX_BUILDS = 500  # rolling activity log


def library_dir():
    return os.path.expanduser(os.environ.get("DECK_CRAFT_HOME", "~/.deck-craft"))


def library_path():
    return os.path.join(library_dir(), "library.json")


def _now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def deck_id_for(html_path):
    """Stable id from absolute HTML path."""
    abs_html = os.path.abspath(html_path)
    return hashlib.sha256(abs_html.encode("utf-8")).hexdigest()[:16]


def empty_library():
    return {
        "version": SCHEMA_VERSION,
        "decks": {},
        "builds": [],
        "import_roots": [],
    }


def load_library(path=None):
    path = path or library_path()
    if not os.path.isfile(path):
        return empty_library()
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, json.JSONDecodeError):
        return empty_library()
    if not isinstance(data, dict):
        return empty_library()
    data.setdefault("version", SCHEMA_VERSION)
    data.setdefault("decks", {})
    data.setdefault("builds", [])
    data.setdefault("import_roots", [])
    if not isinstance(data["decks"], dict):
        data["decks"] = {}
    if not isinstance(data["builds"], list):
        data["builds"] = []
    if not isinstance(data["import_roots"], list):
        data["import_roots"] = []
    return data


def save_library(data, path=None):
    path = path or library_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".library-", suffix=".json",
                               dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def record_build(source_path, html_path, meta=None, slide_count=0,
                 path=None, at=None, count_build=True):
    """
    Upsert a deck entry and optionally append a build event.
    meta: dict with optional title, classification, subtitle.
    count_build=False updates metadata without inflating build_count (imports).
    Returns the deck id.
    """
    meta = meta or {}
    html_path = os.path.abspath(html_path)
    source_path = os.path.abspath(source_path)
    did = deck_id_for(html_path)
    lib = load_library(path)
    now = at or _now_iso()
    title = (meta.get("title") or os.path.splitext(os.path.basename(source_path))[0]
             or "Untitled")
    folder = os.path.basename(os.path.dirname(html_path)) or os.path.dirname(html_path)
    parent = os.path.dirname(html_path)

    existing = lib["decks"].get(did)
    if existing:
        created = existing.get("created_at", now)
        build_count = int(existing.get("build_count", 0))
        if count_build:
            build_count += 1
    else:
        created = now
        build_count = 1 if count_build else 0

    lib["decks"][did] = {
        "id": did,
        "title": title,
        "subtitle": meta.get("subtitle") or "",
        "classification": meta.get("classification") or "",
        "source": source_path,
        "html": html_path,
        "folder": folder,
        "parent": parent,
        "slide_count": int(slide_count),
        "created_at": created,
        "updated_at": now,
        "build_count": build_count,
    }
    if count_build:
        lib["builds"].append({
            "deck_id": did,
            "at": now,
            "slides": int(slide_count),
            "title": title,
        })
        if len(lib["builds"]) > MAX_BUILDS:
            lib["builds"] = lib["builds"][-MAX_BUILDS:]
    save_library(lib, path)
    return did


def register_existing(html_path, source_path=None, meta=None, slide_count=0,
                      path=None, count_build=None):
    """Add an already-built HTML deck.

    First registration counts as one build; re-registering the same path only
    refreshes metadata unless count_build=True is forced.
    """
    html_path = os.path.abspath(html_path)
    if not os.path.isfile(html_path):
        raise FileNotFoundError(html_path)
    if source_path is None:
        guess = os.path.splitext(html_path)[0] + ".md"
        source_path = guess if os.path.isfile(guess) else html_path
    lib = load_library(path)
    did = deck_id_for(html_path)
    if count_build is None:
        count_build = did not in lib["decks"]
    return record_build(source_path, html_path, meta=meta,
                        slide_count=slide_count, path=path,
                        count_build=count_build)


def looks_like_deck_craft_html(html_path):
    """Heuristic: Deck Craft HTML embeds a #stage canvas and .slide shells."""
    try:
        with open(html_path, encoding="utf-8", errors="ignore") as fh:
            head = fh.read(12000)
    except OSError:
        return False
    return "#stage" in head and 'class="slide' in head


def find_deck_htmls(root, recursive=True):
    """Yield absolute paths to Deck Craft HTML files under root."""
    root = os.path.abspath(os.path.expanduser(root))
    if not os.path.isdir(root):
        raise NotADirectoryError(root)
    if recursive:
        walker = os.walk(root)
    else:
        walker = [(root, [], os.listdir(root))]
    for dirpath, _dirnames, filenames in walker:
        for name in filenames:
            if not name.lower().endswith(".html"):
                continue
            # Skip our own dashboard artifacts if ever dropped in-tree
            if name.lower() in ("dashboard.html", "index.html") and not looks_like_deck_craft_html(
                    os.path.join(dirpath, name)):
                continue
            path = os.path.join(dirpath, name)
            if looks_like_deck_craft_html(path):
                yield path


def remember_import_root(root, path=None):
    root = os.path.abspath(os.path.expanduser(root))
    lib = load_library(path)
    if root not in lib["import_roots"]:
        lib["import_roots"].append(root)
        save_library(lib, path)
    return lib["import_roots"]


def import_directory(root, recursive=True, path=None, extract_meta=None):
    """
    Scan a folder of existing decks and upsert them into the local library.

    extract_meta: optional callable(html_path, source_path) -> (meta, slide_count)
    Returns dict with added/updated/skipped counts and deck ids.
    """
    root = os.path.abspath(os.path.expanduser(root))
    remember_import_root(root, path=path)
    added, updated, skipped = [], [], []
    lib_before = load_library(path)
    known = set(lib_before["decks"])

    for html in find_deck_htmls(root, recursive=recursive):
        did = deck_id_for(html)
        guess = os.path.splitext(html)[0] + ".md"
        source = guess if os.path.isfile(guess) else html
        meta, slide_count = {}, 0
        if extract_meta:
            try:
                meta, slide_count = extract_meta(html, source)
            except Exception:
                meta, slide_count = {}, 0
        elif source.endswith(".md") and os.path.isfile(source):
            # Title fallback from filename when parser not provided
            meta = {"title": os.path.splitext(os.path.basename(source))[0]}
        else:
            meta = {"title": os.path.splitext(os.path.basename(html))[0]}

        # Importing only indexes existing paths — it must not inflate usage
        # metrics, so never record a synthetic build event for discovered decks.
        register_existing(html, source_path=source, meta=meta,
                          slide_count=slide_count, path=path,
                          count_build=False)
        if did in known:
            updated.append(did)
        else:
            added.append(did)
            known.add(did)

    return {
        "root": root,
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "total_found": len(added) + len(updated),
    }


def prune_missing(lib=None, path=None):
    """Drop deck entries whose HTML file no longer exists. Returns (lib, removed)."""
    path = path or library_path()
    lib = lib if lib is not None else load_library(path)
    removed = []
    keep = {}
    for did, entry in lib["decks"].items():
        html = entry.get("html", "")
        if html and os.path.isfile(html):
            keep[did] = entry
        else:
            removed.append(did)
    if removed:
        lib["decks"] = keep
        alive = set(keep)
        lib["builds"] = [b for b in lib["builds"] if b.get("deck_id") in alive]
        save_library(lib, path)
    return lib, removed


def metrics(lib=None, path=None):
    """Aggregate personal usage metrics from the local library."""
    path = path or library_path()
    lib = lib if lib is not None else load_library(path)
    decks = list(lib["decks"].values())
    builds = lib["builds"]
    total_decks = len(decks)
    total_builds = sum(int(d.get("build_count", 0)) for d in decks)
    total_slides = sum(int(d.get("slide_count", 0)) for d in decks)
    avg_slides = (total_slides / total_decks) if total_decks else 0.0
    avg_builds = (total_builds / total_decks) if total_decks else 0.0

    now = time.time()

    def _parse_ts(iso):
        if not iso:
            return None
        try:
            s = iso.replace("Z", "+00:00")
            return datetime.fromisoformat(s).timestamp()
        except ValueError:
            return None

    def _count_since(days):
        cutoff = now - days * 86400
        n = 0
        for b in builds:
            ts = _parse_ts(b.get("at"))
            if ts is not None and ts >= cutoff:
                n += 1
        return n

    folders = {}
    for d in decks:
        key = d.get("folder") or "Other"
        folders[key] = folders.get(key, 0) + 1

    return {
        "deck_count": total_decks,
        "build_count": total_builds,
        "slide_total": total_slides,
        "avg_slides": round(avg_slides, 1),
        "avg_builds_per_deck": round(avg_builds, 1),
        "builds_7d": _count_since(7),
        "builds_30d": _count_since(30),
        "folders": folders,
        "library_path": path,
    }


def decks_grouped(lib=None, path=None):
    """Return decks grouped by parent folder path, newest first within group."""
    lib = lib if lib is not None else load_library(path)
    groups = {}
    for entry in lib["decks"].values():
        parent = entry.get("parent") or "Unknown"
        groups.setdefault(parent, []).append(entry)
    for parent in groups:
        groups[parent].sort(key=lambda d: d.get("updated_at") or "", reverse=True)
    ordered = sorted(
        groups.items(),
        key=lambda kv: max((d.get("updated_at") or "") for d in kv[1]),
        reverse=True,
    )
    return ordered
