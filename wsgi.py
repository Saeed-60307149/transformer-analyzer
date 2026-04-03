"""WSGI entry point for production deployment."""
from app.main import create_app

app = create_app()
