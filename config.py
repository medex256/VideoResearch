import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# -----------------------------------------------------------------------------
# App setup
# -----------------------------------------------------------------------------
app = Flask(__name__)

# SECRET_KEY: use env var in prod, fallback to a dev key locally
app.secret_key = os.environ.get("SECRET_KEY", "secret-key-here")

# -----------------------------------------------------------------------------
# Database configuration
# -----------------------------------------------------------------------------
# Default to SQLite in current folder if DATABASE_URL is not set
default_sqlite = f"sqlite:///{os.path.join(os.getcwd(), 'mydatabase.db')}"
database_url = os.environ.get("DATABASE_URL", default_sqlite)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url

# Always disable modification tracking (overhead)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# If using MySQL (i.e. RDS), add a connection pool
if database_url.startswith(("mysql://", "mysql+pymysql://")):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size":      int(os.environ.get("DB_POOL_SIZE", 10)),
        "max_overflow":   int(os.environ.get("DB_MAX_OVERFLOW", 20)),
        "pool_recycle":   int(os.environ.get("DB_POOL_RECYCLE", 300)),
        "pool_pre_ping":  True,
    }

# -----------------------------------------------------------------------------
# Initialize extensions
# -----------------------------------------------------------------------------
db = SQLAlchemy(app)
migrate = Migrate(app, db)