FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true

# Copy requirements first to leverage Docker cache
COPY requirements.txt requirements-all.txt ./

# Install Python dependencies with error handling
RUN pip install --no-cache-dir --upgrade pip && \
    # Try to install from requirements.txt, but continue on error
    pip install --no-cache-dir -r requirements.txt || echo "Some packages could not be installed. Continuing with best effort." && \
    # Install critical packages explicitly to ensure they're available
    pip install --no-cache-dir streamlit pandas numpy matplotlib openai python-dotenv requests && \
    # Install watchdog for better performance
    pip install --no-cache-dir watchdog

# Copy the rest of the application
COPY . .

# Create a non-root user to run the application
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose the Streamlit port
EXPOSE 8501

# Set volume for database files
VOLUME ["/app/data"]

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run the Streamlit app
CMD ["streamlit", "run", "run_streamlit.py", "--server.port=8501", "--server.address=0.0.0.0"]