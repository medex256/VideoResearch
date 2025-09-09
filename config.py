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
    max_group_number: int = 7


class Config:
    """Configuration factory for different environments."""
    
    @staticmethod
    def get_database_config(environment: str = "development") -> DatabaseConfig:
        """Get database configuration for the specified environment."""
        if environment == "production":
            return DatabaseConfig(
                uri=os.environ.get('DATABASE_URL', 'mysql://user:password@localhost/db'),
                pool_size=20,
                pool_timeout=30,
                pool_recycle=1800,
                echo=False
            )
        elif environment == "testing":
            return DatabaseConfig(
                uri="sqlite:///:memory:",
                echo=False
            )
        else:  # development
            return DatabaseConfig(
                uri=os.environ.get('DEV_DATABASE_URL', 'sqlite:///mydatabase.db'),
                echo=True
            )
    
    @staticmethod
    def get_app_config(environment: str = "development") -> AppConfig:
        """Get application configuration for the specified environment."""
        base_config = AppConfig(
            secret_key=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
        )
        
        if environment == "production":
            base_config.debug = False
            base_config.testing = False
        elif environment == "testing":
            base_config.debug = False
            base_config.testing = True
        else:  # development
            base_config.debug = True
            base_config.testing = False
        
        return base_config


# Global configuration instances
ENVIRONMENT = os.environ.get('FLASK_ENV', 'development')
APP_CONFIG = Config.get_app_config(ENVIRONMENT)
DB_CONFIG = Config.get_database_config(ENVIRONMENT)

# Flask application setup (maintaining backward compatibility)
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = APP_CONFIG.secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = DB_CONFIG.uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Only set connection pooling options if not using SQLite
if not DB_CONFIG.uri.startswith('sqlite'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': DB_CONFIG.pool_size,
        'pool_timeout': DB_CONFIG.pool_timeout,
        'pool_recycle': DB_CONFIG.pool_recycle,
        'echo': DB_CONFIG.echo
    }
else:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'echo': DB_CONFIG.echo
    }

# Database instance
db = SQLAlchemy(app)
