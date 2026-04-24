FROM python:3.13-slim
# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Setup environment variables for Python and uv
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app/src
WORKDIR /app
# Copy dependency files first (for Docker layer caching)
COPY pyproject.toml uv.lock ./
# Install dependencies (without the project itself)
RUN uv sync --frozen --no-install-project --no-dev
# Copy bot source code and migrations
COPY src ./src
COPY alembic.ini ./
COPY README.md ./
COPY migrations ./migrations
COPY configs ./configs 
# Install the project itself
RUN uv sync --frozen --no-dev
# Entrypoint via uv to use the correct virtual environment
ENTRYPOINT ["uv", "run", "trading-bot"]
