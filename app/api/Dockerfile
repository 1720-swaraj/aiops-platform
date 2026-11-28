# ---- Stage 1: Builder (installs dependencies into a virtual environment) ----
FROM python:3.13-slim-trixie AS builder

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: Runtime (minimal, non-root final image) ----
FROM python:3.13-slim-trixie AS runtime

RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user and group (UID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin appuser

WORKDIR /app

# Copy ONLY the virtualenv from builder + our app code
COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appgroup main.py .

ENV PATH="/opt/venv/bin:$PATH"
# Remove packaging tools and bundled wheels not needed at runtime
RUN rm -rf \
    /opt/venv/lib/python*/site-packages/pip* \
    /opt/venv/lib/python*/site-packages/setuptools* \
    /opt/venv/bin/pip* \
    /usr/local/lib/python*/site-packages/pip* \
    /usr/local/lib/python*/site-packages/setuptools* \
    /usr/local/lib/python*/ensurepip \
    /usr/local/bin/pip*
USER appuser

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
