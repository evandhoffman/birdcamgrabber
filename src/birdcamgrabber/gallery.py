"""Minimal web gallery for browsing captured bird video clips.

Run as `python -m birdcamgrabber.gallery`. Serves clips from
``BIRDCAM_IMAGE_DIR`` (default ``/data/images``) on
``BIRDCAM_GALLERY_PORT`` (default 8383).

The directory layout produced by the capture loop is::

    <image_dir>/YYYY-MM-DD/HHMMSS-<event_id>.mp4
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
.grid { display: grid; gap: 0.75rem;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
.clip video { width: 100%; border-radius: 4px; background: #222; display: block; }
.clip p { margin: 0.3rem 0 0; font-size: 0.85rem; color: #aaa; }
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
      &mdash; {{ count }} clip{{ '' if count == 1 else 's' }}</li>
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
{% if clips %}
<div class="grid">
{% for clip in clips %}
  <div class="clip">
    <video controls preload="metadata">
      <source src="{{ url_for('clip', date=date, filename=clip) }}" type="video/mp4">
    </video>
    <p>{{ clip }}</p>
  </div>
{% endfor %}
</div>
{% else %}
<p class="empty">No clips on this date.</p>
{% endif %}
</body></html>
"""


def _safe_child(parent: Path, name: str) -> Path:
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
                count = sum(1 for f in d.iterdir() if f.suffix.lower() == ".mp4")
                dates.append((d.name, count))
    return render_template_string(INDEX_TMPL, dates=dates, css=CSS)


@app.route("/date/<date>")
def date_view(date: str):
    date_dir = _safe_child(IMAGE_DIR, date)
    if not date_dir.is_dir():
        abort(404)
    clips = sorted(
        f.name for f in date_dir.iterdir()
        if f.is_file() and f.suffix.lower() == ".mp4"
    )
    return render_template_string(DATE_TMPL, date=date, clips=clips, css=CSS)


@app.route("/clip/<date>/<filename>")
def clip(date: str, filename: str):
    date_dir = _safe_child(IMAGE_DIR, date)
    return send_from_directory(date_dir, filename)


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
