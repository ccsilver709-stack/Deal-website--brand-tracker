FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for better networking
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ModelScope Studio requires port 7860
ENV PORT=7860
EXPOSE 7860

CMD ["python", "app.py"]
