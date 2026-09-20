FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/leadpulse

RUN groupadd --system leadpulse \
    && useradd --system --gid leadpulse --home-dir /opt/leadpulse leadpulse

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY app ./app
COPY .streamlit ./.streamlit

RUN python -m pip install --upgrade pip \
    && python -m pip install ".[dashboard]" \
    && chown -R leadpulse:leadpulse /opt/leadpulse

USER leadpulse

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"]

CMD ["python", "-m", "streamlit", "run", "app/app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
