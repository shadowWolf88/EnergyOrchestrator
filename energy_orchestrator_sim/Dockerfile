FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Install package in development mode
RUN pip install -e .

# Expose Streamlit port (for future dashboard)
EXPOSE 8501

# Run simulation by default
CMD ["python", "main.py", "--homes", "50", "--days", "30"]
