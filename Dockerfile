FROM python:3.8.18-slim

WORKDIR /app

COPY requirements.txt .

# Cập nhật pip và cài đặt dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
