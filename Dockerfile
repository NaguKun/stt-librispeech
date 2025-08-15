FROM python:3.8.18-slim

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install ffmpeg & dependencies for DeepSpeech
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    sox \
    libsox-fmt-all \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
