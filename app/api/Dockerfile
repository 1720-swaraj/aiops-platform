# ---- Stage 1: Builder (installs dependencies into a virtual environment) ----
FROM python:3.13-slim-trixie AS builder

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: Runtime (minimal, non-root final image) ----
FROM python:3.13-slim-trixie AS runtime

# Create a non-root user and group (UID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin appuser

WORKDIR /app

# Copy ONLY the virtualenv from builder + our app code
COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appgroup main.py .

ENV PATH="/opt/venv/bin:$PATH"
USER appuser

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
