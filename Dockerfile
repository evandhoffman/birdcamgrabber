FROM cgr.dev/chainguard/python:latest-dev AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY src/ src/
RUN uv sync --no-dev --frozen --no-editable

FROM cgr.dev/chainguard/python:latest

# Keep runtime minimal. The app currently uses opencv-python-headless, so it
# does not need the optional ffmpeg/libgl runtime packages.

USER root

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

RUN ["python", "-c", "import os,pwd; u=pwd.getpwnam('nonroot'); os.makedirs('/data/images', exist_ok=True); os.chown('/data/images', u.pw_uid, u.pw_gid)"]
VOLUME ["/data/images"]

USER nonroot

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["python", "-m", "birdcamgrabber"]
CMD ["/data/config.yaml"]
