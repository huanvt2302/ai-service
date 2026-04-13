FROM python:3.11-slim

WORKDIR /app

# Install gcloud CLI (needed to call `gcloud run services update`)
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl \
      gnupg \
      apt-transport-https \
    && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
       | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] \
             https://packages.cloud.google.com/apt cloud-sdk main" \
       > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get update && apt-get install -y google-cloud-cli \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY controller.py .

# The container expects GCP credentials mounted at:
#   /root/.config/gcloud  (via Swarm secret/volume)
# or set GOOGLE_APPLICATION_CREDENTIALS env var to a SA JSON file.

CMD ["python", "-u", "controller.py"]
