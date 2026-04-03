FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port (Railway overrides with $PORT)
EXPOSE 5000

# Health check using dynamic port
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
    CMD python -c "import urllib.request, os; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT', '5000') + '/health')" || exit 1

# Run with gunicorn in production (Railway sets $PORT)
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 4 --timeout 120 wsgi:app
