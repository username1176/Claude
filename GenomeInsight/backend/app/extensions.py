"""Shared Flask extension instances.

Instantiated here so that models, routes, and other modules can import
them without circular-import issues.  Actual init happens in the app
factory (app/__init__.py) via ``init_app()``.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

db = SQLAlchemy()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute"])
cors = CORS()
