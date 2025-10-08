FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for OpenCV and other libraries
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the API port
EXPOSE 6300

# Set environment variables
ENV FLASK_APP=clf_analysis_api.py
ENV FLASK_ENV=production
ENV PORT=6300

# Run the application
CMD ["python", "clf_analysis_api.py"]
