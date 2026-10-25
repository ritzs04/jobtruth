FROM python:3.12-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY public public
RUN useradd -m appuser && mkdir -p /data && chown appuser:appuser /data
ENV JOBTRUTH_DB_PATH=/data/jobtruth.db
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
