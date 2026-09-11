#!/usr/bin/env python3
"""
Deck Craft builder — turns a Markdown source file into a single, self-contained,
themeable HTML presentation (31 slide types, several built-in visual themes).

Usage:
    python3 build.py deck.md            # writes deck.html next to deck.md
    python3 build.py deck.md out.html   # explicit output path
    python3 build.py deck.md --watch    # auto-rebuild on save (Ctrl+C to stop)
    python3 build.py deck.md --no-pptx  # omit the in-HTML "Save as PowerPoint" button
    python3 build.py deck.md --no-pdf   # omit the in-HTML "Save as PDF" button
    python3 build.py deck.md --no-index # skip writing to the local library index

Standard library only. Images referenced by filename are looked up in an
`assets/` folder next to the deck and base64-embedded so the output is portable.
Fixed 1280x720 canvas, scaled to fit the viewport. Arrow keys / buttons navigate.
Each successful build is recorded in ~/.deck-craft/library.json (local only; no
network) so `dashboard.py` can show personal metrics and link to your decks.
"""
import sys, os, re, base64, html, mimetypes, time
from datetime import date, timedelta
from urllib.parse import urlparse

try:
    from library import record_build
except ImportError:
    # Allow running as `python3 path/to/build.py` from another cwd when the
    # skill folder is not on sys.path.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from library import record_build

CANVAS_W, CANVAS_H = 1280, 720
DEFAULT_CLASS = "Private & Confidential"

# Feature flags: embed in-browser "Save as PowerPoint" / "Save as PDF" buttons
# (one image per slide) into the generated HTML. Set either False (or pass
# --no-pptx / --no-pdf) to disable and slim down the output. The .pptx/.pdf are
# built client-side using the bundled MIT libraries in lib/ (html-to-image plus
# pptxgen and/or jsPDF, see lib/THIRD_PARTY_NOTICES.md); build.py itself stays
# pure standard library.
PPTX_EXPORT = True
PDF_EXPORT = True

SELF_DIR = os.path.dirname(os.path.abspath(__file__))

# ---- themes -----------------------------------------------------------
# A theme is a bundle of design tokens (colors, fonts, chrome). Pick one with
# `theme:` in front matter; `accent:` / `font:` in front matter override just
# those two tokens on top of whichever theme is chosen. See resolve_theme().
#
# `font` is the functional/body face (body copy, labels, numbers, chrome);
# `font_display` is used only for slide headlines (cover/section titles,
# `head()`'s title, statement, quote, closing) — see FONT_DISPLAY_FONT below.
# `hot` is the "highlighted item" color used by grid-2x2's `*`-prefixed cell
# and bar-chart's `*`-prefixed bar; it defaults to `accent` and only differs
# where a theme calls for a second, distinct highlight color.
DEFAULT_THEME = "modern"

THEMES = {
    # One accent blue on greyscale, dark throughout. Left-aligned, no rules, no shadows.
    "modern": {
        "ink": "#f2f3f5", "ink_soft": "#c7c9d1", "muted": "#8a8f99", "line": "rgba(255,255,255,.12)",
        "bg": "#101114", "accent": "#7b90ff", "hot": "var(--accent)",
        "font": '"Archivo","Helvetica Neue",Arial,sans-serif',
        "font_display": '"Archivo","Helvetica Neue",Arial,sans-serif',
        "dark_bg": "radial-gradient(circle farthest-corner at 100% 0%,#1b1d22 0%,#0a0a0c 60%,#000000 100%)",
        "head_bg": "#000000",
        "topbar_bg": "none", "topbar_h": "0px",
        "panel_grad": "linear-gradient(180deg,#17181c,#101114)", "panel_flat": "#17181c",
        "accent_soft": "linear-gradient(180deg,#1c2440,#141a30)", "row_alt": "#17181c",
        "radius": "4px", "shadow": "none",
    },
    # Serif headings, navy authority, thin gold rule under every title.
    "professional": {
        "ink": "#14284b", "ink_soft": "#2e4568", "muted": "#4a5d78", "line": "#d7dee8",
        "bg": "#edf1f6", "accent": "#7e6122", "hot": "var(--accent)",
        "font": '"Libre Franklin","Helvetica Neue",Arial,sans-serif',
        "font_display": '"Spectral",Georgia,"Times New Roman",serif',
        "dark_bg": "radial-gradient(circle farthest-corner at 100% 0%,#1c3862 0%,#14284b 55%,#0b1930 100%)",
        "head_bg": "#0b1930",
        "topbar_bg": "var(--accent)", "topbar_h": "3px",
        "panel_grad": "linear-gradient(180deg,#ffffff,#edf1f6)", "panel_flat": "#e3e9f2",
        "accent_soft": "linear-gradient(180deg,#f7f1e2,#efe6d0)", "row_alt": "#e3e9f2",
        "radius": "6px", "shadow": "0 20px 50px rgba(20,40,75,.12)",
    },
    # Dark surface that lifts with a lighter fill, never a shadow. Teal accent.
    "dark": {
        "ink": "#e8e9ec", "ink_soft": "#c5c8ce", "muted": "#7a8089", "line": "rgba(255,255,255,.10)",
        "bg": "#0c0d10", "accent": "#38e1c0", "hot": "var(--accent)",
        "font": '"Sora","Helvetica Neue",Arial,sans-serif',
        "font_display": '"Sora","Helvetica Neue",Arial,sans-serif',
        "dark_bg": "radial-gradient(circle farthest-corner at 100% 0%,#1b1e24 0%,#0c0d10 60%,#000000 100%)",
        "head_bg": "#060708",
        "topbar_bg": "var(--accent)", "topbar_h": "3px",
        "panel_grad": "linear-gradient(180deg,#1b1d23,#16181d)", "panel_flat": "#16181d",
        "accent_soft": "linear-gradient(180deg,#173330,#122824)", "row_alt": "#16181d",
        "radius": "12px", "shadow": "none",
    },
    # No colour at all. One idea per slide, huge margins, light weights only.
    "light": {
        "ink": "#111111", "ink_soft": "#444444", "muted": "#767676", "line": "#e6e6e6",
        "bg": "#ffffff", "accent": "#767676", "hot": "var(--accent)",
        "font": '"Libre Franklin","Helvetica Neue",Arial,sans-serif',
        "font_display": '"Libre Franklin","Helvetica Neue",Arial,sans-serif',
        "dark_bg": "#111111",
        "head_bg": "#111111",
        "topbar_bg": "none", "topbar_h": "0px",
        "panel_grad": "#fafafa", "panel_flat": "#f2f2f2",
        "accent_soft": "#ededed", "row_alt": "#f7f7f7",
        "radius": "2px", "shadow": "0 12px 32px rgba(0,0,0,.08)",
    },
    # Magazine logic: pull quotes, italic captions, titles that can run three lines.
    "editorial": {
        "ink": "#1b1a17", "ink_soft": "#3a362e", "muted": "#8a8070", "line": "#e4dac5",
        "bg": "#faf6ee", "accent": "#b3261e", "hot": "var(--accent)",
        "font": '"Spectral",Georgia,serif',
        "font_display": '"Instrument Serif",Georgia,serif',
        "dark_bg": "linear-gradient(160deg,#2e2a22 0%,#1b1a17 100%)",
        "head_bg": "#1b1a17",
        "topbar_bg": "var(--accent)", "topbar_h": "3px",
        "panel_grad": "linear-gradient(180deg,#fffdf7,#f5efe0)", "panel_flat": "#f2eada",
        "accent_soft": "linear-gradient(180deg,#f8e0dc,#f0cac4)", "row_alt": "#f4eee0",
        "radius": "10px", "shadow": "0 20px 50px rgba(27,26,23,.15)",
    },
    # Charts are the slide. Mono labels, amber reserved for the outlier.
    "technical": {
        "ink": "#0f1b1f", "ink_soft": "#2a3b3f", "muted": "#6d7a7d", "line": "#dce2e2",
        "bg": "#f7f8f8", "accent": "#0e6e6e", "hot": "#d98a0b",
        "font": '"Libre Franklin","Helvetica Neue",Arial,sans-serif',
        "font_display": '"IBM Plex Mono","SFMono-Regular",Consolas,monospace',
        "dark_bg": "radial-gradient(circle farthest-corner at 100% 0%,#173a3a 0%,#0c1f1f 55%,#020a0a 100%)",
        "head_bg": "#0c1f1f",
        "topbar_bg": "var(--accent)", "topbar_h": "3px",
        "panel_grad": "linear-gradient(180deg,#ffffff,#eff3f3)", "panel_flat": "#ebf0f0",
        "accent_soft": "linear-gradient(180deg,#dff2f0,#c9e8e4)", "row_alt": "#eef2f2",
        "radius": "6px", "shadow": "0 16px 40px rgba(15,27,31,.12)",
    },
    # Type fills the frame edge to edge. Six words maximum. One colour flip.
    "bold": {
        "ink": "#ffffff", "ink_soft": "#d8d8d8", "muted": "#8c8c8c", "line": "rgba(255,255,255,.18)",
        "bg": "#000000", "accent": "#f2ff49", "hot": "#ff3d2e",
        "font": '"Archivo","Helvetica Neue",Arial,sans-serif',
        "font_display": '"Archivo","Helvetica Neue",Arial,sans-serif',
        "dark_bg": "#000000",
        "head_bg": "#000000",
        "topbar_bg": "none", "topbar_h": "0px",
        "panel_grad": "linear-gradient(180deg,#141414,#000000)", "panel_flat": "#0d0d0d",
        "accent_soft": "linear-gradient(180deg,#3a3600,#262300)", "row_alt": "#0d0d0d",
        "radius": "0px", "shadow": "none",
    },
    # Rounded corners, photography over flat colour, hand-set captions.
    "warm": {
        "ink": "#4a3728", "ink_soft": "#6b5240", "muted": "#8a7c6c", "line": "#e3d6c4",
        "bg": "#f3e9dc", "accent": "#9b3f23", "hot": "var(--accent)",
        "font": '"Sora","Helvetica Neue",Arial,sans-serif',
        "font_display": '"Lora",Georgia,serif',
        "dark_bg": "linear-gradient(160deg,#4a3728 0%,#2e2015 100%)",
        "head_bg": "#2e2015",
        "topbar_bg": "var(--accent)", "topbar_h": "4px",
        "panel_grad": "linear-gradient(180deg,#faf4ec,#f0e3d2)", "panel_flat": "#eddfc9",
        "accent_soft": "linear-gradient(180deg,#f3ded2,#ecccb8)", "row_alt": "#efe1cc",
        "radius": "18px", "shadow": "0 20px 50px rgba(74,55,40,.18)",
    },
}

# Renamed-theme aliases: the old id keeps working (mapped to its closest new
# theme) but prints a warning pointing at the new name, so an existing deck
# never silently breaks.
THEME_ALIASES = {
    "corporate": "modern",
    "minimal-mono": "light",
    "dark-tech": "dark",
    "warm-editorial": "warm",
}

def resolve_theme(meta):
    """Merge the named theme's tokens with any accent:/font: override from
    front matter. Resolves a renamed alias (with a warning) and falls back to
    DEFAULT_THEME (with a warning) on an unknown theme name."""
    name = (meta.get("theme") or DEFAULT_THEME).strip().lower()
    if name in THEME_ALIASES:
        new_name = THEME_ALIASES[name]
        WARNINGS.append("theme '%s' has been renamed to '%s' -> using '%s' "
                        "(update your deck.md)" % (name, new_name, new_name))
        name = new_name
    base = THEMES.get(name)
    if base is None:
        WARNINGS.append("unknown theme '%s' -> %s (options: %s)"
                        % (name, DEFAULT_THEME, ", ".join(sorted(THEMES))))
        base = THEMES[DEFAULT_THEME]
    tokens = dict(base)
    if meta.get("accent"):
        tokens["accent"] = meta["accent"]
    if meta.get("font"):
        tokens["font"] = meta["font"]
    return tokens

# ---- design tokens ----------------------------------------------------
ROOT_CSS = """
:root{
  --ink:%INK%; --ink-soft:%INK_SOFT%; --muted:%MUTED%; --line:%LINE%;
  --bg:%BG%; --accent:%ACCENT%; --hot:%HOT%;
  --radius:%RADIUS%; --shadow:%SHADOW%;
  --dark-bg:%DARK_BG%; --head-bg:%HEAD_BG%;
  --topbar-bg:%TOPBAR_BG%; --topbar-h:%TOPBAR_H%;
  --panel-grad:%PANEL_GRAD%; --panel-flat:%PANEL_FLAT%; --accent-soft:%ACCENT_SOFT%;
  --row-alt:%ROW_ALT%;
  --font:%FONT%; --font-display:%FONT_DISPLAY%;
  --type-title:64px; --type-h2:48px; --type-h3:38px; --type-subtitle:28px;
  --type-body:24px; --type-small:24px; --type-label:24px; --type-footer:24px;
  --pad-x:64px; --pad-top:48px; --pad-bot:48px; --gap-title:40px; --gap-item:20px;
  --row-pad:20px;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{background:#0c0d10;font-family:var(--font);overflow:hidden;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}
#stage{position:absolute;top:50%;left:50%;width:1280px;height:720px;
  transform-origin:center center;}
.slide{position:absolute;inset:0;width:1280px;height:720px;border-radius:var(--radius);
  overflow:hidden;box-shadow:var(--shadow);display:flex;flex-direction:column;
  opacity:0;pointer-events:none;z-index:0;}
/* fade (default): layered crossfade, outgoing held opaque so no bg bleed-through */
.fx-fade .slide.prev{opacity:1;z-index:0;}
.fx-fade .slide.on{opacity:1;pointer-events:auto;z-index:1;
  transition:opacity .28s ease;will-change:opacity;}
/* swipe: horizontal slide; JS sets inline transforms so it's direction-aware */
.fx-swipe{overflow:hidden;}
.fx-swipe .slide{opacity:1;transform:translateX(100%);
  transition:transform .4s cubic-bezier(.4,0,.2,1);will-change:transform;}
.fx-swipe .slide.on{transform:translateX(0);pointer-events:auto;z-index:1;}
@media (prefers-reduced-motion:reduce){
  .fx-fade .slide.on{transition:none;}
  .fx-swipe .slide{transition:none;}}
.missing{outline:2px dashed #ff2d2d;outline-offset:-2px;}
.nav{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);display:flex;
  align-items:center;gap:14px;z-index:10;}
.nav button{border:none;cursor:pointer;width:46px;height:46px;border-radius:50%;
  background:rgba(255,255,255,.1);color:#fff;font-size:22px;display:grid;
  place-items:center;backdrop-filter:blur(6px);transition:background .15s,transform .15s;}
.nav button:hover:not(:disabled){background:var(--accent);transform:translateY(-2px);}
.nav button:disabled{opacity:.3;cursor:default;}
.nav .pg{color:rgba(255,255,255,.7);font-size:13px;letter-spacing:.1em;min-width:64px;
  text-align:center;font-family:var(--font);}
.nav .pptx{width:auto;border-radius:23px;padding:0 18px;gap:8px;font-size:13px;
  font-weight:700;letter-spacing:.06em;font-family:var(--font);}
.nav .pptx[disabled]{opacity:.6;}
#swim-tip{position:fixed;top:0;left:0;z-index:20;max-width:360px;pointer-events:none;
  background:var(--head-bg);color:#fff;font-family:var(--font);font-size:15px;font-weight:600;
  line-height:1.4;padding:11px 15px;border-radius:12px;
  box-shadow:0 16px 40px rgba(10,12,25,.45);opacity:0;transform:translateY(4px);
  transition:opacity .12s ease,transform .12s ease;}
#swim-tip.on{opacity:1;transform:translateY(0);}
#swim-tip::after{content:"";position:absolute;top:100%;left:var(--tip-ax,50%);
  transform:translateX(-50%);border:7px solid transparent;border-top-color:var(--head-bg);}
#swim-tip.below::after{top:auto;bottom:100%;border-top-color:transparent;
  border-bottom-color:var(--head-bg);}
""".strip()

# ---- HTML shell -----------------------------------------------------------
PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>%TITLE%</title>
<style>%CSS%</style>
</head><body>
<div id="stage" class="%MODE%">
%SLIDES%
</div>
<div class="nav">
  <button id="prev" aria-label="Previous">&#8249;</button>
  <span class="pg" id="pg"></span>
  <button id="next" aria-label="Next">&#8250;</button>
%PPTX_BTN%%PDF_BTN%</div>
%LIBS%<script>%JS%</script>
%EXPORT%</body></html>"""

PPTX_BTN = ('  <button id="pptx" class="pptx" aria-label="Save as PowerPoint" '
            'title="Save as PowerPoint (one image per slide)">'
            '&#8595; PowerPoint</button>\n')

PDF_BTN = ('  <button id="pdf" class="pptx" aria-label="Save as PDF" '
           'title="Save as PDF (one page per slide)">'
           '&#8595; PDF</button>\n')

NAV_JS = """
(function(){
  var stage=document.getElementById('stage');
  var slides=[].slice.call(document.querySelectorAll('.slide'));
  var pg=document.getElementById('pg'), prev=document.getElementById('prev'),
      next=document.getElementById('next'), i=0;
  var swipe=stage.className.indexOf('fx-swipe')>=0;
  // Hover tooltips for swimlane phase bars whose label is clipped: reveal the
  // full text in a small tooltip, but only when it doesn't fit.
  var tip=document.createElement('div'); tip.id='swim-tip';
  document.body.appendChild(tip);
  function hideTip(){tip.classList.remove('on');}
  function showTip(el){
    var t=el.getAttribute('data-tip'); if(!t){return;}
    // The label may live in an inner <span> that owns the truncation, so probe
    // the span's overflow when present; otherwise fall back to the element.
    var m=el.querySelector('span')||el;
    if(m.scrollWidth<=m.clientWidth+1){hideTip();return;}
    tip.textContent=t;
    var r=el.getBoundingClientRect(), tw=tip.offsetWidth, th=tip.offsetHeight;
    var cx=r.left+r.width/2;
    var left=Math.max(8,Math.min(window.innerWidth-tw-8,cx-tw/2));
    var below=false, top=r.top-th-12;
    if(top<8){below=true; top=r.bottom+12;}
    tip.style.left=left+'px'; tip.style.top=top+'px';
    tip.style.setProperty('--tip-ax',(cx-left)+'px');
    tip.classList.toggle('below',below);
    tip.classList.add('on');
  }
  stage.addEventListener('mouseover',function(e){
    var el=e.target&&e.target.closest?e.target.closest('[data-tip]'):null;
    if(el){showTip(el);}
  });
  stage.addEventListener('mouseout',function(e){
    var el=e.target&&e.target.closest?e.target.closest('[data-tip]'):null;
    if(!el){return;}
    if(e.relatedTarget&&el.contains(e.relatedTarget)){return;}
    hideTip();
  });
  function fit(){
    var s=Math.min(window.innerWidth/1280,(window.innerHeight-70)/720);
    stage.style.transform='translate(-50%,-50%) scale('+s+')';
  }
  function show(n){
    var old=i; hideTip();
    i=Math.max(0,Math.min(slides.length-1,n));
    if(swipe){
      slides.forEach(function(el,k){
        el.classList.toggle('on',k===i);
        el.style.transform='translateX('+(k===i?0:(k<i?-100:100))+'%)';
      });
    } else {
      slides.forEach(function(el){el.classList.remove('prev');});
      if(old!==i){slides[old].classList.remove('on');slides[old].classList.add('prev');}
      slides[i].classList.add('on');
      window.clearTimeout(show._t);
      show._t=window.setTimeout(function(){
        if(old!==i){slides[old].classList.remove('prev');}
      },320);
    }
    pg.textContent=(i+1)+' / '+slides.length;
    prev.disabled=i===0; next.disabled=i===slides.length-1;
  }
  prev.onclick=function(){show(i-1);}; next.onclick=function(){show(i+1);};
  document.addEventListener('keydown',function(e){
    if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'){show(i+1);e.preventDefault();}
    else if(e.key==='ArrowLeft'||e.key==='PageUp'){show(i-1);e.preventDefault();}
    else if(e.key==='Home'){show(0);} else if(e.key==='End'){show(slides.length-1);}
  });
  // Auto-fit: if a slide's content overflows the fixed 720px canvas (e.g. a
  // footnote or the page number is clipped off the bottom), shrink that slide's
  // font scale in ~1px steps until it fits, down to a floor of ~2 points.
  function autofit(){
    slides.forEach(function(el){
      var st=el.querySelector('.stage');
      if(!st) return;
      st.style.zoom='';
      // If the content overflows the fixed canvas (e.g. a footnote or the page
      // number is clipped), shrink this slide's content in ~1px steps (on the
      // 24px body text) until it fits. Floor keeps text readable (~2pt max).
      // A slide may opt into a lower floor via data-fit-floor (e.g. a very
      // dense delivery-plan); otherwise use the default ~87.5% floor. The
      // guard scales with the range so a lower floor can actually be reached.
      var floor=st.dataset.fitFloor?parseFloat(st.dataset.fitFloor):21/24;
      var z=1, guard=0;
      while(st.scrollHeight>st.clientHeight+1 && z>floor && guard<16){
        z-=1/24; guard++;
        st.style.zoom=z.toFixed(4);
      }
    });
  }
  window.addEventListener('resize',fit); fit(); autofit(); show(0);
})();
""".strip()

# ---- optional PPTX / PDF export (client-side, one image per slide) ----------
EXPORT_JS = """
(function(){
  var slides=[].slice.call(document.querySelectorAll('.slide'));
  function capture(el){
    // Force the slide fully visible and untransformed at native 1280x720,
    // regardless of the on-screen scale / crossfade state.
    return htmlToImage.toPng(el,{
      width:1280,height:720,pixelRatio:2,backgroundColor:'#ffffff',
      style:{opacity:'1',transform:'none',position:'static',
             boxShadow:'none',borderRadius:'0'}
    });
  }
  function fileName(ext){
    return (document.title||'deck').replace(/[^a-z0-9._-]+/gi,'_')+ext;
  }
  // Capture every slide in order, invoking each(dataUrl,index), then done();
  // shows a progress counter on the button and restores it when finished.
  var busy=false;
  function run(btn,each,done){
    if(busy){return;}
    busy=true;
    btn.disabled=true;
    var label=btn.innerHTML;
    var chain=Promise.resolve();
    slides.forEach(function(el,k){
      chain=chain.then(function(){
        btn.innerHTML='&#8987; '+(k+1)+'/'+slides.length;
        return capture(el).then(function(dataUrl){each(dataUrl,k);});
      });
    });
    chain.then(done).then(function(){
      btn.innerHTML=label; btn.disabled=false; busy=false;
    }).catch(function(err){
      console.error('Export failed:',err);
      alert('Sorry, the export failed. See the console for details.');
      btn.innerHTML=label; btn.disabled=false; busy=false;
    });
  }
  var pptxBtn=document.getElementById('pptx');
  if(pptxBtn&&window.htmlToImage&&window.PptxGenJS){
    pptxBtn.onclick=function(){
      var pptx=new PptxGenJS();
      pptx.defineLayout({name:'DeckCraft16x9',width:10,height:5.625});
      pptx.layout='DeckCraft16x9';
      run(pptxBtn,function(dataUrl){
        pptx.addSlide().addImage({data:dataUrl,x:0,y:0,w:10,h:5.625});
      },function(){return pptx.writeFile({fileName:fileName('.pptx')});});
    };
  }
  var pdfBtn=document.getElementById('pdf');
  if(pdfBtn&&window.htmlToImage&&window.jspdf){
    pdfBtn.onclick=function(){
      var doc=new window.jspdf.jsPDF({orientation:'landscape',unit:'px',
                                      format:[1280,720]});
      run(pdfBtn,function(dataUrl,k){
        if(k>0){doc.addPage([1280,720],'landscape');}
        doc.addImage(dataUrl,'PNG',0,0,1280,720);
      },function(){doc.save(fileName('.pdf'));});
    };
  }
})();
""".strip()

def _read_lib(name):
    p = os.path.join(SELF_DIR, "lib", name)
    with open(p, encoding="utf-8") as fh:
        return fh.read()

def _libs_block(pptx=True, pdf=False):
    """Embed the bundled MIT libraries as inline <script> tags. html-to-image
    captures slides for either export; pptxgen / jsPDF are added only for the
    format(s) enabled.

    Licenses/attribution for these vendored bundles: lib/THIRD_PARTY_NOTICES.md.
    """
    names = []
    if pptx:
        names.append("pptxgen.bundle.js")
    if pdf:
        names.append("jspdf.umd.min.js")
    if pptx or pdf:
        names.append("html-to-image.js")
    tags = []
    for name in names:
        tags.append("<script>/* %s */\n%s\n</script>" % (name, _read_lib(name)))
    return "\n".join(tags) + "\n"

# ---- small helpers --------------------------------------------------------
def esc(s):
    return html.escape(s or "", quote=True)

def _sanitize_href(href):
    """Allowlist safe URL schemes so deck sources can't inject javascript:/data: links."""
    href = (href or "").strip()
    scheme = urlparse(href).scheme.lower()
    return href if scheme in ("", "http", "https", "mailto") else "#"

def _link(m):
    return '<a href="%s" rel="noopener noreferrer">%s</a>' % (_sanitize_href(m.group(2)), m.group(1))

def inline(s):
    """Minimal inline markdown: **bold**, *italic*, [text](url)."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", _link, s)
    return s

def plain_text(s):
    """Strip inline markdown (**bold**, *italic*, [text](url)) to plain text —
    used for tooltip/title attributes where markup can't render."""
    s = s or ""
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"\1", s)
    return s.strip()

WARNINGS = []

def data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as fh:
        return "data:%s;base64,%s" % (mime, base64.b64encode(fh.read()).decode())

def image(src, style, assets_dir, alt=""):
    """<img> for a local asset (base64-embedded) or a dashed placeholder.

    Must be a bare filename resolved inside assets_dir; absolute paths and
    parent traversal are rejected so a deck source cannot embed arbitrary
    local files.
    """
    if src:
        p = None
        if os.path.isabs(src) or os.path.basename(src) != src:
            WARNINGS.append("invalid image path (must be a filename in assets/): %s" % src)
        else:
            cand = os.path.abspath(os.path.join(assets_dir, src))
            if cand.startswith(os.path.abspath(assets_dir) + os.sep):
                p = cand
            else:
                WARNINGS.append("invalid image path (must be a filename in assets/): %s" % src)
        if p and os.path.isfile(p):
            return '<img src="%s" alt="%s" style="%s">' % (data_uri(p), esc(alt), style)
        if p is not None:
            WARNINGS.append("missing image: %s" % src)
        label = esc(src)
    else:
        label = "Image / Diagram"
    return ('<div class="missing" style="%s;display:flex;align-items:center;'
            'justify-content:center;background:var(--panel-flat);color:var(--muted);'
            'font-family:var(--font);font-size:var(--type-small);font-weight:500;'
            'border-radius:12px;">%s</div>') % (style, label)

# ---- chrome (shared across every slide) -----------------------------------
def topbar():
    return '<div style="height:var(--topbar-h);width:100%;background:var(--topbar-bg);flex:none;"></div>'

def footer(cls, pageno, year, dark):
    if dark:
        pgc, sepc, clsc, pad = "rgba(255,255,255,.65)", "rgba(255,255,255,.35)", "rgba(255,255,255,.5)", "32px"
    else:
        pgc, sepc, clsc, pad = "var(--ink-soft)", "var(--muted)", "var(--muted)", "28px"
    right = (('<div style="font-size:13px;font-weight:600;letter-spacing:.16em;'
              'text-transform:uppercase;color:%s;">%s</div>') % (clsc, esc(cls))) if cls else ""
    return ('<div style="display:flex;align-items:center;justify-content:space-between;'
            'padding:0 var(--pad-x) %s;font-family:var(--font);font-size:18px;'
            'letter-spacing:.1em;flex:none;">'
            '<div style="display:flex;align-items:center;">'
            '<div style="font-weight:800;color:%s;">%d</div>'
            '<div style="color:%s;font-weight:500;margin:0 12px;">|</div>'
            '<div style="color:%s;font-weight:600;">%s</div></div>'
            '%s</div>'
            ) % (pad, pgc, pageno, sepc, sepc, esc(year), right)

def footnote_block(text, dark=False):
    color = "rgba(255,255,255,.5)" if dark else "var(--muted)"
    return ('<div style="padding:2px var(--pad-x) 6px;font-family:var(--font);'
            'font-size:16px;font-style:italic;line-height:1.35;color:%s;flex:none;">%s</div>'
            ) % (color, inline(text))

def shell(inner, cls, pageno, year, dark=False, footnote=None):
    bg = "var(--dark-bg)" if dark else "var(--bg)"
    fn = footnote_block(footnote, dark) if footnote else ""
    return ('<section class="slide" style="background:%s;">%s%s%s%s</section>'
            % (bg, topbar(), inner, fn, footer(cls, pageno, year, dark)))

def stage(inner, center=False, fit_floor=None):
    just = "justify-content:center;" if center else ""
    # fit_floor lets a slide opt into a lower autofit zoom floor (e.g. a very
    # dense delivery-plan) WITHOUT changing the global floor for other slides.
    ff = (' data-fit-floor="%.4f"' % fit_floor) if fit_floor else ""
    return ('<div class="stage"%s style="flex:1;min-height:0;overflow:hidden;'
            'padding:var(--pad-top) var(--pad-x) var(--pad-bot);'
            'display:flex;flex-direction:column;%s">%s</div>') % (ff, just, inner)

def head(title, subtitle=None, dark=False):
    tc = "#fff" if dark else "var(--ink)"
    sc = "rgba(255,255,255,.5)" if dark else "var(--ink-soft)"
    sub = ('<div style="font-family:var(--font);font-size:var(--type-subtitle);'
           'color:%s;font-weight:500;margin-top:10px;">%s</div>' % (sc, inline(subtitle))
           ) if subtitle else ""
    return ('<div style="margin-bottom:var(--gap-title);">'
            '<div style="font-family:var(--font-display);font-size:var(--type-h2);font-weight:800;'
            'letter-spacing:-.02em;color:%s;line-height:1.05;">%s</div>%s</div>'
            ) % (tc, inline(title), sub)

# ---- parser ---------------------------------------------------------------
KNOWN_FIELDS = {"type", "title", "subtitle", "eyebrow", "number", "section",
                "image", "quote", "author", "role", "left-label", "right-label",
                "accent", "classification", "date", "audience", "name", "org",
                "email", "url", "logo", "label", "variant",
                "lead", "assistant", "pa", "statement", "columns", "quarters",
                "footnote", "markers", "style",
                "start", "end", "scale", "today", "teams", "bars", "density"}

def parse_deck(text):
    """Return (meta, slides). Front matter is the first --- fenced block."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    meta = {}
    lines = text.split("\n")
    # optional front matter
    if lines and lines[0].strip() == "---":
        j = 1
        while j < len(lines) and lines[j].strip() != "---":
            m = re.match(r"([a-zA-Z][\w-]*)\s*:\s*(.*)", lines[j])
            if m:
                meta[m.group(1).strip().lower()] = m.group(2).strip()
            j += 1
        lines = lines[j + 1:]
    # split remaining into slide blocks on lines that are exactly ---
    blocks, cur = [], []
    for ln in lines:
        if ln.strip() == "---":
            if any(x.strip() for x in cur):
                blocks.append(cur)
            cur = []
        else:
            cur.append(ln)
    if any(x.strip() for x in cur):
        blocks.append(cur)
    return meta, [parse_block(b) for b in blocks]

def parse_block(block):
    s = {"type": "bullets", "fields": {}, "items": [], "rows": []}
    for raw in block:
        line = raw.rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        # table row
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            s["rows"].append(cells)
            continue
        # column-2 item (right side)
        if stripped.startswith("-- "):
            s["items"].append({"text": stripped[3:].strip(), "subs": [], "col": 2})
            continue
        # sub-bullet (indented "- ")
        if stripped.startswith("- ") and indent >= 2 and s["items"]:
            s["items"][-1]["subs"].append(stripped[2:].strip())
            continue
        # top-level item
        if stripped.startswith("- "):
            s["items"].append({"text": stripped[2:].strip(), "subs": [], "col": 1})
            continue
        # field   key: value
        m = re.match(r"([a-zA-Z][\w-]*)\s*:\s*(.*)", line)
        if m and m.group(1).lower() in KNOWN_FIELDS:
            s["fields"][m.group(1).lower()] = m.group(2).strip()
            continue
        # otherwise body text
        s["fields"].setdefault("_body", []).append(stripped)
    s["type"] = s["fields"].pop("type", s["type"]).strip().lower()
    return s

def split_item(text, n=2):
    """Split 'Title :: body' (or 'a | b | c'); pads to n parts."""
    parts = [p.strip() for p in re.split(r"\s*::\s*", text)]
    if len(parts) == 1 and "|" in text:
        parts = [p.strip() for p in text.split("|")]
    while len(parts) < n:
        parts.append("")
    return parts

# ---- component fragments --------------------------------------------------
CARD = ("border:2px solid var(--line);border-radius:16px;"
        "background:var(--panel-grad);"
        "box-shadow:0 8px 24px rgba(0,0,0,.08);")

def card_title(text, color="var(--ink)"):
    return (f'<div style="font-family:var(--font);font-size:var(--type-subtitle);'
            f'font-weight:800;color:{color};line-height:1.2;">{inline(text)}</div>')

def card_body(text):
    if not text:
        return ""
    return (f'<div style="font-family:var(--font);font-size:var(--type-body);'
            f'color:var(--ink-soft);font-weight:500;line-height:1.5;">{inline(text)}</div>')

def bullet_li(text, subs=None, pad=36):
    li = (f'<li style="position:relative;padding-left:{pad}px;font-family:var(--font);'
          f'font-size:var(--type-body);font-weight:700;line-height:1.3;color:var(--ink);">'
          f'<span style="position:absolute;left:4px;top:.55em;width:13px;height:13px;'
          f'border-radius:50%;background:var(--ink);display:inline-block;"></span>'
          f'<span>{inline(text)}</span>')
    if subs:
        sub = '<ul style="list-style:none;margin:10px 0 0;display:flex;flex-direction:column;gap:8px;">'
        for su in subs:
            sub += (f'<li style="position:relative;padding-left:28px;font-family:var(--font);'
                    f'font-size:var(--type-body);font-weight:500;color:var(--ink-soft);">'
                    f'<span style="position:absolute;left:2px;top:.6em;width:8px;height:8px;'
                    f'border-radius:50%;background:var(--muted);display:inline-block;"></span>'
                    f'<span>{inline(su)}</span></li>')
        li += sub + "</ul>"
    return li + "</li>"

# ---- renderers (return (inner_html, dark)) --------------------------------
def r_cover(s, ctx):
    f, m = s["fields"], ctx["meta"]
    title = f.get("title") or m.get("title", "Presentation Title")
    subtitle = (f.get("subtitle") or m.get("subtitle")
                or " · ".join(x for x in [m.get("date"), m.get("audience")] if x)
                or "Subtitle or Date · Audience")
    logo = f.get("logo") or f.get("image")
    logo_html = (f'<div style="margin-bottom:36px;">'
                 f'{image(logo, "height:80px;width:auto;", ctx["assets"], "logo")}</div>'
                 ) if logo else ""
    inner = (f'{logo_html}'
             f'<div style="font-family:var(--font-display);font-size:var(--type-title);font-weight:800;'
             f'letter-spacing:-.03em;color:#fff;line-height:1.05;margin-bottom:20px;">{inline(title)}</div>'
             f'<div style="font-family:var(--font);font-size:var(--type-subtitle);'
             f'color:rgba(255,255,255,.55);letter-spacing:.06em;text-transform:uppercase;'
             f'font-weight:500;">{inline(subtitle)}</div>')
    return stage(inner, center=True), True

def r_section(s, ctx):
    f = s["fields"]
    eyebrow = f.get("section") or ("Section " + f.get("number", "01"))
    inner = (f'<div style="font-family:var(--font);font-size:var(--type-label);font-weight:600;'
             f'color:rgba(255,255,255,.45);letter-spacing:.12em;text-transform:uppercase;'
             f'margin-bottom:28px;">{inline(eyebrow)}</div>'
             f'<div style="font-family:var(--font-display);font-size:80px;font-weight:800;'
             f'letter-spacing:-.03em;color:#fff;line-height:1;">'
             f'{inline(f.get("title", "Section Title"))}</div>')
    return stage(inner, center=True), True

def r_agenda(s, ctx):
    items, n = s["items"], len(s["items"])
    rows = ""
    for idx, it in enumerate(items):
        label, timing = split_item(it["text"], 2)
        border = "" if idx == n - 1 else "border-bottom:1px solid var(--line);"
        rows += (f'<div style="display:flex;align-items:center;gap:48px;padding:28px 0;{border}">'
                 f'<div style="font-family:var(--font);font-size:var(--type-h3);font-weight:800;'
                 f'color:var(--accent);min-width:56px;">{idx + 1:02d}</div>'
                 f'<div style="font-family:var(--font);font-size:var(--type-subtitle);font-weight:700;'
                 f'color:var(--ink);flex:1;">{inline(label)}</div>'
                 f'<div style="font-family:var(--font);font-size:var(--type-body);'
                 f'color:var(--muted);">{inline(timing)}</div></div>')
    inner = (head(s["fields"].get("title", "Agenda"))
             + f'<div style="display:flex;flex-direction:column;gap:0;flex:1;'
               f'justify-content:center;">{rows}</div>')
    return stage(inner), False

def r_bullets(s, ctx):
    lis = "".join(bullet_li(it["text"], it["subs"]) for it in s["items"])
    inner = (head(s["fields"].get("title", "Overview"), s["fields"].get("subtitle"))
             + f'<ul style="list-style:none;display:flex;flex-direction:column;gap:var(--gap-item);'
               f'max-width:1100px;flex:1;">{lis}</ul>')
    return stage(inner), False

def r_two_col_bullets(s, ctx):
    items = s["items"]
    col1 = [it for it in items if it["col"] == 1]
    col2 = [it for it in items if it["col"] == 2]
    if not col2:
        half = (len(col1) + 1) // 2
        col1, col2 = col1[:half], col1[half:]
    def col(lst):
        return ('<ul style="list-style:none;display:flex;flex-direction:column;'
                'gap:var(--gap-item);">' + "".join(bullet_li(it["text"], None, 32)
                for it in lst) + "</ul>")
    inner = (head(s["fields"].get("title", "Two-Column Bullets"), s["fields"].get("subtitle"))
             + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:60px;flex:1;">'
               f'{col(col1)}{col(col2)}</div>')
    return stage(inner), False

def r_cards3(s, ctx):
    cells = ""
    for it in s["items"]:
        title, desc, img = split_item(it["text"], 3)
        icon = (image(img, "width:72px;height:72px;object-fit:contain;", ctx["assets"])
                if img else "")
        cells += (f'<div style="{CARD}padding:40px 36px;display:flex;flex-direction:column;gap:16px;">'
                  f'{icon}{card_title(title)}{card_body(desc)}</div>')
    inner = (head(s["fields"].get("title", "Three-Column Layout"), s["fields"].get("subtitle"))
             + f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:28px;flex:1;'
               f'align-content:center;">{cells}</div>')
    return stage(inner), False

def r_cards4(s, ctx):
    cells = ""
    for it in s["items"]:
        title, desc, img = split_item(it["text"], 3)
        icon = (image(img, "width:72px;height:72px;object-fit:contain;", ctx["assets"])
                if img else "")
        cells += (f'<div style="{CARD}padding:40px 36px;display:flex;flex-direction:column;gap:16px;">'
                  f'{icon}{card_title(title)}{card_body(desc)}</div>')
    inner = (head(s["fields"].get("title", "Four-Column Layout"), s["fields"].get("subtitle"))
             + f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:28px;flex:1;'
               f'align-content:center;">{cells}</div>')
    return stage(inner), False

def r_cards4_bullets(s, ctx):
    cells = ""
    for it in s["items"]:
        subs = it.get("subs") or []
        lis = ""
        for su in subs:
            lis += (f'<li style="position:relative;padding-left:22px;font-family:var(--font);'
                    f'font-size:18px;font-weight:500;color:var(--ink-soft);line-height:1.3;">'
                    f'<span style="position:absolute;left:2px;top:.5em;width:8px;height:8px;'
                    f'border-radius:50%;background:var(--ink);display:inline-block;"></span>'
                    f'<span>{inline(su)}</span></li>')
        ul = (f'<ul style="list-style:none;display:flex;flex-direction:column;gap:10px;'
              f'margin:0;">{lis}</ul>')
        cells += (f'<div style="{CARD}padding:24px 20px;display:flex;flex-direction:column;gap:14px;">'
                  f'<div style="font-family:var(--font);font-size:22px;font-weight:800;'
                  f'color:var(--ink);line-height:1.2;">{inline(it["text"])}</div>{ul}</div>')
    inner = (head(s["fields"].get("title", "Four-Column Layout"), s["fields"].get("subtitle"))
             + f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:20px;flex:1;'
               f'align-content:center;">{cells}</div>')
    return stage(inner), False

def r_grid2x2(s, ctx):
    cells = ""
    for it in s["items"]:
        hot = it["text"].startswith("*")
        label, stmt = split_item(it["text"].lstrip("*").strip(), 2)
        if hot:
            box = "border:2px solid var(--hot);background:var(--accent-soft);"
            tc = "var(--hot)"
        else:
            box = "border:2px solid var(--line);background:var(--panel-grad);"
            tc = "var(--ink)"
        cells += (f'<div style="{box}border-radius:16px;padding:36px;display:flex;'
                  f'flex-direction:column;gap:16px;">'
                  f'{card_title(label, tc)}{card_body(stmt)}</div>')
    inner = (head(s["fields"].get("title", "2 × 2 Grid"), s["fields"].get("subtitle"))
             + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;flex:1;'
               f'align-content:center;">{cells}</div>')
    return stage(inner), False

def r_grid3x2(s, ctx):
    cells = ""
    for it in s["items"]:
        title, desc = split_item(it["text"], 2)
        cells += (f'<div style="{CARD}padding:28px;display:flex;flex-direction:column;gap:16px;">'
                  f'{card_title(title)}{card_body(desc)}</div>')
    inner = (head(s["fields"].get("title", "3 × 2 Grid"), s["fields"].get("subtitle"))
             + f'<div style="display:grid;grid-template-columns:repeat(3,1fr);'
               f'gap:20px;flex:1;align-content:center;">{cells}</div>')
    return stage(inner), False

def r_flow_h(s, ctx):
    parts, n = [], len(s["items"])
    for idx, it in enumerate(s["items"]):
        title, desc = split_item(it["text"], 2)
        parts.append(
            f'<div style="flex:1;min-height:200px;{CARD}padding:36px 32px;display:flex;'
            f'flex-direction:column;gap:16px;">'
            f'<div style="width:48px;height:48px;border-radius:50%;background:var(--accent);'
            f'display:flex;align-items:center;justify-content:center;font-family:var(--font);'
            f'font-size:var(--type-body);color:#fff;font-weight:800;">{idx + 1}</div>'
            f'<div style="font-family:var(--font);font-size:var(--type-subtitle);color:var(--ink);'
            f'font-weight:800;line-height:1.2;">{inline(title)}</div>'
            f'<div style="font-family:var(--font);font-size:var(--type-body);color:var(--ink-soft);'
            f'font-weight:500;line-height:1.5;">{inline(desc)}</div></div>')
        if idx < n - 1:
            parts.append('<div style="padding:0 20px;flex-shrink:0;color:var(--muted);'
                         'font-size:40px;font-weight:800;">&#8250;</div>')
    inner = (head(s["fields"].get("title", "Horizontal Process Flow"), s["fields"].get("subtitle"))
             + f'<div style="display:flex;align-items:center;flex:1;gap:0;">{"".join(parts)}</div>')
    return stage(inner), False

def r_flow_v(s, ctx):
    f, n, steps = s["fields"], len(s["items"]), ""
    for idx, it in enumerate(s["items"]):
        title, desc = split_item(it["text"], 2)
        connector = ('<div style="width:2px;height:44px;background:var(--line);"></div>'
                     if idx < n - 1 else "")
        pad = "padding-bottom:44px;" if idx < n - 1 else ""
        steps += (f'<div style="display:flex;align-items:center;gap:32px;">'
                  f'<div style="display:flex;flex-direction:column;align-items:center;">'
                  f'<div style="width:52px;height:52px;border-radius:50%;background:var(--accent);'
                  f'display:flex;align-items:center;justify-content:center;font-family:var(--font);'
                  f'font-size:var(--type-body);color:#fff;font-weight:800;flex-shrink:0;">{idx + 1}</div>'
                  f'{connector}</div>'
                  f'<div style="display:flex;flex-direction:column;gap:4px;{pad}">'
                  f'<div style="font-family:var(--font);font-size:var(--type-subtitle);color:var(--ink);'
                  f'font-weight:700;">{inline(title)}</div>'
                  f'<div style="font-family:var(--font);font-size:var(--type-body);color:var(--ink-soft);'
                  f'font-weight:500;">{inline(desc)}</div></div></div>')
    left = (f'<div style="display:flex;flex-direction:column;justify-content:center;min-width:440px;">'
            f'<div style="font-family:var(--font);font-size:var(--type-h2);font-weight:800;'
            f'letter-spacing:-.02em;color:var(--ink);margin-bottom:16px;">'
            f'{inline(f.get("title", "Vertical Process Flow"))}</div>'
            f'<div style="font-family:var(--font);font-size:var(--type-subtitle);color:var(--ink-soft);'
            f'font-weight:500;">{inline(f.get("subtitle", "Top-to-bottom sequence"))}</div></div>')
    right = (f'<div style="display:flex;flex-direction:column;justify-content:center;flex:1;'
             f'gap:0;">{steps}</div>')
    inner = (f'<div style="flex:1;padding:var(--pad-top) var(--pad-x) var(--pad-bot);'
             f'display:flex;gap:80px;">{left}{right}</div>')
    return inner, False

def r_table(s, ctx):
    rows = s["rows"]
    f = s["fields"]
    if not rows:
        return stage(head(f.get("title", "Table"), f.get("subtitle"))), False
    header, body = rows[0], rows[1:]
    nc = len(header); last = nc - 1
    gc = f"1fr repeat({nc - 1},1.4fr)" if nc > 1 else "1fr"
    hc = ""
    for ci, c in enumerate(header):
        if ci == 0:
            hc += (f'<div style="font-family:var(--font);font-size:var(--type-body);'
                   f'color:rgba(255,255,255,.5);font-weight:600;letter-spacing:.04em;">{inline(c)}</div>')
        elif ci == last and nc > 2:
            hc += (f'<div style="font-family:var(--font);font-size:var(--type-body);'
                   f'color:#fff;font-weight:700;text-align:center;'
                   f'background:rgba(255,255,255,.08);border-radius:6px;padding:4px 0;">{inline(c)}</div>')
        else:
            hc += (f'<div style="font-family:var(--font);font-size:var(--type-body);color:#fff;'
                   f'font-weight:700;text-align:center;">{inline(c)}</div>')
    hrow = (f'<div style="display:grid;grid-template-columns:{gc};background:var(--head-bg);'
            f'padding:var(--row-pad) 32px;">{hc}</div>')
    brows = ""
    for ri, row in enumerate(body):
        bg = "var(--row-alt)" if ri % 2 == 0 else "var(--bg)"
        cs = ""
        for ci in range(nc):
            val = row[ci] if ci < len(row) else ""
            dot = _rag_dot(val) if ci else None
            if ci == 0:
                cs += (f'<div style="font-family:var(--font);font-size:var(--type-body);'
                       f'color:var(--ink);font-weight:700;">{inline(val)}</div>')
            elif dot:
                cs += dot
            elif ci == last and nc > 2:
                cs += (f'<div style="font-family:var(--font);font-size:var(--type-body);'
                       f'color:var(--accent);font-weight:800;text-align:center;">{inline(val)}</div>')
            else:
                cs += (f'<div style="font-family:var(--font);font-size:var(--type-body);'
                       f'color:var(--ink-soft);text-align:center;font-weight:500;">{inline(val)}</div>')
        brows += (f'<div style="display:grid;grid-template-columns:{gc};padding:var(--row-pad) 32px;'
                  f'align-items:center;background:{bg};">{cs}</div>')
    fn = f.pop("footnote", None)
    grow = "flex:none;" if fn else "flex:1;"
    container = (f'<div style="{grow}display:flex;flex-direction:column;border-radius:16px;'
                 f'overflow:hidden;border:2px solid var(--line);">{hrow}{brows}</div>')
    fn_html = (f'<div style="padding:14px 0 0;font-family:var(--font);font-size:16px;'
               f'font-style:italic;line-height:1.35;color:var(--muted);">{inline(fn)}</div>'
               ) if fn else ""
    return stage(head(f.get("title", "Comparison Table"), f.get("subtitle")) + container + fn_html), False

def r_stats(s, ctx):
    cells = ""
    for it in s["items"]:
        value, label, trend = split_item(it["text"], 3)
        tr = ""
        if trend:
            tr = (f'<div style="display:flex;align-items:center;gap:8px;">'
                  f'<div style="width:8px;height:8px;border-radius:50%;background:#3ad13a;"></div>'
                  f'<div style="font-family:var(--font);font-size:var(--type-small);color:#3ad13a;'
                  f'font-weight:600;">{inline(trend)}</div></div>')
        cells += (f'<div style="border:1px solid rgba(255,255,255,.1);border-radius:16px;'
                  f'padding:48px 40px;display:flex;flex-direction:column;gap:16px;'
                  f'justify-content:flex-end;background:rgba(255,255,255,.04);">'
                  f'<div style="font-family:var(--font);font-size:80px;color:#fff;line-height:.9;'
                  f'font-weight:800;letter-spacing:-.04em;">{inline(value)}</div>'
                  f'<div style="font-family:var(--font);font-size:var(--type-body);'
                  f'color:rgba(255,255,255,.55);font-weight:500;">{inline(label)}</div>{tr}</div>')
    inner = (head(s["fields"].get("title", "Key Metrics"), s["fields"].get("subtitle"), True)
             + f'<div style="display:grid;grid-template-columns:repeat({max(1, len(s["items"]))},1fr);'
               f'gap:24px;flex:1;">{cells}</div>')
    return stage(inner), True

def r_quote(s, ctx):
    f = s["fields"]
    quote = f.get("quote") or " ".join(f.get("_body", [])) or "Quotation text."
    author = f.get("author", "Speaker Name")
    role = f.get("role", "Title, Organisation")
    inner = (f'<div style="font-family:var(--font-display);font-size:80px;color:var(--accent);'
             f'line-height:.8;font-weight:800;margin-bottom:20px;">&#8220;</div>'
             f'<div style="font-family:var(--font-display);font-size:52px;line-height:1.2;color:var(--ink);'
             f'font-weight:800;max-width:1400px;letter-spacing:-.02em;margin-bottom:56px;">'
             f'{inline(quote)}</div>'
             f'<div style="display:flex;align-items:center;gap:24px;">'
             f'<div style="width:56px;height:56px;border-radius:50%;background:var(--line);"></div>'
             f'<div style="display:flex;flex-direction:column;gap:4px;">'
             f'<div style="font-family:var(--font);font-size:var(--type-body);color:var(--ink);'
             f'font-weight:700;">{inline(author)}</div>'
             f'<div style="font-family:var(--font);font-size:var(--type-small);color:var(--muted);'
             f'font-weight:500;">{inline(role)}</div></div></div>')
    return stage(inner, center=True), False

def r_text_image(s, ctx):
    f = s["fields"]
    lis = "".join(bullet_li(it["text"], None, 32) for it in s["items"])
    left = (f'<div style="flex:1;padding:var(--pad-top) 72px var(--pad-bot) var(--pad-x);'
            f'display:flex;flex-direction:column;justify-content:center;">'
            f'<div style="font-family:var(--font);font-size:var(--type-h2);font-weight:800;'
            f'letter-spacing:-.02em;color:var(--ink);margin-bottom:16px;">'
            f'{inline(f.get("title", "Text + Visual Split"))}</div>'
            f'<div style="font-family:var(--font);font-size:var(--type-subtitle);color:var(--ink-soft);'
            f'font-weight:500;margin-bottom:36px;">{inline(f.get("subtitle", ""))}</div>'
            f'<ul style="list-style:none;display:flex;flex-direction:column;gap:var(--gap-item);">{lis}</ul></div>')
    img = image(f.get("image"), "width:100%;height:100%;object-fit:contain;", ctx["assets"])
    right = (f'<div style="width:640px;background:var(--panel-flat);display:flex;align-items:center;'
             f'justify-content:center;flex-shrink:0;border-left:2px solid var(--line);'
             f'overflow:hidden;">{img}</div>')
    return f'<div style="flex:1;display:flex;align-items:stretch;">{left}{right}</div>', False

def _image_panel(src, assets):
    """A framed, contain-fit image panel that fills its grid/flex cell."""
    img = image(src, "max-width:100%;max-height:100%;width:auto;height:auto;"
                "object-fit:contain;", assets)
    return ('<div style="flex:1;min-height:0;background:var(--panel-flat);border:2px solid var(--line);'
            'border-radius:16px;overflow:hidden;display:flex;align-items:center;'
            'justify-content:center;padding:12px;">%s</div>') % img

def r_image_full(s, ctx):
    f = s["fields"]
    panel = _image_panel(f.get("image"), ctx["assets"])
    inner = (head(f.get("title", "Image"), f.get("subtitle"))
             + f'<div style="flex:1;min-height:0;display:flex;">{panel}</div>')
    return stage(inner), False

def _r_image_cols(s, ctx, n, default_title):
    f = s["fields"]
    srcs = [it["text"].strip() for it in s["items"]]
    if len(srcs) > n:
        WARNINGS.append("%s uses the first %d images; %d ignored"
                        % (s["type"], n, len(srcs) - n))
    srcs = (srcs[:n] + [None] * n)[:n]
    cells = "".join(_image_panel(src, ctx["assets"]) for src in srcs)
    grid = (f'<div style="flex:1;min-height:0;display:grid;'
            f'grid-template-columns:repeat({n},1fr);gap:20px;">{cells}</div>')
    inner = head(f.get("title", default_title), f.get("subtitle")) + grid
    return stage(inner), False

def r_image_2col(s, ctx):
    return _r_image_cols(s, ctx, 2, "Images")

def r_image_3col(s, ctx):
    return _r_image_cols(s, ctx, 3, "Images")

def r_timeline(s, ctx):
    milestones = ""
    for it in s["items"]:
        date, title, desc = split_item(it["text"], 3)
        milestones += (f'<div style="display:flex;flex-direction:column;align-items:center;gap:20px;'
                       f'position:relative;z-index:1;">'
                       f'<div style="width:52px;height:52px;border-radius:50%;background:var(--accent);'
                       f'border:4px solid var(--bg);"></div>'
                       f'<div style="text-align:center;display:flex;flex-direction:column;gap:6px;">'
                       f'<div style="font-family:var(--font);font-size:var(--type-small);color:var(--muted);'
                       f'font-weight:600;">{inline(date)}</div>'
                       f'<div style="font-family:var(--font);font-size:var(--type-body);color:var(--ink);'
                       f'font-weight:800;">{inline(title)}</div>'
                       f'<div style="font-family:var(--font);font-size:var(--type-label);color:var(--ink-soft);'
                       f'max-width:200px;line-height:1.4;">{inline(desc)}</div></div></div>')
    n = max(1, len(s["items"]))
    grid = (f'<div style="flex:1;display:flex;align-items:center;">'
            f'<div style="display:grid;grid-template-columns:repeat({n},1fr);width:100%;position:relative;">'
            f'<div style="position:absolute;top:24px;left:5%;right:5%;height:2px;background:var(--line);'
            f'z-index:0;"></div>{milestones}</div></div>')
    inner = head(s["fields"].get("title", "Roadmap"), s["fields"].get("subtitle")) + grid
    return stage(inner), False

def r_two_col_text(s, ctx):
    f = s["fields"]
    left_p = [it["text"] for it in s["items"] if it["col"] == 1]
    right_p = [it["text"] for it in s["items"] if it["col"] == 2]
    def paras(lst):
        out = ""
        for i, p in enumerate(lst):
            col = "var(--ink)" if i == 0 else "var(--ink-soft)"
            out += (f'<div style="font-family:var(--font);font-size:var(--type-body);color:{col};'
                    f'line-height:1.7;font-weight:500;">{inline(p)}</div>')
        return out
    def label(txt, color):
        return (f'<div style="font-family:var(--font);font-size:var(--type-small);color:{color};'
                f'letter-spacing:.1em;text-transform:uppercase;font-weight:700;">{inline(txt)}</div>')
    left = (f'<div style="display:flex;flex-direction:column;gap:24px;padding-right:60px;'
            f'border-right:2px solid var(--line);">'
            f'{label(f.get("left-label", "Challenge"), "var(--muted)")}{paras(left_p)}</div>')
    right = (f'<div style="display:flex;flex-direction:column;gap:24px;">'
             f'{label(f.get("right-label", "Approach"), "var(--accent)")}{paras(right_p)}</div>')
    inner = (head(f.get("title", "Problem / Solution"), f.get("subtitle"))
             + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:60px;flex:1;">{left}{right}</div>')
    return stage(inner), False

def r_closing(s, ctx):
    f = s["fields"]
    contacts = []
    for it in s["items"]:
        name, detail = split_item(it["text"], 2)
        contacts.append(f'<div style="display:flex;flex-direction:column;gap:6px;">'
                        f'<div style="font-family:var(--font);font-size:var(--type-body);color:#fff;'
                        f'font-weight:700;">{inline(name)}</div>'
                        f'<div style="font-family:var(--font);font-size:var(--type-small);'
                        f'color:rgba(255,255,255,.5);">{inline(detail)}</div></div>')
    divider = '<div style="width:1px;height:44px;background:rgba(255,255,255,.15);"></div>'
    row = divider.join(contacts)
    inner = (f'<div style="font-family:var(--font);font-size:var(--type-label);color:rgba(255,255,255,.4);'
             f'letter-spacing:.12em;text-transform:uppercase;font-weight:600;margin-bottom:32px;">'
             f'{inline(f.get("eyebrow", "Thank You"))}</div>'
             f'<div style="font-family:var(--font-display);font-size:80px;font-weight:800;letter-spacing:-.03em;'
             f'color:#fff;line-height:1;margin-bottom:56px;">{inline(f.get("title", "Questions?"))}</div>'
             f'<div style="display:flex;align-items:center;gap:56px;">{row}</div>')
    return stage(inner, center=True), True

# RAG status keywords -> dot colour (used by r_status).
RAG = {
    "green": "#22b455", "g": "#22b455", "on-track": "#22b455",
    "on track": "#22b455", "done": "#22b455", "complete": "#22b455",
    "amber": "#f0a020", "a": "#f0a020", "at-risk": "#f0a020",
    "at risk": "#f0a020", "yellow": "#f0a020", "watch": "#f0a020",
    "red": "#e23b3b", "r": "#e23b3b", "off-track": "#e23b3b",
    "off track": "#e23b3b", "blocked": "#e23b3b", "late": "#e23b3b",
}

def rag_color(key):
    return RAG.get((key or "").strip().lower(), "var(--muted)")

def _rag_dot(val):
    """Render a RAG cell as a coloured dot + label, or None if not a RAG word."""
    color = RAG.get((val or "").strip().lower())
    if not color:
        return None
    return (f'<div style="display:flex;align-items:center;justify-content:center;gap:10px;">'
            f'<span style="width:16px;height:16px;border-radius:50%;background:{color};'
            f'flex:none;"></span><span style="font-family:var(--font);'
            f'font-size:var(--type-body);color:var(--ink-soft);font-weight:700;">'
            f'{esc(val.strip().title())}</span></div>')

def r_status(s, ctx):
    items, n = s["items"], len(s["items"])
    rows = ""
    for idx, it in enumerate(items):
        name, status, note, owner = split_item(it["text"], 4)
        color = rag_color(status)
        border = "" if idx == n - 1 else "border-bottom:1px solid var(--line);"
        rows += (f'<div style="display:flex;align-items:center;gap:32px;padding:22px 4px;{border}">'
                 f'<div style="width:18px;height:18px;border-radius:50%;background:{color};'
                 f'flex:none;"></div>'
                 f'<div style="font-family:var(--font);font-size:var(--type-subtitle);font-weight:800;'
                 f'color:var(--ink);min-width:320px;">{inline(name)}</div>'
                 f'<div style="font-family:var(--font);font-size:var(--type-body);color:var(--ink-soft);'
                 f'font-weight:500;flex:1;line-height:1.3;">{inline(note)}</div>'
                 f'<div style="font-family:var(--font);font-size:var(--type-body);color:var(--muted);'
                 f'font-weight:600;text-align:right;min-width:170px;">{inline(owner)}</div></div>')
    inner = (head(s["fields"].get("title", "Workstream Status"), s["fields"].get("subtitle"))
             + f'<div style="display:flex;flex-direction:column;flex:1;justify-content:center;">{rows}</div>')
    return stage(inner), False

def r_bar_chart(s, ctx):
    f = s["fields"]
    CH = 360
    vals = []
    for it in s["items"]:
        hot = it["text"].startswith("*")
        label, raw = split_item(it["text"].lstrip("*").strip(), 2)
        num = re.sub(r"[^0-9.\-]", "", raw)
        try:
            v = float(num)
        except ValueError:
            v = 0.0
        vals.append((label, raw, v, hot))
    peak = max([v for _, _, v, _ in vals], default=0) or 1
    cols = ""
    for label, raw, v, hot in vals:
        hpx = max(6, round(v / peak * CH))
        fill = "var(--hot)" if hot else "var(--accent-soft)"
        vc = "var(--hot)" if hot else "var(--ink)"
        cols += (f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:14px;">'
                 f'<div style="font-family:var(--font);font-size:var(--type-body);font-weight:800;'
                 f'color:{vc};">{inline(raw)}</div>'
                 f'<div style="width:100%;max-width:120px;height:{hpx}px;background:{fill};'
                 f'border-radius:12px 12px 0 0;"></div>'
                 f'<div style="font-family:var(--font);font-size:var(--type-small);color:var(--muted);'
                 f'font-weight:600;text-align:center;">{inline(label)}</div></div>')
    inner = (head(f.get("title", "Bar Chart"), f.get("subtitle"))
             + f'<div style="flex:1;display:flex;align-items:flex-end;justify-content:space-around;'
               f'gap:40px;padding-top:20px;">{cols}</div>')
    return stage(inner), False

def r_callout(s, ctx):
    f = s["fields"]
    dark = (s["type"].endswith("-dark")
            or f.get("variant", "").strip().lower() in ("dark", "emphasis", "invert"))
    eyebrow = f.get("eyebrow") or f.get("label", "Recommendation")
    title = f.get("title") or " ".join(f.get("_body", [])) or "Our recommendation goes here."
    if dark:
        card_style = "border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.05);"
        tcol, icol = "#fff", "rgba(255,255,255,.82)"
    else:
        card_style, tcol, icol = CARD, "var(--ink)", "var(--ink)"
    body = ""
    if s["items"]:
        lis = ""
        for it in s["items"]:
            lis += (f'<li style="position:relative;padding-left:32px;font-family:var(--font);'
                    f'font-size:var(--type-body);font-weight:600;line-height:1.4;color:{icol};">'
                    f'<span style="position:absolute;left:2px;top:.5em;width:12px;height:12px;'
                    f'border-radius:50%;background:{icol};"></span>{inline(it["text"])}</li>')
        body = (f'<ul style="list-style:none;display:flex;flex-direction:column;gap:14px;'
                f'margin-top:12px;">{lis}</ul>')
    card = (f'<div style="{card_style}border-left:10px solid var(--accent);border-radius:20px;'
            f'padding:56px 64px;display:flex;flex-direction:column;gap:24px;max-width:1500px;">'
            f'<div style="font-family:var(--font);font-size:var(--type-label);color:var(--accent);'
            f'letter-spacing:.12em;text-transform:uppercase;font-weight:700;">{inline(eyebrow)}</div>'
            f'<div style="font-family:var(--font);font-size:52px;font-weight:800;letter-spacing:-.02em;'
            f'color:{tcol};line-height:1.15;">{inline(title)}</div>{body}</div>')
    return stage(card, center=True), dark

def _org_node(name, role, style, name_size="var(--type-subtitle)"):
    role_html = (f'<div style="font-family:var(--font);font-size:var(--type-small);'
                 f'color:var(--muted);font-weight:500;margin-top:6px;line-height:1.25;">'
                 f'{inline(role)}</div>') if role else ""
    return (f'<div style="{style}border-radius:14px;padding:20px 26px;text-align:center;">'
            f'<div style="font-family:var(--font);font-size:{name_size};font-weight:800;'
            f'color:var(--ink);line-height:1.15;">{inline(name)}</div>{role_html}</div>')

def r_org_chart(s, ctx):
    f = s["fields"]
    lead_name, lead_role = split_item(f.get("lead", f.get("title", "Lead")), 2)
    lead = _org_node(lead_name, lead_role,
                     "border:2px solid var(--accent);min-width:260px;"
                     "background:var(--accent-soft);",
                     name_size="var(--type-h3)")
    pa = f.get("assistant") or f.get("pa")
    pa_html = ""
    if pa:
        pa_name, pa_role = split_item(pa, 2)
        pa_card = _org_node(pa_name, pa_role,
                            "border:2px dashed var(--muted);min-width:190px;background:var(--bg);")
        pa_html = (f'<div style="position:absolute;left:100%;top:50%;transform:translateY(-50%);'
                   f'display:flex;align-items:center;white-space:nowrap;">'
                   f'<div style="width:52px;height:0;border-top:2px dashed var(--muted);"></div>'
                   f'{pa_card}</div>')
    lead_row = (f'<div style="display:flex;justify-content:center;">'
                f'<div style="position:relative;display:inline-flex;">{lead}{pa_html}</div></div>')
    def _bus(subset):
        ins = 50.0 / max(1, len(subset))
        cols = ""
        for it in subset:
            rn, rr = split_item(it["text"], 2)
            card = _org_node(rn, rr, CARD + "width:100%;")
            cols += (f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;'
                     f'box-sizing:border-box;padding:0 12px;">'
                     f'<div style="width:2px;height:38px;background:var(--line);"></div>{card}</div>')
        return (f'<div style="position:relative;display:flex;justify-content:center;'
                f'align-items:flex-start;width:100%;">'
                f'<div style="position:absolute;top:0;left:{ins:.3f}%;right:{ins:.3f}%;'
                f'height:2px;background:var(--line);"></div>{cols}</div>')
    # Up to ROW_MAX reports fit comfortably in one row; beyond that, wrap onto
    # two balanced rows joined by a short central connector so cards stay legible.
    reports = s["items"]
    n = len(reports)
    ROW_MAX = 6
    if n > ROW_MAX:
        half = (n + 1) // 2
        mid = '<div style="width:2px;height:30px;background:var(--line);"></div>'
        rows = _bus(reports[:half]) + mid + _bus(reports[half:])
    elif n:
        rows = _bus(reports)
    else:
        rows = ""
    stem = ('<div style="width:2px;height:36px;background:var(--line);"></div>'
            if n else "")
    tree = (f'<div style="display:flex;flex-direction:column;align-items:center;flex:1;'
            f'justify-content:center;gap:0;">{lead_row}{stem}{rows}</div>')
    inner = head(f.get("title", "Team Structure"), f.get("subtitle")) + tree
    return stage(inner), False

def r_statement(s, ctx):
    f = s["fields"]
    text = (f.get("title") or f.get("statement")
            or " ".join(f.get("_body", [])) or "A single big idea, stated plainly.")
    eyebrow = f.get("eyebrow") or f.get("label")
    eb = (f'<div style="font-family:var(--font);font-size:var(--type-label);'
          f'color:rgba(255,255,255,.4);letter-spacing:.14em;text-transform:uppercase;'
          f'font-weight:600;margin-bottom:36px;">{inline(eyebrow)}</div>') if eyebrow else ""
    bar = ('<div style="width:72px;height:6px;border-radius:3px;background:var(--accent);'
           'margin-bottom:40px;"></div>')
    inner = (f'{eb}{bar}'
             f'<div style="font-family:var(--font-display);font-size:64px;font-weight:800;'
             f'letter-spacing:-.02em;color:#fff;line-height:1.18;max-width:1500px;">'
             f'{inline(text)}</div>')
    return stage(inner, center=True), True

def _initials(name):
    parts = [p for p in re.split(r"\s+", (name or "").strip()) if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()

def r_team(s, ctx):
    f = s["fields"]
    items = s["items"]
    n = max(1, len(items))
    cols = min(n, 4)
    cells = ""
    for it in items:
        name, role, img = split_item(it["text"], 3)
        if img:
            avatar = image(img, "width:120px;height:120px;border-radius:50%;"
                           "object-fit:cover;", ctx["assets"], name)
        else:
            avatar = (f'<div style="width:120px;height:120px;border-radius:50%;'
                      f'background:var(--accent-soft);'
                      f'border:2px solid var(--accent);display:flex;align-items:center;'
                      f'justify-content:center;font-family:var(--font);font-size:var(--type-h3);'
                      f'font-weight:800;color:var(--accent);">{esc(_initials(name))}</div>')
        cells += (f'<div style="{CARD}padding:36px 28px;display:flex;flex-direction:column;'
                  f'align-items:center;text-align:center;gap:18px;">{avatar}'
                  f'<div style="display:flex;flex-direction:column;gap:6px;">'
                  f'<div style="font-family:var(--font);font-size:var(--type-subtitle);'
                  f'font-weight:800;color:var(--ink);line-height:1.15;">{inline(name)}</div>'
                  f'<div style="font-family:var(--font);font-size:var(--type-small);'
                  f'color:var(--muted);font-weight:500;line-height:1.25;">{inline(role)}</div>'
                  f'</div></div>')
    inner = (head(f.get("title", "The Team"), f.get("subtitle"))
             + f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);gap:28px;'
               f'flex:1;align-content:center;">{cells}</div>')
    return stage(inner), False

# Semantic tokens -> mark glyph + colour (used by r_matrix).
MATRIX_MARKS = {
    "yes": "y", "y": "y", "true": "y", "\u2713": "y", "check": "y", "full": "y",
    "no": "n", "n": "n", "false": "n", "\u2717": "n", "x": "n", "none": "n",
    "partial": "p", "~": "p", "maybe": "p", "some": "p", "\u00b1": "p", "half": "p",
}
MARK_GLYPH = {"y": ("\u2713", "#22b455"), "n": ("\u2717", "#e23b3b"),
              "p": ("~", "#f0a020")}

def _matrix_mark(val):
    key = MATRIX_MARKS.get((val or "").strip().lower())
    if not key:
        return None
    glyph, color = MARK_GLYPH[key]
    return (f'<div style="font-family:var(--font);font-size:32px;font-weight:800;'
            f'color:{color};text-align:center;line-height:1;">{glyph}</div>')

def r_matrix(s, ctx):
    rows = s["rows"]
    f = s["fields"]
    if not rows:
        return stage(head(f.get("title", "Comparison Matrix"), f.get("subtitle"))), False
    header, body = rows[0], rows[1:]
    nc = len(header); last = nc - 1
    gc = f"2fr repeat({nc - 1},1fr)" if nc > 1 else "1fr"
    hc = ""
    for ci, c in enumerate(header):
        if ci == 0:
            hc += (f'<div style="font-family:var(--font);font-size:var(--type-body);'
                   f'color:rgba(255,255,255,.5);font-weight:600;letter-spacing:.04em;">{inline(c)}</div>')
        elif ci == last and nc > 2:
            hc += (f'<div style="font-family:var(--font);font-size:var(--type-body);'
                   f'color:rgba(255,255,255,.7);font-weight:700;text-align:center;'
                   f'background:rgba(255,255,255,.08);border-radius:6px;padding:4px 0;">{inline(c)}</div>')
        else:
            hc += (f'<div style="font-family:var(--font);font-size:var(--type-body);color:#fff;'
                   f'font-weight:700;text-align:center;">{inline(c)}</div>')
    hrow = (f'<div style="display:grid;grid-template-columns:{gc};background:var(--head-bg);'
            f'padding:20px 32px;">{hc}</div>')
    brows = ""
    for ri, row in enumerate(body):
        bg = "var(--row-alt)" if ri % 2 == 0 else "var(--bg)"
        cs = ""
        for ci in range(nc):
            val = row[ci] if ci < len(row) else ""
            if ci == 0:
                cs += (f'<div style="font-family:var(--font);font-size:var(--type-body);'
                       f'color:var(--ink);font-weight:700;">{inline(val)}</div>')
                continue
            mark = _matrix_mark(val)
            if mark:
                cs += mark
            elif ci == last and nc > 2:
                cs += (f'<div style="font-family:var(--font);font-size:var(--type-body);'
                       f'color:var(--accent);font-weight:800;text-align:center;">{inline(val)}</div>')
            else:
                cs += (f'<div style="font-family:var(--font);font-size:var(--type-body);'
                       f'color:var(--ink-soft);text-align:center;font-weight:500;">{inline(val)}</div>')
        brows += (f'<div style="display:grid;grid-template-columns:{gc};padding:20px 32px;'
                  f'align-items:center;background:{bg};">{cs}</div>')
    container = (f'<div style="flex:1;display:flex;flex-direction:column;border-radius:16px;'
                 f'overflow:hidden;border:2px solid var(--line);">{hrow}{brows}</div>')
    return stage(head(f.get("title", "Comparison Matrix"), f.get("subtitle")) + container), False

def r_glossary(s, ctx):
    f = s["fields"]
    items = s["items"]
    col1 = [it for it in items if it["col"] == 1]
    col2 = [it for it in items if it["col"] == 2]
    if not col2:
        half = (len(col1) + 1) // 2
        col1, col2 = col1[:half], col1[half:]
    def col(lst):
        out = ""
        for it in lst:
            term, definition = split_item(it["text"], 2)
            out += (f'<div style="display:flex;flex-direction:column;gap:4px;">'
                    f'<div style="font-family:var(--font);font-size:var(--type-subtitle);'
                    f'font-weight:800;color:var(--accent);line-height:1.2;">{inline(term)}</div>'
                    f'<div style="font-family:var(--font);font-size:var(--type-body);'
                    f'color:var(--ink-soft);font-weight:500;line-height:1.4;">{inline(definition)}</div></div>')
        return f'<div style="display:flex;flex-direction:column;gap:22px;">{out}</div>'
    inner = (head(f.get("title", "Glossary"), f.get("subtitle"))
             + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:56px;flex:1;'
               f'align-content:center;">{col(col1)}{col(col2)}</div>')
    return stage(inner), False

# Phase-bar palette for r_swimlane (distinguishes phases within a row).
SWIM_COLORS = ["#2d7bff", "#00c2c7", "#3ad13a", "#ff7a00", "#7a3cff", "#e23b3b"]

# Weekday tokens for milestone (star) markers: index into a Mon–Sun week so the
# star can sit on the actual day within its column instead of the column start.
SWIM_WEEKDAYS = {"mon": 0, "monday": 0, "tue": 1, "tues": 1, "tuesday": 1,
                 "wed": 2, "weds": 2, "wednesday": 2, "thu": 3, "thur": 3,
                 "thurs": 3, "thursday": 3, "fri": 4, "friday": 4,
                 "sat": 5, "saturday": 5, "sun": 6, "sunday": 6}

def _phase(seg, nc):
    """Parse 'a-b Label' or 'a Label' into (start, end, label), clamped to nc."""
    seg = seg.strip()
    m = re.match(r"(\d+)\s*-\s*(\d+)\s+(.*)", seg)
    if m:
        a, b, lab = int(m.group(1)), int(m.group(2)), m.group(3)
    else:
        m2 = re.match(r"(\d+)\s+(.*)", seg)
        if not m2:
            return None
        a = b = int(m2.group(1)); lab = m2.group(2)
    a = max(1, min(nc, a)); b = max(a, min(nc, b))
    return a, b, lab.strip()

def r_swimlane(s, ctx):
    f = s["fields"]
    cols = [c.strip() for c in re.split(r"\s*\|\s*",
            (f.get("columns") or f.get("quarters") or "Q1 | Q2 | Q3 | Q4")) if c.strip()]
    nc = max(1, len(cols))
    grid = f"220px repeat({nc},1fr)"
    hcells = "<div></div>"
    for c in cols:
        hcells += (f'<div style="font-family:var(--font);font-size:var(--type-body);'
                   f'font-weight:700;color:var(--ink);text-align:center;">{inline(c)}</div>')
    header = (f'<div style="display:grid;grid-template-columns:{grid};gap:12px;'
              f'padding:0 8px 14px;border-bottom:2px solid var(--line);">{hcells}</div>')
    mk = (f.get("markers") or f.get("style") or "").strip().lower()
    milestone = mk in ("star", "stars", "milestone", "milestones")
    body = ""
    for idx, it in enumerate(s["items"]):
        parts = [p.strip() for p in re.split(r"\s*::\s*", it["text"])]
        name = parts[0] if parts else ""
        bars = ""
        for pi, seg in enumerate(parts[1:]):
            pr = _phase(seg, nc)
            if not pr:
                continue
            a, b, lab = pr
            color = SWIM_COLORS[pi % len(SWIM_COLORS)]
            if milestone:
                # Star mode selects per item from the leading weekday token:
                #   * a single weekday (or none) is an EXACT date → star on that
                #     day within the column;
                #   * a weekday range (e.g. Mon-Fri) or a multi-column span is a
                #     date RANGE → filled block covering those days.
                toks = lab.split(None, 1)
                tok = toks[0].lower().rstrip(".") if toks else ""
                rest = toks[1] if len(toks) > 1 else ""
                rng = re.match(r"([a-z]+)-([a-z]+)$", tok)
                if a != b:
                    bars += (f'<div data-tip="{esc(plain_text(lab))}" '
                             f'style="grid-column:{a + 1} / {b + 2};background:{color};'
                             f'border-radius:10px;padding:12px 16px;font-family:var(--font);'
                             f'font-size:var(--type-small);font-weight:700;color:#fff;'
                             f'line-height:1.15;white-space:nowrap;overflow:hidden;'
                             f'text-overflow:ellipsis;">{inline(lab)}</div>')
                elif rng and rng.group(1) in SWIM_WEEKDAYS and rng.group(2) in SWIM_WEEKDAYS:
                    d0, d1 = SWIM_WEEKDAYS[rng.group(1)], SWIM_WEEKDAYS[rng.group(2)]
                    lo, hi = min(d0, d1), max(d0, d1)
                    ml = lo / 7.0 * 100
                    wd = (hi - lo + 1) / 7.0 * 100
                    bars += (f'<div style="grid-column:{a + 1};position:relative;">'
                             f'<div data-tip="{esc(plain_text(rest))}" '
                             f'style="margin-left:{ml:.2f}%;width:{wd:.2f}%;'
                             f'box-sizing:border-box;background:{color};border-radius:10px;'
                             f'padding:12px 16px;font-family:var(--font);'
                             f'font-size:var(--type-small);font-weight:700;color:#fff;'
                             f'line-height:1.15;white-space:nowrap;overflow:hidden;'
                             f'text-overflow:ellipsis;">{inline(rest)}</div></div>')
                else:
                    off = (SWIM_WEEKDAYS[tok] + 0.5) / 7.0 if tok in SWIM_WEEKDAYS else 0.0
                    if tok in SWIM_WEEKDAYS:
                        lab = rest
                    # Outer div is the grid cell (width = one column); the inner
                    # margin-left % resolves against it, placing the star on the day.
                    bars += (f'<div style="grid-column:{a + 1};position:relative;">'
                             f'<div style="margin-left:{off * 100:.2f}%;display:inline-flex;'
                             f'align-items:center;gap:10px;white-space:nowrap;'
                             f'font-family:var(--font);font-size:var(--type-small);'
                             f'font-weight:700;color:var(--ink);line-height:1.15;">'
                             f'<span style="color:{color};font-size:26px;line-height:1;">&#9733;</span>'
                             f'<span>{inline(lab)}</span></div></div>')
            else:
                bars += (f'<div data-tip="{esc(plain_text(lab))}" '
                         f'style="grid-column:{a + 1} / {b + 2};background:{color};'
                         f'border-radius:10px;padding:12px 16px;font-family:var(--font);'
                         f'font-size:var(--type-small);font-weight:700;color:#fff;line-height:1.15;'
                         f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{inline(lab)}</div>')
        namecell = (f'<div style="font-family:var(--font);font-size:var(--type-body);'
                    f'font-weight:800;color:var(--ink);display:flex;align-items:center;">{inline(name)}</div>')
        bg = "var(--row-alt)" if idx % 2 == 0 else "var(--bg)"
        body += (f'<div style="display:grid;grid-template-columns:{grid};gap:12px;'
                 f'align-items:center;padding:14px 8px;background:{bg};border-radius:10px;'
                 f'min-height:64px;">{namecell}{bars}</div>')
    fn = f.pop("footnote", None)
    fn_html = (f'<div style="padding:14px 8px 0;font-family:var(--font);font-size:16px;'
               f'font-style:italic;line-height:1.35;color:var(--muted);">{inline(fn)}</div>'
               ) if fn else ""
    inner = (head(f.get("title", "Roadmap"), f.get("subtitle"))
             + f'<div style="display:flex;flex-direction:column;flex:1;justify-content:center;'
               f'gap:6px;">{header}{body}{fn_html}</div>')
    return stage(inner), False

# Team-bar palette for r_delivery_plan (cycled when a team has no explicit
# colour in the `teams:` legend). Kept distinct from SWIM_COLORS' order so the
# two renderers read differently at a glance.
PLAN_COLORS = ["#2d7bff", "#00b8a9", "#f0a020", "#7a3cff", "#e2467d",
               "#3ad13a", "#e23b3b", "#0a9bd6"]

# Status-bar palette for r_delivery_plan when `bars: status`. Bars are coloured
# by a RAG/progress word (field 3) instead of by team. Maps a word -> a canonical
# key so synonyms collapse; PLAN_STATUS_META holds the colour + legend label and
# defines the legend order. TBD/placeholder is a neutral grey.
PLAN_STATUS_ALIAS = {
    "complete": "complete", "completed": "complete", "done": "complete",
    "blue": "complete",
    "in-progress": "progress", "in progress": "progress", "progress": "progress",
    "on-track": "progress", "on track": "progress", "active": "progress",
    "amber": "atrisk", "at-risk": "atrisk", "at risk": "atrisk",
    "watch": "atrisk", "yellow": "atrisk",
    "red": "blocked", "blocked": "blocked", "off-track": "blocked",
    "off track": "blocked", "late": "blocked",
    "tbd": "tbd", "placeholder": "tbd", "grey": "tbd", "gray": "tbd",
    "not-started": "tbd", "planned": "tbd",
}
PLAN_STATUS_META = {
    "complete": ("#2d7bff", "Complete"),
    "progress": ("#f0a020", "On Track"),
    "atrisk":   ("#e07b00", "At Risk"),
    "blocked":  ("#e23b3b", "Blocked"),
    "tbd":      ("#9aa2ad", "TBD"),
}
# Legend order when in status mode.
PLAN_STATUS_ORDER = ["complete", "progress", "atrisk", "blocked", "tbd"]

def _plan_status(word):
    """Map a bar status word -> (canonical_key, colour). Unknown -> ('tbd', grey)."""
    key = PLAN_STATUS_ALIAS.get((word or "").strip().lower(), "tbd")
    return key, PLAN_STATUS_META[key][0]

PLAN_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
               "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11,
               "dec": 12}

def _parse_date(tok, default_year=None):
    """Parse a date token into a datetime.date, or None.

    Accepts ISO ``YYYY-MM-DD``, ``D Mon [YYYY]`` / ``Dth Mon`` (e.g. ``7 Apr``,
    ``28th April 2026``), and ``Mon YYYY`` / ``Mon`` (first of month). When no
    year is given, ``default_year`` is used so short forms stay inside the
    plan's own span.
    """
    if not tok:
        return None
    tok = tok.strip()
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})$", tok)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    # D[th] Mon [YYYY]
    m = re.match(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\.?\s*(\d{4})?$", tok)
    if m:
        mon = PLAN_MONTHS.get(m.group(2)[:4].lower()) or PLAN_MONTHS.get(m.group(2)[:3].lower())
        if mon:
            yr = int(m.group(3)) if m.group(3) else default_year
            if yr:
                try:
                    return date(yr, mon, int(m.group(1)))
                except ValueError:
                    return None
    # Mon [YYYY]  -> first of month
    m = re.match(r"([A-Za-z]+)\.?\s*(\d{4})?$", tok)
    if m:
        mon = PLAN_MONTHS.get(m.group(1)[:4].lower()) or PLAN_MONTHS.get(m.group(1)[:3].lower())
        if mon:
            yr = int(m.group(2)) if m.group(2) else default_year
            if yr:
                return date(yr, mon, 1)
    return None

def _plan_teams(raw):
    """Parse a ``teams:`` legend ('Client=#2d7bff, Server=#00b8a9') into an
    ordered {name_lower: (display, colour)} map, assigning palette colours to
    any entry that omits one."""
    out, ci = {}, 0
    for chunk in re.split(r"\s*,\s*", raw or ""):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" in chunk:
            name, col = chunk.split("=", 1)
            name, col = name.strip(), col.strip()
        else:
            name, col = chunk, ""
        # Custom colours are interpolated into a quoted style attribute, so only
        # accept a strict 6-digit hex; anything else falls back to the palette.
        if col and not re.fullmatch(r"#[0-9A-Fa-f]{6}", col):
            WARNINGS.append("delivery-plan: invalid team colour for '%s' -> palette" % name)
            col = ""
        if not col:
            col = PLAN_COLORS[ci % len(PLAN_COLORS)]
            ci += 1
        out[name.lower()] = (name, col)
    return out

def _plan_frac(d, start, span_days):
    """Fractional x-position (0..1) of date d across the plan span."""
    if not d or span_days <= 0:
        return 0.0
    return max(0.0, min(1.0, (d - start).days / span_days))

def _plan_pack_tracks(bars):
    """Greedy interval packing: assign each bar the lowest track whose previous
    bar has already ended, so sequential (non-overlapping) deliverables share a
    single track and only genuinely overlapping bars stack. Bars are ordered
    chronologically by start date; returns (track_index_by_bar_position, n_tracks).
    Ties/absent dates keep authored order and never overlap-collapse."""
    order = sorted(range(len(bars)), key=lambda i: (bars[i][2] is None, bars[i][2]))
    track_end = []                       # last end-date placed on each track
    track_of = [0] * len(bars)
    for i in order:
        _, _, d0, d1 = bars[i]
        placed = False
        for t, end in enumerate(track_end):
            # a bar can share a track if it starts on/after that track's last end
            if d0 is not None and end is not None and d0 >= end:
                track_end[t] = d1 if d1 is not None else end
                track_of[i] = t
                placed = True
                break
        if not placed:
            track_of[i] = len(track_end)
            track_end.append(d1 if d1 is not None else d0)
    return track_of, max(1, len(track_end))

def r_delivery_plan(s, ctx):
    f = s["fields"]
    # Seed the default year from whichever boundary states one explicitly
    # (start first, then end) so a yearless end doesn't mask a dated start.
    default_year = None
    for boundary in (f.get("start"), f.get("end")):
        m = re.search(r"((?:19|20)\d\d)", boundary or "")
        if m:
            default_year = int(m.group(1))
            break
    start = _parse_date(f.get("start"), default_year)
    end = _parse_date(f.get("end"), default_year)
    # If end's year was inferred equal to start's but lands on/before start, the
    # plan crosses a year boundary (e.g. start Nov 2026, end Mar) -> roll end to
    # the next year. Short bar/marker dates still inherit default_year, so add an
    # explicit year to rows that fall in the later year of such a span.
    if start and end and end <= start and not re.search(r"(?:19|20)\d\d", f.get("end") or ""):
        try:
            end = end.replace(year=end.year + 1)
        except ValueError:
            end = end + timedelta(days=365)
        WARNINGS.append("delivery-plan: end rolled to next year (span crosses a "
                        "year boundary) — add explicit years to later-year rows")
    if not start or not end or end <= start:
        # Fall back to a readable error band rather than crashing the build.
        WARNINGS.append("delivery-plan: needs valid 'start' and 'end' dates (start < end)")
        start = start or date.today()
        end = end if (end and end > start) else start + timedelta(days=90)
    span_days = (end - start).days

    # Colour mode: 'team' (default) colours bars by owner from teams:; 'status'
    # colours them by a RAG/progress word (field 3 of each bar) and swaps the
    # legend for a status legend.
    mode = (f.get("bars") or "team").strip().lower()
    status_mode = mode in ("status", "rag", "progress")
    used_status = set()   # canonical status keys seen, for the legend
    used_teams = {}       # team key -> (display, colour) seen on bars, for the legend

    # Density: an OPT-IN control so authors can trade bar/label size for more
    # swimlanes. Two levels: 'comfortable' (default) is unchanged from a normal
    # plan; 'compact' hides the title/subtitle, tightens the band floor + gaps,
    # and lowers this slide's autofit zoom floor so it auto-scales to any band
    # count (many lanes still fit). Other slide types are unaffected.
    # 'dense' (and its synonyms) is accepted as an alias of 'compact'.
    density = (f.get("density") or "comfortable").strip().lower()
    if density in ("comfortable", "normal", "roomy"):
        density = "comfortable"
    elif density in ("compact", "tight", "dense", "max", "packed"):
        density = "compact"
    else:
        WARNINGS.append("delivery-plan: unknown density '%s' -> comfortable" % density)
        density = "comfortable"

    teams = _plan_teams(f.get("teams"))
    def team_color(name):
        key = (name or "").strip().lower()
        if key in teams:
            return teams[key][1]
        # unknown team -> stable palette slot by insertion
        teams[key] = (name.strip() if name else "", PLAN_COLORS[len(teams) % len(PLAN_COLORS)])
        return teams[key][1]

    # ---- group items into phases -----------------------------------------
    groups, cur = [], None
    for it in s["items"]:
        parts = [p.strip() for p in re.split(r"\s*::\s*", it["text"])]
        kind = parts[0].lower() if parts else ""
        rest = parts[1:]
        if kind in ("phase", "group", "workstream", "row"):
            cur = {"name": rest[0] if rest else "", "refs": rest[1] if len(rest) > 1 else "",
                   "bars": [], "milestones": [], "launches": []}
            groups.append(cur)
            continue
        if cur is None:
            cur = {"name": "", "refs": "", "bars": [], "milestones": [], "launches": []}
            groups.append(cur)
        if kind in ("bar", "block", "dev"):
            # bar :: Label :: Team :: start..end
            label = rest[0] if rest else ""
            team = rest[1] if len(rest) > 1 else ""
            rng = rest[2] if len(rest) > 2 else ""
            # Split on '..'/en-dash (flexible), or an ASCII '-'/'to' that is
            # surrounded by whitespace — so an ISO date's hyphens (2026-03-01)
            # and the 'to' inside 'October' don't wrongly split the range.
            dm = re.split(r"(?:\s*\.\.\s*|\s*–\s*|\s+-\s+|\s+to\s+)", rng,
                          maxsplit=1, flags=re.IGNORECASE)
            d0 = _parse_date(dm[0], default_year) if dm else None
            d1 = _parse_date(dm[1], default_year) if len(dm) > 1 else None
            if d0 and d1:
                cur["bars"].append((label, team, d0, d1))
        elif kind in ("milestone", "ms", "gate"):
            # milestone :: Label :: status :: date
            label = rest[0] if rest else ""
            status = rest[1] if len(rest) > 1 else ""
            d = _parse_date(rest[2], default_year) if len(rest) > 2 else None
            if d:
                cur["milestones"].append((label, status, d))
        elif kind in ("launch", "golive", "go-live", "rocket"):
            # launch :: Label :: date
            label = rest[0] if rest else ""
            d = _parse_date(rest[1], default_year) if len(rest) > 1 else None
            if d:
                cur["launches"].append((label, d))

    # ---- axis: month gridlines -------------------------------------------
    # Tick at the first of EVERY month the span touches, including the (possibly
    # partial) start month, so a single-month or mid-month plan still gets a
    # label + gridline. Each label is centred over its VISIBLE segment (clamped
    # to [start, end]) rather than the full calendar month.
    ticks = []
    cyr, cmo = start.year, start.month
    while True:
        td = date(cyr, cmo, 1)
        if td > end:
            break
        ticks.append(td)
        cmo += 1
        if cmo > 12:
            cmo = 1; cyr += 1
    axis = ""
    for i, td in enumerate(ticks):
        nxt = ticks[i + 1] if i + 1 < len(ticks) else end + timedelta(days=1)
        # gridline sits at the month boundary, clamped to the plot's left edge
        gf = _plan_frac(max(td, start), start, span_days) * 100
        # label centres on the part of the month that is actually shown
        seg0, seg1 = max(td, start), min(nxt, end)
        mid = seg0 + (seg1 - seg0) / 2
        mf = _plan_frac(mid, start, span_days) * 100
        axis += (f'<div style="position:absolute;top:0;bottom:0;left:{gf:.3f}%;width:1px;'
                 f'background:var(--line);"></div>'
                 f'<div style="position:absolute;top:-26px;left:{mf:.3f}%;transform:translateX(-50%);'
                 f'font-family:var(--font);font-size:15px;font-weight:700;color:var(--muted);'
                 f'white-space:nowrap;">{td.strftime("%b %Y")}</div>')

    # today line
    today = _parse_date(f.get("today"), default_year)
    today_html = ""
    if today and start <= today <= end:
        tf = _plan_frac(today, start, span_days) * 100
        today_html = (f'<div style="position:absolute;top:-6px;bottom:0;left:{tf:.3f}%;width:2px;'
                      f'background:var(--accent);opacity:.7;z-index:4;"></div>'
                      f'<div style="position:absolute;top:-24px;left:{tf:.3f}%;transform:translateX(-50%);'
                      f'font-family:var(--font);font-size:12px;font-weight:800;color:var(--accent);'
                      f'letter-spacing:.06em;">TODAY</div>')

    # ---- rows -------------------------------------------------------------
    # Height budget: fit every band inside the fixed 720px canvas rather than
    # letting fixed row heights overflow (which clips lower swimlanes and
    # desyncs the rail from the plot). We compute a per-band height from the
    # available plot area, then size bars/gaps/fonts to match. Rail and plot
    # bands share the SAME height so the two columns stay pixel-aligned.
    n_bands = max(1, len(groups))
    # Density knobs (see the density: field above). comfortable = today's look.
    #   BAND_GAP   inter-band gap        BAND_FLOOR  min band height (legibility)
    #   HEADER     header reserve px     fit_floor   per-slide autofit zoom floor
    show_sub = True                      # compact hides the subtitle to reclaim px
    show_title = True                    # compact drops the whole title row
    fit_floor = None                     # None -> default global autofit floor
    if density == "compact":
        # Title hidden -> the header is just a slim legend strip, so HEADER only
        # needs to cover that strip (~34px key + a little gap), not a title.
        # The low autofit floor lets the slide zoom out so compact auto-scales
        # to any band count (many lanes still fit on the fixed canvas).
        BAND_GAP, BAND_FLOOR, HEADER = 5, 30, 44
        show_sub = False
        show_title = False
        fit_floor = 18 / 24              # ~0.75, well below the 0.875 default
    else:                                # comfortable (default)
        BAND_GAP, BAND_FLOOR, HEADER = 6, 38, 128
    # Vertical budget (measured against the real 720px canvas chrome):
    #   rainbow bar 10 + classification banner 23 + footer 28 + stage padding
    #   (top 48 + bottom 48) = 157px of fixed chrome the chart lives inside.
    #   The custom header (title + subtitle + gap-title) is the HEADER reserve
    #   above (shrinks with density). The legend sits INSIDE that header
    #   (top-right) so it costs nothing extra. Then reserve RAIL_TOP for the
    #   month labels above row 1 + a small bottom pad; the rest is the bands'.
    CHROME = 157
    RAIL_TOP = 26
    # Bottom safety reserve: keep a little clearance so the LAST band (often the
    # Milestones band, which also carries the caption lane) never clips even when
    # the header renders a touch taller than the 128px estimate.
    BOTTOM_PAD = 18
    plot_avail = CANVAS_H - CHROME - HEADER - RAIL_TOP - BOTTOM_PAD
    plot_avail = max(200, plot_avail)
    # per_band is the height of ONE band; the inter-band gaps are separate, so
    # subtract them from the budget before dividing (no double-count).
    per_band = (plot_avail - (n_bands - 1) * BAND_GAP) / n_bands
    per_band = max(BAND_FLOOR, per_band)  # never collapse below a legible floor

    # Pack each band's bars onto the fewest tracks: sequential (non-overlapping)
    # deliverables share one track, only true overlaps stack. This is what keeps
    # dense plans single-track (fat bars) instead of one row per deliverable.
    for g in groups:
        g["track_of"], g["n_tracks"] = _plan_pack_tracks(g["bars"])

    # A caption lane (for milestone/launch labels above the track) is only
    # reserved on bands that actually HAVE a milestone or launch. Bands with just
    # dev bars skip it, so their bars fill the band instead of leaving dead space.
    max_tracks = max((g["n_tracks"] for g in groups), default=1)
    # Caption lane height. Inline markers stagger across two rows, so when any
    # band carries 2+ markers reserve enough for both rows (~30px); a single
    # marker only needs one row (~18px). Capped so it never dominates the band.
    max_markers = max((len(g["milestones"]) + len(g["launches"]) for g in groups),
                      default=0)
    CAP_H = 30 if max_markers >= 2 else 18
    TRACK_GAP = 6
    PAD_V = 8                                    # top+bottom breathing room in a band
    # Size bars for the WORST case: the band with the most tracks, assuming it may
    # also carry a caption lane. This keeps every band's bars a uniform height.
    worst_cap = CAP_H if any(g["milestones"] or g["launches"] for g in groups) else 0
    track_room = max(12, per_band - worst_cap - PAD_V)
    BAR_H = (track_room - (max_tracks - 1) * TRACK_GAP) / max_tracks
    BAR_H = max(10, min(40, BAR_H))  # fatter bars when there's room; thin if dense
    if BAR_H <= 16:
        TRACK_GAP = 4
    # font sizes track the bar height so labels don't overflow thin bars
    bar_fs = max(9, min(15, round(BAR_H * 0.42)))
    cap_fs = max(8, min(11, round(CAP_H * 0.34)))
    name_fs = max(11, min(17, round(per_band * 0.24)))
    ref_fs = max(10, min(13, name_fs - 4))

    rail = ""      # left label column
    plot = ""      # right timeline column
    for gi, g in enumerate(groups):
        tracks = g["n_tracks"] if g["bars"] else 1
        band_h = round(per_band)     # every band identical height -> aligned
        bg = "var(--row-alt)" if gi % 2 == 0 else "var(--bg)"
        # rail label — same height as the plot band
        refs = (f'<div style="font-family:var(--font);font-size:{ref_fs}px;font-weight:700;'
                f'color:var(--accent);margin-top:3px;">{inline(g["refs"])}</div>') if g["refs"] else ""
        rail += (f'<div style="height:{band_h}px;display:flex;flex-direction:column;'
                 f'justify-content:center;padding:0 14px 0 0;background:{bg};box-sizing:border-box;'
                 f'border-radius:10px 0 0 10px;overflow:hidden;">'
                 f'<div style="font-family:var(--font);font-size:{name_fs}px;font-weight:800;'
                 f'color:var(--ink);line-height:1.15;">{inline(g["name"])}</div>{refs}</div>')
        # plot band
        bars_html = ""
        # This band only needs a caption lane if it carries a milestone/launch;
        # bars-only bands use the whole band so the bars sit fatter and centred.
        band_cap = CAP_H if (g["milestones"] or g["launches"]) else 0
        # centre the stacked tracks within the space below the caption lane
        stack_h = tracks * BAR_H + (tracks - 1) * TRACK_GAP
        stack_top = band_cap + max(0, (band_h - band_cap - stack_h) / 2)
        for bi, (label, team, d0, d1) in enumerate(g["bars"]):
            lf = _plan_frac(d0, start, span_days) * 100
            wf = max(1.2, (_plan_frac(d1, start, span_days) - _plan_frac(d0, start, span_days)) * 100)
            if status_mode:
                # field 3 is a status word -> colour the bar by RAG/progress
                skey, col = _plan_status(team)
                used_status.add(skey)
            else:
                col = team_color(team)
                # remember the colour->team pairing so the legend can decode it
                tkey = (team or "").strip().lower()
                if tkey:
                    used_teams[tkey] = (team.strip(), col)
            # vertical slot = this bar's PACKED track (sequential bars share one)
            ti = g["track_of"][bi]
            top = stack_top + ti * (BAR_H + TRACK_GAP)
            # The label lives in an inner span that owns the truncation, so the
            # bar's left/right padding stays symmetric even when the text clips
            # (otherwise the ellipsis runs to the right edge and looks lopsided).
            bars_html += (f'<div data-tip="{esc(plain_text(label))}" '
                          f'style="position:absolute;top:{top:.1f}px;left:{lf:.3f}%;width:{wf:.3f}%;'
                          f'height:{BAR_H:.1f}px;background:{col};border-radius:6px;display:flex;'
                          f'align-items:center;padding:0 9px;box-sizing:border-box;'
                          f'box-shadow:0 2px 6px rgba(20,30,70,.18);overflow:hidden;">'
                          f'<span style="min-width:0;font-family:var(--font);font-size:{bar_fs}px;'
                          f'font-weight:700;color:#fff;line-height:1.1;white-space:nowrap;'
                          f'overflow:hidden;text-overflow:ellipsis;">{inline(label)}</span></div>')
        # Milestones + launches render as INLINE markers: a coloured dot with the
        # label + date on a single line to its side (no tall stacked caption).
        # Launches reuse the milestone green dot (no rocket) so the band reads
        # consistently. Markers are merged and sorted by date, then a marker is
        # pushed to a 2nd row ONLY when its label would actually overlap the one
        # before it (collision-aware) — so a plan with well-spaced markers keeps
        # every dot on a single baseline instead of alternating unnecessarily.
        dot = max(9, min(13, round(CAP_H * 0.42)))
        markers = ([(d, label, rag_color(status)) for label, status, d in g["milestones"]]
                   + [(d, label, rag_color("green")) for label, d in g["launches"]])
        markers.sort(key=lambda m: (m[0] is None, m[0]))
        # A milestone-only band (no bars) has no track stack under the caption
        # lane, so the lane would otherwise sit pinned to the top with dead space
        # below. Centre the two-row caption block vertically within the band.
        cap_off = 0 if g["bars"] else max(0, (band_h - CAP_H) / 2)
        # Estimate each label's horizontal footprint (as a % of the 922px plot)
        # so we can detect real overlaps. Widths are approximate — char count x
        # font size — but only need to be good enough to spot collisions; we lean
        # slightly wide so labels never touch. Anchor side matches the render.
        PLOT_PX = CANVAS_W - 2 * 64 - 230       # canvas minus stage pad-x + rail
        placed = []
        for d, label, col in markers:
            lf = _plan_frac(d, start, span_days) * 100
            date_txt = d.strftime("%d %b") if d else ""
            right_side = lf <= 62               # label right of dot, unless near the edge
            text = f"{label} \u00b7 {date_txt}"
            w_pct = (dot + 5 + len(text) * cap_fs * 0.58 + 8) / PLOT_PX * 100
            x0, x1 = (lf, lf + w_pct) if right_side else (lf - w_pct, lf)
            placed.append([d, label, col, lf, right_side, date_txt, x0, x1])
        # Greedy 2-row packing: keep each row's running right edge; a marker sits
        # on the top row if it clears the last top-row label (+PAD), else bottom.
        row_end = [-1e9, -1e9]
        PAD = 1.2                               # min % gap required between labels
        for m in placed:
            row = 0 if m[6] >= row_end[0] + PAD else 1
            row_end[row] = m[7]
            m.append(row)
        for d, label, col, lf, right_side, date_txt, x0, x1, row in placed:
            row_y = cap_off + (1 if row == 0 else max(1, band_cap - dot - 1))
            lbl = (f'<span style="font-family:var(--font);font-size:{cap_fs}px;font-weight:800;'
                   f'color:var(--ink);white-space:nowrap;line-height:1;">{inline(label)}'
                   f'<span style="color:var(--muted);font-weight:700;"> \u00b7 {date_txt}</span></span>')
            dot_html = (f'<span style="width:{dot}px;height:{dot}px;border-radius:50%;background:{col};'
                        f'border:2px solid var(--bg);flex:none;box-shadow:0 1px 4px '
                        f'rgba(20,30,70,.25);"></span>')
            inner_order = f'{dot_html}{lbl}' if right_side else f'{lbl}{dot_html}'
            anchor = f'left:{lf:.3f}%;' if right_side else f'right:{100 - lf:.3f}%;'
            bars_html += (f'<div style="position:absolute;top:{row_y:.0f}px;{anchor}'
                          f'display:flex;align-items:center;gap:5px;z-index:3;">{inner_order}</div>')
        plot += (f'<div style="position:relative;height:{band_h}px;background:{bg};box-sizing:border-box;'
                 f'border-radius:0 10px 10px 0;">{bars_html}</div>')

    # Exact height of the rendered band stack (every band is band_h, with a
    # BAND_GAP between them). The gridline overlay is pinned to THIS height so
    # the month lines stop at the bottom of the last band instead of running on
    # to the container's floor and leaving stray grey lines below the plan.
    band_h_px = round(per_band)
    stack_total = n_bands * band_h_px + (n_bands - 1) * BAND_GAP

    # Legend: a colour key so bar colours can be decoded. Status mode lists the
    # RAG meanings (Complete / On Track / At Risk / Blocked / TBD). Team mode
    # lists the teams actually used by bars — the rail names the PHASE, not the
    # team, so a phase mixing multiple teams is otherwise undecodable.
    legend = ""
    if status_mode:
        # show the statuses actually used, in canonical order
        for key in PLAN_STATUS_ORDER:
            if key not in used_status:
                continue
            col, name = PLAN_STATUS_META[key]
            legend += (f'<div style="display:flex;align-items:center;gap:7px;">'
                       f'<span style="width:14px;height:14px;border-radius:4px;background:{col};'
                       f'flex:none;"></span><span style="font-family:var(--font);font-size:14px;'
                       f'font-weight:600;color:var(--ink-soft);">{esc(name)}</span></div>')
    else:
        # team mode: show the teams actually used by bars, in first-seen order
        for name, col in used_teams.values():
            legend += (f'<div style="display:flex;align-items:center;gap:7px;">'
                       f'<span style="width:14px;height:14px;border-radius:4px;background:{col};'
                       f'flex:none;"></span><span style="font-family:var(--font);font-size:14px;'
                       f'font-weight:600;color:var(--ink-soft);">{esc(name)}</span></div>')
    # Compact key for the header top-right. Columns scale with the number of
    # entries so a big key stays short (wider, not taller) and never steals
    # vertical space from the swimlanes: <=6 -> 2 cols, 7-12 -> 3, 13+ -> 4.
    n_legend = len(used_status) if status_mode else len(used_teams)
    legend_cols = 2 if n_legend <= 6 else (3 if n_legend <= 12 else 4)
    legend_html = (f'<div style="display:grid;'
                   f'grid-template-columns:repeat({legend_cols},auto);'
                   f'gap:4px 16px;align-content:start;justify-content:end;">{legend}</div>'
                   ) if legend else ""
    # Horizontal variant for the title-less view (compact): the key runs
    # as a single wrapping row across the top, so it uses width not the valuable
    # top-right corner. Wraps to a 2nd row only if there are too many entries.
    legend_row_html = (f'<div style="display:flex;flex-wrap:wrap;align-items:center;'
                       f'gap:6px 18px;">{legend}</div>') if legend else ""

    # Both columns start their band stacks at the same y (RAIL_TOP) and use the
    # same inter-band gap (BAND_GAP) so rows line up exactly. The axis backdrop
    # (gridlines + month labels + today line) spans the plot area behind the
    # bands, offset only enough to clear the month labels sitting above row 1.
    # RAIL_TOP must match the budget's RAIL_TOP so the height maths and the
    # rendered layout agree (a mismatch here reintroduces bottom-band clipping).
    chart = (f'<div style="display:grid;grid-template-columns:230px 1fr;gap:0;flex:1;'
             f'min-height:0;overflow:hidden;">'
             f'<div style="display:flex;flex-direction:column;gap:{BAND_GAP}px;'
             f'padding-top:{RAIL_TOP}px;">{rail}</div>'
             f'<div style="position:relative;padding-top:{RAIL_TOP}px;">'
             f'<div style="position:absolute;top:{RAIL_TOP}px;left:0;right:0;'
             f'height:{stack_total}px;">'
             f'{axis}{today_html}</div>'
             f'<div style="position:relative;display:flex;flex-direction:column;'
             f'gap:{BAND_GAP}px;">{plot}</div></div></div>')
    # Custom header: title/subtitle on the left, the key on the right. This keeps
    # the legend off the plot area so every swimlane band gets the full height.
    title_txt = f.get("title", "Delivery Plan")
    sub = f.get("subtitle")
    # compact density hides the subtitle on the plot to reclaim header height.
    sub_html = (f'<div style="font-family:var(--font);font-size:var(--type-subtitle);'
                f'color:var(--ink-soft);font-weight:500;margin-top:10px;">{inline(sub)}</div>'
                ) if (sub and show_sub) else ""
    # Header bottom gap shrinks with density so the rendered header matches the
    # reduced HEADER reserve used in the budget above.
    head_mb = {"comfortable": "var(--gap-title)", "compact": "8px"}[density]
    if show_title:
        # Full header: title (+ optional subtitle) left, key right.
        header = (f'<div style="display:flex;align-items:flex-start;'
                  f'justify-content:space-between;gap:24px;margin-bottom:{head_mb};">'
                  f'<div><div style="font-family:var(--font);font-size:var(--type-h2);'
                  f'font-weight:800;letter-spacing:-.02em;color:var(--ink);line-height:1.05;">'
                  f'{inline(title_txt)}</div>{sub_html}</div>'
                  f'<div style="flex:none;padding-top:4px;">{legend_html}</div></div>')
    else:
        # Title-less (compact): the key runs as a single horizontal row
        # across the top so it uses width, not the valuable top-right corner.
        # The plot reclaims the title's vertical space. Suppressed if no key.
        header = (f'<div style="margin-bottom:{head_mb};">{legend_row_html}</div>'
                  ) if legend_row_html else ""
    inner = (header
             + f'<div style="display:flex;flex-direction:column;flex:1;min-height:0;">'
               f'{chart}</div>')
    return stage(inner, fit_floor=fit_floor), False

# ---- dispatch + build -----------------------------------------------------
RENDERERS = {
    "cover": r_cover, "section": r_section, "section-divider": r_section, "divider": r_section,
    "agenda": r_agenda, "bullets": r_bullets, "bullet": r_bullets,
    "two-col-bullets": r_two_col_bullets, "2col-bullets": r_two_col_bullets,
    "cards-3": r_cards3, "cards3": r_cards3, "cards": r_cards3,
    "cards-4": r_cards4, "cards4": r_cards4,
    "cards-4-bullets": r_cards4_bullets, "cards4-bullets": r_cards4_bullets,
    "cards-4-bullet": r_cards4_bullets, "cards4b": r_cards4_bullets,
    "grid-2x2": r_grid2x2, "2x2": r_grid2x2, "grid2x2": r_grid2x2,
    "grid-3x2": r_grid3x2, "3x2": r_grid3x2, "grid3x2": r_grid3x2,
    "flow-h": r_flow_h, "flow": r_flow_h, "flow-horizontal": r_flow_h,
    "flow-v": r_flow_v, "flow-vertical": r_flow_v,
    "table": r_table, "stats": r_stats, "stat": r_stats, "quote": r_quote,
    "text-image": r_text_image, "text+image": r_text_image, "image": r_text_image,
    "image-full": r_image_full, "image-fullwidth": r_image_full,
    "screenshot": r_image_full, "fullbleed-image": r_image_full,
    "image-2col": r_image_2col, "images-2": r_image_2col, "two-image": r_image_2col,
    "image-3col": r_image_3col, "images-3": r_image_3col, "three-image": r_image_3col,
    "timeline": r_timeline, "roadmap": r_timeline,
    "two-col-text": r_two_col_text, "two-col": r_two_col_text, "problem-solution": r_two_col_text,
    "status": r_status, "rag": r_status, "workstream-status": r_status,
    "bar-chart": r_bar_chart, "bar": r_bar_chart, "barchart": r_bar_chart, "chart": r_bar_chart,
    "callout": r_callout, "decision": r_callout, "recommendation": r_callout,
    "callout-dark": r_callout, "decision-dark": r_callout, "recommendation-dark": r_callout,
    "org-chart": r_org_chart, "org": r_org_chart, "orgchart": r_org_chart,
    "org-tree": r_org_chart, "reporting-line": r_org_chart, "team-structure": r_org_chart,
    "statement": r_statement, "big-idea": r_statement, "bigidea": r_statement, "impact": r_statement,
    "team": r_team, "people": r_team, "team-grid": r_team, "avatars": r_team,
    "matrix": r_matrix, "feature-compare": r_matrix, "feature-comparison": r_matrix,
    "comparison-matrix": r_matrix, "compare": r_matrix,
    "glossary": r_glossary, "definitions": r_glossary, "terms": r_glossary,
    "roadmap-swimlane": r_swimlane, "swimlane": r_swimlane, "swimlanes": r_swimlane,
    "roadmap-grid": r_swimlane,
    "delivery-plan": r_delivery_plan, "delivery": r_delivery_plan,
    "delivery-timeline": r_delivery_plan, "gantt": r_delivery_plan,
    "e2e-plan": r_delivery_plan,
    "closing": r_closing, "close": r_closing, "thanks": r_closing,
}

def build(deck_path, out_path=None, pptx=None, pdf=None, index=True):
    WARNINGS.clear()
    deck_path = os.path.abspath(deck_path)
    base = os.path.dirname(deck_path)
    assets = os.path.join(base, "assets")
    out_path = out_path or os.path.splitext(deck_path)[0] + ".html"
    with open(deck_path, encoding="utf-8") as fh:
        meta, slides = parse_deck(fh.read())
    theme_tokens = resolve_theme(meta)
    accent = theme_tokens["accent"]
    cls = meta.get("classification", DEFAULT_CLASS)
    date_value = meta.get("date", "") or ""
    m4 = re.search(r"(?:19|20)\d\d", date_value)
    m2 = None if m4 else re.search(r"(?<!\d)\d\d(?!\d)", date_value)
    if m4:
        year = m4.group(0)
    elif m2:
        year = "20" + m2.group(0)
    else:
        if date_value:
            WARNINGS.append("could not derive footer year from date: %s" % date_value)
        year = str(time.localtime().tm_year)
    mode = "fx-swipe" if meta.get("transition", "fade").strip().lower() == "swipe" else "fx-fade"
    ctx = {"meta": meta, "accent": accent, "assets": assets, "class": cls}
    parts = []
    for i, s in enumerate(slides):
        r = RENDERERS.get(s["type"])
        if r is None:
            WARNINGS.append("unknown slide type '%s' (slide %d) -> bullets" % (s["type"], i + 1))
            r = r_bullets
        inner, dark = r(s, ctx)
        parts.append(shell(inner, s["fields"].get("classification", cls), i + 1, year, dark,
                           s["fields"].get("footnote")))
    css = ROOT_CSS
    for key, val in theme_tokens.items():
        css = css.replace("%%%s%%" % key.upper(), val)
    want_pptx = PPTX_EXPORT if pptx is None else pptx
    want_pdf = PDF_EXPORT if pdf is None else pdf
    want_export = want_pptx or want_pdf
    page = (PAGE.replace("%TITLE%", esc(meta.get("title", "Presentation")))
                .replace("%MODE%", mode)
                .replace("%CSS%", css).replace("%SLIDES%", "\n".join(parts))
                .replace("%PPTX_BTN%", PPTX_BTN if want_pptx else "")
                .replace("%PDF_BTN%", PDF_BTN if want_pdf else "")
                .replace("%LIBS%", _libs_block(want_pptx, want_pdf) if want_export else "")
                .replace("%JS%", NAV_JS)
                .replace("%EXPORT%", "<script>%s</script>\n" % EXPORT_JS if want_export else ""))
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(page)
    if index:
        try:
            record_build(deck_path, out_path, meta=meta, slide_count=len(slides))
        except Exception as e:
            WARNINGS.append("library index update failed: %s" % e)
    return out_path, len(slides)

def _watch_mtime(deck_path):
    base = os.path.dirname(os.path.abspath(deck_path))
    paths = [os.path.abspath(deck_path)]
    assets = os.path.join(base, "assets")
    if os.path.isdir(assets):
        paths += [os.path.join(assets, n) for n in os.listdir(assets)]
    stamp = 0.0
    for p in paths:
        try:
            stamp = max(stamp, os.path.getmtime(p))
        except OSError:
            pass
    return stamp

def _rebuild(deck_path, out_path, pptx=None, pdf=None, index=True):
    try:
        out, n = build(deck_path, out_path, pptx=pptx, pdf=pdf, index=index)
        msg = "Built %s  (%d slides)" % (out, n)
        for w in WARNINGS:
            msg += "\n  ! " + w
        return msg
    except Exception as e:
        return "Build failed: %s" % e

def watch(deck_path, out_path=None, interval=0.5, pptx=None, pdf=None, index=True):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    print(_rebuild(deck_path, out_path, pptx=pptx, pdf=pdf, index=index))
    print("Watching %s and assets/ - save to rebuild; Ctrl+C to stop." % deck_path)
    last = _watch_mtime(deck_path)
    try:
        while True:
            time.sleep(interval)
            now = _watch_mtime(deck_path)
            if now != last:
                last = now
                print("[%s] %s  (refresh browser: Cmd+R)"
                      % (time.strftime("%H:%M:%S"),
                         _rebuild(deck_path, out_path, pptx=pptx, pdf=pdf, index=index)))
    except KeyboardInterrupt:
        print("\nStopped watching.")
    return 0

def main(argv):
    args = [a for a in argv[1:] if not a.startswith("-")]
    flags = [a for a in argv[1:] if a.startswith("-")]
    if not args:
        print(__doc__); return 2
    deck = args[0]
    out = args[1] if len(args) > 1 else None
    pptx = False if "--no-pptx" in flags else None
    pdf = False if "--no-pdf" in flags else None
    index = "--no-index" not in flags
    if "--watch" in flags or "-w" in flags:
        return watch(deck, out, pptx=pptx, pdf=pdf, index=index)
    out, n = build(deck, out, pptx=pptx, pdf=pdf, index=index)
    print("Built %s  (%d slides)" % (out, n))
    for w in WARNINGS:
        print("  ! " + w)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
