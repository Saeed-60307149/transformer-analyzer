FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose port (container standard 5000, env PORT overrides)
EXPOSE 5000

# Run gunicorn directly (use $PORT env var)
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT:-5000}", "--workers", "1", "--timeout", "120", "wsgi:app"]
