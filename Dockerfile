FROM cgr.dev/chainguard/python:latest-dev AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY src/ src/
COPY scripts/ scripts/

FROM cgr.dev/chainguard/python:latest-dev

# Install ffmpeg for RTSP clip capture.  The -dev variant is required for apk.
USER root
RUN apk add --no-cache ffmpeg

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

RUN ["python", "-c", "import os,pwd; u=pwd.getpwnam('nonroot'); os.makedirs('/data/images', exist_ok=True); os.chown('/data/images', u.pw_uid, u.pw_gid)"]
VOLUME ["/data/images"]

USER nonroot

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

ENTRYPOINT ["python", "-m", "birdcamgrabber"]
CMD ["/data/config.yaml"]
