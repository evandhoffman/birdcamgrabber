FROM cgr.dev/chainguard/python:latest-dev AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY src/ src/
RUN uv sync --no-dev --frozen

FROM cgr.dev/chainguard/python:latest

# Keep runtime minimal. The app currently uses opencv-python-headless, so it
# does not need the optional ffmpeg/libgl runtime packages.

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

RUN mkdir -p /data/images && chown nonroot:nonroot /data/images
VOLUME ["/data/images"]

USER nonroot

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["python", "-m", "birdcamgrabber"]
CMD ["/data/config.yaml"]
