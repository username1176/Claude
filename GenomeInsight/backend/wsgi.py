"""WSGI entry point.

Usage:
    Development:  flask run
    Production:   gunicorn wsgi:app -w 4 -b 0.0.0.0:5000
"""

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app()
