FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY main.py .

EXPOSE 8888

# Run with a single worker — routing decisions are async, no need for multi-process
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8888", \
     "--workers", "1", "--loop", "uvloop", "--log-level", "info"]
