"""
Configuration for pytest, defines fixtures and common test utilities
"""
import os
import sys
import pytest
from flask import Flask, session
import tempfile
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import app as flask_app, db
from models import Participant, Video, VideoCategory, Preference, WatchingTime

@pytest.fixture
def app():
    """Create a Flask app configured for testing"""
    # Set up testing config
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SERVER_NAME": "localhost.localdomain", 
        "SECRET_KEY": "test-key-for-testing",
        "WTF_CSRF_ENABLED": False
    })
    
    # Import the application module to ensure routes are registered
    import app as application  # This imports the app module which registers all routes
    
    # Create test context
    with flask_app.app_context():
        # Create tables
        db.create_all()
        # Set up basic test data
        _setup_test_data()
        yield flask_app
        # Clean up
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create a test CLI runner"""
    return app.test_cli_runner()

@pytest.fixture
def authenticated_client(app, client):
    """Create a test client with an authenticated session"""
    with client.session_transaction() as sess:
        sess['participant_number'] = '10001'  # Use the same high test participant number
    return client

def _setup_test_data():
    """Add basic test data to the database"""
    # Add test participant with a high ID number to avoid conflicts
    test_participant_number = '10001'  # Using a high number for test participant
    participant = Participant(participant_number=test_participant_number, group_number=1)
    db.session.add(participant)
    
    # Check if categories already exist and use them, otherwise create new ones with unique test IDs
    # Use high ID numbers (10001+) to avoid conflicts with existing data
    category_map = {}  # Maps category names to their IDs
    
    # Define test categories
    test_categories = ['humor', 'food', 'travel', 'education']
    
    for i, name in enumerate(test_categories):
        # Check if category exists
        existing = VideoCategory.query.filter_by(name=name).first()
        if existing:
            # Use existing category
            category_map[name] = existing.id
        else:
            # Create new category with high test ID
            test_id = 10001 + i
            new_category = VideoCategory(id=test_id, name=name)
            db.session.add(new_category)
            db.session.flush()  # Get the ID without full commit
            category_map[name] = test_id
    
    # Add test videos using the category IDs we have
    videos = [
        Video(id=10101, title='Funny Video 1', url='https://example.com/video1', duration=45, category_id=category_map['humor']),
        Video(id=10102, title='Food Video 1', url='https://example.com/video2', duration=60, category_id=category_map['food']),
        Video(id=10103, title='Travel Video 1', url='https://example.com/video3', duration=90, category_id=category_map['travel']),
        Video(id=10104, title='Education Video 1', url='https://example.com/video4', duration=120, category_id=category_map['education']),
        # Add an info video (using a different test ID)
        Video(id=19999, title='Info Video', url='https://example.com/info', duration=228, category_id=category_map['education']),
    ]
    
    # Add videos one by one to handle potential conflicts
    for video in videos:
        # Check if a video with this ID already exists
        if not Video.query.get(video.id):
            db.session.add(video)
    
    db.session.flush()
    
    # Add test preferences
    preferences = [
        Preference(participant_number=test_participant_number, round_number=1, category_id=category_map['humor'], rating=9),
        Preference(participant_number=test_participant_number, round_number=1, category_id=category_map['food'], rating=7),
        Preference(participant_number=test_participant_number, round_number=1, category_id=category_map['travel'], rating=5),
    ]
    db.session.bulk_save_objects(preferences)
    
    db.session.commit()
