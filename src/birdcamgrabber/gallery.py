"""Minimal web gallery for browsing captured bird photos.

Run as `python -m birdcamgrabber.gallery`. Serves images from
``BIRDCAM_IMAGE_DIR`` (default ``/data/images``) on
``BIRDCAM_GALLERY_PORT`` (default 8383).

The directory layout produced by the capture loop is::

    <image_dir>/YYYY-MM-DD/HHMMSS-<event_id>/frame-NNN.jpg
"""

import logging
import os
from pathlib import Path

from flask import Flask, abort, render_template_string, send_from_directory

logger = logging.getLogger(__name__)

IMAGE_DIR = Path(os.environ.get("BIRDCAM_IMAGE_DIR", "/data/images")).resolve()

app = Flask(__name__)

CSS = """
body { font-family: -apple-system, system-ui, sans-serif; background: #111;
       color: #eee; margin: 0; padding: 1rem; }
a { color: #6cf; text-decoration: none; }
a:hover { text-decoration: underline; }
h1, h2, h3 { color: #fff; }
h1 { margin-top: 0; }
nav { margin-bottom: 1rem; font-size: 0.9rem; }
ul.list { list-style: none; padding: 0; }
ul.list li { padding: 0.5rem 0; border-bottom: 1px solid #333; }
.session { margin-bottom: 2rem; }
.session h3 { margin: 0 0 0.4rem 0; font-weight: normal; font-size: 0.95rem;
              color: #aaa; }
.grid { display: grid; gap: 0.4rem;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); }
.grid a { display: block; }
.grid img { width: 100%; height: 140px; object-fit: cover; border-radius: 4px;
            background: #222; display: block; }
.empty { color: #888; font-style: italic; }
"""

INDEX_TMPL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Birdcam Gallery</title><style>{{ css }}</style></head><body>
<h1>Birdcam Gallery</h1>
{% if dates %}
<ul class="list">
{% for d, count in dates %}
  <li><a href="{{ url_for('date_view', date=d) }}">{{ d }}</a>
      &mdash; {{ count }} capture{{ '' if count == 1 else 's' }}</li>
{% endfor %}
</ul>
{% else %}
<p class="empty">No captures yet.</p>
{% endif %}
</body></html>
"""

DATE_TMPL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{{ date }} &mdash; Birdcam</title><style>{{ css }}</style></head><body>
<nav><a href="{{ url_for('index') }}">&larr; All dates</a></nav>
<h1>{{ date }}</h1>
{% if sessions %}
{% for session, frames in sessions %}
<div class="session">
  <h3>{{ session }} &mdash; {{ frames|length }} frame{{ '' if frames|length == 1 else 's' }}</h3>
  <div class="grid">
  {% for f in frames %}
    <a href="{{ url_for('image', date=date, session=session, frame=f) }}" target="_blank">
      <img src="{{ url_for('image', date=date, session=session, frame=f) }}" loading="lazy" alt="{{ f }}">
    </a>
  {% endfor %}
  </div>
</div>
{% endfor %}
{% else %}
<p class="empty">No captures on this date.</p>
{% endif %}
</body></html>
"""


def _safe_child(parent: Path, name: str) -> Path:
    """Resolve ``parent/name`` and ensure it stays within ``parent``."""
    if "/" in name or "\\" in name or name in ("", ".", ".."):
        abort(404)
    child = (parent / name).resolve()
    try:
        child.relative_to(parent)
    except ValueError:
        abort(404)
    if not child.exists():
        abort(404)
    return child


@app.route("/")
def index():
    dates: list[tuple[str, int]] = []
    if IMAGE_DIR.exists():
        for d in sorted(IMAGE_DIR.iterdir(), reverse=True):
            if d.is_dir():
                count = sum(1 for c in d.iterdir() if c.is_dir())
                dates.append((d.name, count))
    return render_template_string(INDEX_TMPL, dates=dates, css=CSS)


@app.route("/date/<date>")
def date_view(date: str):
    date_dir = _safe_child(IMAGE_DIR, date)
    if not date_dir.is_dir():
        abort(404)
    sessions: list[tuple[str, list[str]]] = []
    for s in sorted(date_dir.iterdir(), reverse=True):
        if not s.is_dir():
            continue
        frames = sorted(
            f.name for f in s.iterdir()
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png")
        )
        sessions.append((s.name, frames))
    return render_template_string(DATE_TMPL, date=date, sessions=sessions, css=CSS)


@app.route("/image/<date>/<session>/<frame>")
def image(date: str, session: str, frame: str):
    date_dir = _safe_child(IMAGE_DIR, date)
    session_dir = _safe_child(date_dir, session)
    # send_from_directory itself guards against traversal in `frame`.
    return send_from_directory(session_dir, frame)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    port = int(os.environ.get("BIRDCAM_GALLERY_PORT", "8383"))
    logger.info("Starting gallery on port %d, serving from %s", port, IMAGE_DIR)
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
