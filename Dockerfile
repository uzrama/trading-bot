FROM python:3.13-slim
# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Setup environment variables for Python and uv
# Add /.venv/bin to PATH to execute binaries directly
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app/src \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app
# Create an unprivileged user 'appuser' and change ownership of the working directory
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app
# Switch to the unprivileged user
USER appuser
# Copy dependency files first (for Docker layer caching)
COPY --chown=appuser:appuser pyproject.toml uv.lock ./
# Install dependencies (without the project itself)
RUN uv sync --frozen --no-install-project --no-dev
# Copy bot source code and migrations
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser README.md ./
COPY --chown=appuser:appuser migrations ./migrations
COPY --chown=appuser:appuser configs ./configs 
# Install the project itself
RUN uv sync --frozen --no-dev
# Entrypoint using the direct binary path (thanks to PATH modification)
ENTRYPOINT ["trading-bot"]
