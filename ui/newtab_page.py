"""
AXIOM New Tab Page
------------------
Generates a self-contained HTML new-tab page injected via setHtml().

Features
--------
- Full-screen background: user image (base64 data-URI) or themed gradient.
- 10 built-in dark theme presets (Neo Noir, Catppuccin, Dracula, …)
- Live clock (HH:MM) updated every second.
- Google-style search bar that queries the user's configured search engine.
- Quick-access bookmarks grid (up to 12, icon + title cards).
- Minimal AXIOM watermark.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Optional

from storage.bookmarks_manager import Bookmark

# ---------------------------------------------------------------------------
# Preset theme catalogue
# ---------------------------------------------------------------------------

PRESET_THEMES: dict[str, dict[str, str]] = {
    "Neo Noir": {
        "gradient": "linear-gradient(135deg, #0D0F1A 0%, #141428 35%, #1a1040 65%, #0a0a1a 100%)",
        "accent":   "#5B9CF6",
    },
    "Midnight Blue": {
        "gradient": "linear-gradient(135deg, #0a0e1a 0%, #0d1530 40%, #111d45 70%, #080d1a 100%)",
        "accent":   "#4D8EFF",
    },
    "Catppuccin Mocha": {
        "gradient": "linear-gradient(135deg, #1e1e2e 0%, #181825 35%, #1e1e2e 65%, #11111b 100%)",
        "accent":   "#CBA6F7",
    },
    "Dracula": {
        "gradient": "linear-gradient(135deg, #282a36 0%, #21222c 35%, #282a36 65%, #1a1b23 100%)",
        "accent":   "#BD93F9",
    },
    "Tokyo Night": {
        "gradient": "linear-gradient(135deg, #1a1b2e 0%, #16161e 35%, #1f202e 65%, #0f0f1a 100%)",
        "accent":   "#7AA2F7",
    },
    "Solarized Dark": {
        "gradient": "linear-gradient(135deg, #002b36 0%, #073642 35%, #002b36 65%, #00212b 100%)",
        "accent":   "#268BD2",
    },
    "AMOLED Black": {
        "gradient": "linear-gradient(135deg, #000000 0%, #080808 35%, #050505 65%, #000000 100%)",
        "accent":   "#FF6B6B",
    },
    "Nord": {
        "gradient": "linear-gradient(135deg, #2e3440 0%, #3b4252 35%, #2e3440 65%, #242933 100%)",
        "accent":   "#88C0D0",
    },
    "Gruvbox": {
        "gradient": "linear-gradient(135deg, #282828 0%, #3c3836 35%, #282828 65%, #1d2021 100%)",
        "accent":   "#FABD2F",
    },
    "Rose Pine": {
        "gradient": "linear-gradient(135deg, #191724 0%, #1f1d2e 35%, #191724 65%, #111020 100%)",
        "accent":   "#EBBCBA",
    },
}

_DEFAULT_PRESET = "Neo Noir"
_MAX_QUICK_ACCESS = 12


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _img_to_data_uri(path: str) -> Optional[str]:
    """Read an image from disk and return a data: URI, or None on failure."""
    try:
        ext = Path(path).suffix.lower().lstrip(".")
        mime = {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp",
            "gif": "image/gif",
        }.get(ext, "image/png")
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except OSError:
        return None


def _favicon_data_uri(b64: str) -> str:
    if b64:
        return f"data:image/png;base64,{b64}"
    return ""


# ---------------------------------------------------------------------------
# HTML generator
# ---------------------------------------------------------------------------

def generate_newtab_html(
    bookmarks: list[Bookmark],
    background_path: str = "",
    preset: str = _DEFAULT_PRESET,
    search_url: str = "https://www.google.com/search?q={}",
) -> str:
    """Return a complete HTML string for the AXIOM new-tab page."""

    # ── Theme ─────────────────────────────────────────────────────────
    theme = PRESET_THEMES.get(preset, PRESET_THEMES[_DEFAULT_PRESET])
    accent = theme["accent"]

    # ── Background ────────────────────────────────────────────────────
    bg_data_uri = _img_to_data_uri(background_path) if background_path else None
    if bg_data_uri:
        bg_css = f"background: url('{bg_data_uri}') center/cover no-repeat fixed;"
        overlay_alpha = 0.30
    else:
        bg_css = f"background: {theme['gradient']};"
        overlay_alpha = 0.0

    # ── Search URL (safe for JS string literal) ───────────────────────
    safe_search_url = json.dumps(search_url)   # includes surrounding quotes + escaping

    # ── Quick-access bookmarks (up to _MAX_QUICK_ACCESS) ─────────────
    shown = bookmarks[:_MAX_QUICK_ACCESS]
    cards_html = ""
    for bm in shown:
        fav_uri = _favicon_data_uri(bm.favicon_b64)
        icon_html = (
            f'<img class="card-icon" src="{fav_uri}" alt="">'
            if fav_uri else
            '<div class="card-icon card-letter">'
            + (bm.title[:1].upper() if bm.title else "?")
            + "</div>"
        )
        title = (bm.title or bm.url)[:24]
        safe_url   = bm.url.replace('"', "%22")
        safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        cards_html += f"""
        <a class="card" href="{safe_url}" title="{safe_title}">
            {icon_html}
            <span class="card-title">{safe_title}</span>
        </a>"""

    # ── Full HTML ─────────────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>New Tab</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  html, body {{
    width: 100%; height: 100%;
    font-family: -apple-system, 'Segoe UI Variable', 'Segoe UI', sans-serif;
    overflow: hidden;
  }}

  body {{ {bg_css} }}

  .overlay {{
    position: fixed; inset: 0;
    background: rgba(0,0,0,{overlay_alpha});
  }}

  .page {{
    position: relative; z-index: 1;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    height: 100vh; gap: 28px;
  }}

  /* ── Clock ── */
  .clock {{
    font-size: 72px; font-weight: 200; letter-spacing: -2px;
    color: rgba(255,255,255,0.92);
    text-shadow: 0 2px 24px rgba(0,0,0,0.5);
    line-height: 1; user-select: none;
  }}

  /* ── Search bar ── */
  .search-wrap {{
    width: 100%; max-width: 560px; padding: 0 16px;
  }}
  .search-form {{
    display: flex; align-items: center;
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 26px;
    backdrop-filter: blur(16px);
    padding: 0 18px;
    transition: background 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
  }}
  .search-form:focus-within {{
    background: rgba(255,255,255,0.16);
    border-color: {accent}99;
    box-shadow: 0 0 0 3px {accent}22;
  }}
  .search-icon {{
    font-size: 15px; color: rgba(255,255,255,0.45);
    margin-right: 10px; flex-shrink: 0; user-select: none;
  }}
  .search-input {{
    flex: 1;
    background: transparent; border: none; outline: none;
    color: rgba(255,255,255,0.92);
    font-size: 15px; font-weight: 400;
    height: 44px;
    font-family: -apple-system, 'Segoe UI Variable', 'Segoe UI', sans-serif;
  }}
  .search-input::placeholder {{ color: rgba(255,255,255,0.38); }}

  /* ── Quick-access grid ── */
  .grid {{
    display: flex; flex-wrap: wrap;
    justify-content: center; gap: 14px;
    max-width: 720px; padding: 0 16px;
  }}

  .card {{
    display: flex; flex-direction: column;
    align-items: center; gap: 7px;
    width: 88px; padding: 14px 8px 12px;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 14px;
    backdrop-filter: blur(12px);
    text-decoration: none;
    transition: background 120ms ease, transform 120ms ease, border-color 120ms ease;
    cursor: pointer;
  }}
  .card:hover {{
    background: rgba(255,255,255,0.16);
    border-color: {accent}88;
    transform: translateY(-2px);
  }}
  .card:active {{ transform: translateY(0); }}

  .card-icon {{
    width: 32px; height: 32px;
    object-fit: contain; border-radius: 6px;
  }}
  .card-letter {{
    width: 32px; height: 32px; border-radius: 8px;
    background: {accent}33;
    border: 1px solid {accent}66;
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; font-weight: 600; color: {accent};
  }}
  .card-title {{
    font-size: 11px; font-weight: 400;
    color: rgba(255,255,255,0.80);
    text-align: center;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    max-width: 76px;
  }}

  .hint {{
    font-size: 13px; color: rgba(255,255,255,0.35); user-select: none;
  }}

  .watermark {{
    position: fixed; bottom: 16px; right: 20px;
    font-size: 11px; font-weight: 600; letter-spacing: 3px;
    color: rgba(255,255,255,0.18); user-select: none;
  }}
</style>
</head>
<body>
<div class="overlay"></div>
<div class="page">
  <div class="clock" id="clock">00:00</div>

  <div class="search-wrap">
    <form class="search-form" id="search-form">
      <span class="search-icon">&#128269;</span>
      <input
        class="search-input"
        id="search-input"
        type="text"
        placeholder="Search or enter URL\u2026"
        autocomplete="off"
        spellcheck="false"
      >
    </form>
  </div>

  {'<div class="grid">' + cards_html + '</div>'
    if shown else
    '<p class="hint">No bookmarks yet \u2014 press Ctrl+D to add one</p>'}
</div>
<div class="watermark">AXIOM</div>

<script>
  (function () {{
    // ── Clock ──
    function tick() {{
      var now = new Date();
      var h = String(now.getHours()).padStart(2, '0');
      var m = String(now.getMinutes()).padStart(2, '0');
      document.getElementById('clock').textContent = h + ':' + m;
    }}
    tick();
    setInterval(tick, 1000);

    // ── Search ──
    var SEARCH_URL = {safe_search_url};
    document.getElementById('search-form').addEventListener('submit', function (e) {{
      e.preventDefault();
      var q = document.getElementById('search-input').value.trim();
      if (q) {{
        window.location.href = SEARCH_URL.replace('{{}}', encodeURIComponent(q));
      }}
    }});

    // Auto-focus search bar
    document.getElementById('search-input').focus();
  }})();
</script>
</body>
</html>"""
