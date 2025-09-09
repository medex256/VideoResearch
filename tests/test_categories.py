"""
Tests for category selection and preference storage functionality
"""
import json
import pytest
from models import Preference
from config import db

def test_submit_categories_success(app, authenticated_client):
    """Test successful category submission"""
    # Submit categories using the updated category IDs
    response = authenticated_client.post('/submit_categories', data={
        'rating_10002': '8',  # food
        'rating_10003': '6',  # travel
        'rating_10004': '4',  # education
    }, follow_redirects=True)
    
    # Should succeed and redirect to video viewing
    assert response.status_code == 200
    # Check for content that would be on the video viewing page
    assert b'food' in response.data
    assert b'travel' in response.data
    assert b'education' in response.data
    
    # Check database records
    with app.app_context():
        preferences = Preference.query.filter_by(
            participant_number='10001',
            round_number=1
        ).all()
        
        # Should have 3 preferences
        assert len(preferences) == 3
        
        # Check ratings
        ratings = {p.category_id: p.rating for p in preferences}
        assert ratings[10002] == 8
        assert ratings[10003] == 6
        assert ratings[10004] == 4

def test_submit_categories_validation(authenticated_client):
    """Test category submission validation"""
    # Test with too few categories
    response = authenticated_client.post('/submit_categories', data={
        'rating_1': '9',
        'rating_2': '7',
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'select_categories.html' in response.data  # Should stay on selection page
    
    # Test with invalid ratings (same rating for multiple categories)
    response = authenticated_client.post('/submit_categories', data={
        'rating_1': '9',
        'rating_2': '9',
        'rating_3': '9',
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'select_categories.html' in response.data  # Should stay on selection page

def test_submit_categories_round2(app, authenticated_client):
    """Test round 2 category submission"""
    # Submit categories for round 2 using the updated category IDs
    response = authenticated_client.post('/round2/submit_categories', data={
        'rating_10001': '8',  # humor - already selected in round 1
        'rating_10002': '6',  # food - already selected in round 1
        'rating_10004': '4',  # education - not selected in round 1
    }, follow_redirects=True)
    
    # Should succeed and redirect to video viewing
    assert response.status_code == 200
    # Check for content that would be on the video viewing page
    assert b'humor' in response.data
    assert b'food' in response.data
    assert b'education' in response.data
    
    # Check database records
    with app.app_context():
        preferences = Preference.query.filter_by(
            participant_number='10001',
            round_number=2
        ).all()
        
        # Should have 3 preferences
        assert len(preferences) == 3
        
        # Check ratings
        ratings = {p.category_id: p.rating for p in preferences}
        assert ratings[10001] == 8
        assert ratings[10002] == 6
        assert ratings[10004] == 4

def test_save_preferences_helper(app):
    """Test the save_preferences helper function directly"""
    from utils import save_preferences
    
    with app.app_context():
        # Clear any existing round 2 preferences
        Preference.query.filter_by(
            participant_number='10001',
            round_number=2
        ).delete()
        db.session.commit()
        
        # Save new preferences
        preferences_data = [
            {'category_id': 2, 'rating': 9},
            {'category_id': 3, 'rating': 7},
            {'category_id': 4, 'rating': 5}
        ]
        
        result = save_preferences('10001', 2, preferences_data)
        assert result is True
        
        # Check database records
        preferences = Preference.query.filter_by(
            participant_number='10001',
            round_number=2
        ).all()
        
        # Should have 3 preferences
        assert len(preferences) == 3
        
        # Check ratings
        ratings = {p.category_id: p.rating for p in preferences}
        assert ratings[2] == 9
        assert ratings[3] == 7
        assert ratings[4] == 5
