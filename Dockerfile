# Use a lightweight official Python image
FROM python:3.14-slim

# Set working directory inside the container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    POCKETBASE_URL="http://127.0.0.1:8090"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .

# Expose the application port
EXPOSE 5000

# Start Flask application using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
