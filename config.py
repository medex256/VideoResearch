"""
Application configuration management.
Centralizes all configuration settings with environment-specific options.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    uri: str
    pool_size: int = 10
    pool_timeout: int = 20
    pool_recycle: int = 3600
    echo: bool = False


@dataclass
class AppConfig:
    """Main application configuration."""
    secret_key: str
    debug: bool = False
    testing: bool = False
    host: str = "0.0.0.0"
    port: int = 5000
    
    # Video settings
    info_video_duration: int = 228  # Duration for info video (ID 9999)
    max_participant_attempts: int = 100
    
    # Validation settings
    required_category_count: int = 3
    min_rating: int = 1
    max_rating: int = 10
    
    # Group number validation
    min_group_number: int = 0
    max_group_number: int = 9


class Config:
    """Configuration factory for different environments."""
    
    @staticmethod
    def get_database_config() -> DatabaseConfig:
        """Get database configuration - simplified logic."""
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            # Production: Use provided DATABASE_URL (MySQL or other)
            print(f"[CONFIG] Using DATABASE_URL: {database_url[:50]}...")
            return DatabaseConfig(
                uri=database_url,
                pool_size=20,
                pool_timeout=30,
                pool_recycle=1800,
                echo=False
            )
        else:
            # Development: Use SQLite fallback with absolute path
            base_dir = os.path.abspath(os.path.dirname(__file__))
            instance_path = os.path.join(base_dir, 'instance')
            db_path = os.path.join(instance_path, 'mydatabase.db')
            
            # Ensure instance folder exists
            os.makedirs(instance_path, exist_ok=True)
            
            print(f"[CONFIG] Using SQLite at: {db_path}")
            return DatabaseConfig(
                uri=f'sqlite:///{db_path}',
                echo=True
            )
    
    @staticmethod
    def get_app_config() -> AppConfig:
        """Get application configuration."""
        is_production = os.environ.get('DATABASE_URL') is not None
        
        return AppConfig(
            secret_key=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
            debug=not is_production,
            testing=False
        )


# Global configuration instances - simplified
APP_CONFIG = Config.get_app_config()
DB_CONFIG = Config.get_database_config()

# Flask application setup
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = APP_CONFIG.secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = DB_CONFIG.uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Set connection pooling options based on database type
if DB_CONFIG.uri.startswith(('mysql://', 'mysql+pymysql://')):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': DB_CONFIG.pool_size,
        'pool_timeout': DB_CONFIG.pool_timeout,
        'pool_recycle': DB_CONFIG.pool_recycle,
        'echo': DB_CONFIG.echo
    }
    print("[CONFIG] MySQL connection pooling enabled")
else:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'echo': DB_CONFIG.echo
    }
    print("[CONFIG] Using SQLite (no connection pooling)")

# Database instance
db = SQLAlchemy(app)