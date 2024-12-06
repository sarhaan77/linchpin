# https://github.com/astral-sh/uv-docker-example/blob/main/Dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libstdc++6

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

ADD . /app
RUN uv sync --frozen

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uv", "run", "bot.py"]