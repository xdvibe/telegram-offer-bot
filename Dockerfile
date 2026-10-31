FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/app/data
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 1000 --create-home bot \
    && mkdir -p /app/data && chown bot:bot /app/data
COPY main.py runtime_config.py zovteam_app_business_connected_notice_v8_fixed.py ./
USER bot
CMD ["python", "main.py"]
