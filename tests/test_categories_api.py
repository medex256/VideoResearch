"""
Tests for preference and category selection functionality
"""
import json
import pytest
from models import Preference, VideoCategory

def test_category_selection_validation_api(authenticated_client):
    """Test that category selection validation works correctly"""
    # Valid selection with updated category IDs
    response = authenticated_client.post('/submit_categories',
        data={
            'rating_10001': '9',
            'rating_10002': '7',
            'rating_10003': '5'
        },
        follow_redirects=True)
    
    # Should succeed and reach video viewing page
    assert response.status_code == 200
    # Check for category names in the response
    assert b'humor' in response.data
    assert b'food' in response.data
    assert b'travel' in response.data
    
    # Invalid selection (only 2 categories)
    response = authenticated_client.post('/submit_categories',
        data={
            'rating_1': '9',
            'rating_2': '7'
        },
        follow_redirects=True)
    
    # Should fail and stay on selection page or show error
    assert response.status_code == 200
    assert b'select_categories.html' in response.data or b'error' in response.data
    
    # Invalid selection (duplicate ratings)
    response = authenticated_client.post('/submit_categories',
        data={
            'rating_1': '9',
            'rating_2': '9',
            'rating_3': '9'
        },
        follow_redirects=True)
    
    # Should fail and stay on selection page or show error
    assert response.status_code == 200
    assert b'select_categories.html' in response.data or b'error' in response.data

def test_round2_category_selection(authenticated_client, app):
    """Test round 2 category selection excludes round 1 categories"""
    with app.app_context():
        # First submit round 1 preferences
        authenticated_client.post('/submit_categories',
            data={
                'rating_1': '9',  # humor
                'rating_2': '7',  # food
                'rating_3': '5'   # travel
            })
        
        # Then check round 2 selection page
        response = authenticated_client.get('/round2/select_categories')
        
        assert response.status_code == 200
        
        # Round 2 shouldn't include round 1 categories
        # This is a simple check - it's not comprehensive
        # We'd need to parse the HTML to really verify this
        html_content = response.data.decode('utf-8')
        
        # Check if any of these category names appear in the HTML
        # Note: This is a simplistic approach and might have false positives
        # A more robust approach would be to parse the HTML properly
        assert 'humor' not in html_content.lower() or 'rating_1' not in html_content
        assert 'food' not in html_content.lower() or 'rating_2' not in html_content 
        assert 'travel' not in html_content.lower() or 'rating_3' not in html_content

def test_info_cocoons_flow(authenticated_client):
    """Test the information cocoons educational flow"""
    response = authenticated_client.get('/info_cocoons')
    assert response.status_code == 200
    # The template name is not included in the HTML response
    # Instead, check for content that would be in the info_cocoons page
    assert b'info' in response.data
    assert b'cocoon' in response.data
    assert b'/round2/select_categories_after_info_cocoons' in response.data

def test_category_selection_persistence(authenticated_client, app):
    """Test that selected categories are correctly persisted across views"""
    with app.app_context():
        # Submit categories with updated category IDs
        authenticated_client.post('/submit_categories',
            data={
                'rating_10001': '9',
                'rating_10002': '7', 
                'rating_10003': '5'
            })
        
        # Check that categories are correctly passed to video viewing page
        response = authenticated_client.get('/video_viewing_1')
        assert response.status_code == 200
        
        # Get preferences from DB
        prefs = Preference.query.filter_by(
            participant_number='10001',
            round_number=1
        ).all()
        
        # Get category names
        categories = []
        for pref in prefs:
            cat = VideoCategory.query.get(pref.category_id)
            if cat:
                categories.append(cat.name)
        
        # Check if all category names appear in the response
        html_content = response.data.decode('utf-8')
        for cat_name in categories:
            assert cat_name.lower() in html_content.lower()

def test_category_preference_ratings(authenticated_client, app):
    """Test that category preference ratings are correctly stored"""
    with app.app_context():
        # Submit with specific ratings
        authenticated_client.post('/submit_categories',
            data={
                'rating_1': '10',  # Max rating for humor
                'rating_2': '5',   # Medium rating for food
                'rating_3': '1'    # Min rating for travel
            })
        
        # Verify in database
        prefs = Preference.query.filter_by(
            participant_number='10001',
            round_number=1
        ).all()
        
        # Convert to dictionary for easier lookup
        ratings = {pref.category_id: pref.rating for pref in prefs}
        
        assert ratings.get(1) == 10  # humor rating
        assert ratings.get(2) == 5   # food rating
        assert ratings.get(3) == 1   # travel rating
