"""
Tests for utility functions in utils.py
"""
import pytest
from flask import session
from utils import validate_category_selection, participant_required, record_watch_time
from models import WatchingTime

def test_validate_category_selection():
    """Test category selection validation"""
    # Valid selection with 3 categories
    error, data = validate_category_selection({
        'rating_1': '9',
        'rating_2': '7',
        'rating_3': '5'
    })
    assert error is None
    assert len(data) == 3
    assert data[0]['category_id'] == 1
    assert data[0]['rating'] == 9
    
    # Too few categories
    error, data = validate_category_selection({
        'rating_1': '9',
        'rating_2': '7'
    })
    assert error is not None
    assert data is None
    
    # Duplicate ratings
    error, data = validate_category_selection({
        'rating_1': '9',
        'rating_2': '9',
        'rating_3': '9'
    })
    assert error is not None
    assert data is None
    
    # Ratings out of range
    error, data = validate_category_selection({
        'rating_1': '11',
        'rating_2': '7',
        'rating_3': '5'
    })
    assert error is not None
    assert data is None
    
    # Invalid category ID format
    error, data = validate_category_selection({
        'rating_invalid': '9',
        'rating_2': '7',
        'rating_3': '5'
    })
    assert error is not None
    assert data is None

def test_record_watch_time_function(app):
    """Test the record_watch_time utility function directly"""
    with app.app_context():
        # New record with updated video ID
        success, message = record_watch_time('1001', 10101, 10, 1, 10)
        assert success is True
        
        # Check record was created
        record = WatchingTime.query.filter_by(
            participant_number='1001',
            video_id=10101,
            round_number=1
        ).first()
        
        assert record is not None
        assert record.time_spent == 10
        assert record.percentage_watched == pytest.approx(22.22, 0.01)  # 10/45 * 100
        
        # Update existing record - use the same ID (10101)
        success, message = record_watch_time('1001', 10101, 5, 1, 40)
        assert success is True
        
        # Check record was updated
        record = WatchingTime.query.filter_by(
            participant_number='1001',
            video_id=10101,
            round_number=1
        ).first()
        
        assert record is not None
        assert record.time_spent == 15  # 10 + 5
        assert record.percentage_watched == pytest.approx(33.33, 0.01)  # 15/45 * 100
        
        # Test with missing parameters
        success, message = record_watch_time(None, 101, 10, 1)
        assert success is False
        
        # Test with invalid video ID
        success, message = record_watch_time('1001', 999999, 10, 1)
        assert success is False
