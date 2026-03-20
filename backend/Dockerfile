FROM python:3.11-slim

WORKDIR /app

# Minimal system deps for a slim image
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download NLTK data to ensure stability in CI
ENV NLTK_DATA=/usr/local/nltk_data
RUN mkdir -p ${NLTK_DATA}
RUN python -m nltk.downloader -d ${NLTK_DATA} punkt punkt_tab

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
