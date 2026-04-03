#!/bin/sh
exec gunicorn --bind "0.0.0.0:${PORT:-5000}" --workers 1 --timeout 120 wsgi:app
