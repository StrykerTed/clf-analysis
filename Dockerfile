# Use NVIDIA CUDA base image with Python pre-installed
# This image includes CUDA runtime and Python 3.10
FROM nvidia/cuda:12.0.0-cudnn8-runtime-ubuntu22.04

WORKDIR /app

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    gcc \
    g++ \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for python command
RUN ln -s /usr/bin/python3 /usr/bin/python

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
