FROM cgr.dev/chainguard/python:latest-dev AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY src/ src/
RUN uv sync --no-dev --frozen


FROM cgr.dev/chainguard/python:latest-dev

# ffmpeg for potential future use; opencv needs libgl
RUN apk add --no-cache ffmpeg libstdc++

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

RUN mkdir -p /data/images && chown nonroot:nonroot /data/images
VOLUME ["/data/images"]

USER nonroot

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["python", "-m", "birdcamgrabber"]
CMD ["/data/config.yaml"]
