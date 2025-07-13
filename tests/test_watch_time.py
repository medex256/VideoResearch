"""
Tests for the video watch time tracking functionality
"""
import json
import pytest
from models import WatchingTime

def test_record_watch_time_new_record(app, authenticated_client):
    """Test creating a new watch time record"""
    # Send a request to record watch time
    response = authenticated_client.post('/api/record_watch_time',
        data=json.dumps({
            'video_id': 10101,
            'watch_duration': 10,
            'round_number': 1,
            'current_position': 10
        }),
        content_type='application/json')
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    
    # Check database record
    with app.app_context():
        record = WatchingTime.query.filter_by(
            participant_number='10001',
            video_id=10101,
            round_number=1
        ).first()
        
        assert record is not None
        assert record.time_spent == 10
        assert record.percentage_watched == pytest.approx(22.22, 0.01)  # 10/45 * 100

def test_record_watch_time_update_existing(app, authenticated_client):
    """Test updating an existing watch time record"""
    # First create an initial record
    authenticated_client.post('/api/record_watch_time',
        data=json.dumps({
            'video_id': 10101,
            'watch_duration': 10,
            'round_number': 1
        }),
        content_type='application/json')
    
    # Then update it with additional time
    response = authenticated_client.post('/api/record_watch_time',
        data=json.dumps({
            'video_id': 10101,
            'watch_duration': 5,
            'round_number': 1,
            'current_position': 40  # Simulating seek to position 40
        }),
        content_type='application/json')
    
    # Check response
    assert response.status_code == 200
    
    # Check database record was updated properly
    with app.app_context():
        record = WatchingTime.query.filter_by(
            participant_number='10001',
            video_id=10101,
            round_number=1
        ).first()
        
        assert record is not None
        assert record.time_spent == 15  # 10 + 5
        assert record.percentage_watched == pytest.approx(33.33, 0.01)  # 15/45 * 100

def test_record_watch_time_info_video(app, authenticated_client):
    """Test recording watch time for the info video (ID 9999)"""
    # Send request for info video
    response = authenticated_client.post('/api/record_watch_time',
        data=json.dumps({
            'video_id': 19999,
            'watch_duration': 50,
            'round_number': 1
        }),
        content_type='application/json')
    
    # Check response
    assert response.status_code == 200
    
    # Check database record
    with app.app_context():
        record = WatchingTime.query.filter_by(
            participant_number='10001',
            video_id=19999,
            round_number=1
        ).first()
        
        assert record is not None
        assert record.time_spent == 50
        assert record.percentage_watched == pytest.approx(21.93, 0.01)  # 50/228 * 100

def test_record_watch_time_multiple_segments(app, authenticated_client):
    """Test recording multiple segments of watch time with seeking"""
    # First segment: watch first 5 seconds
    authenticated_client.post('/api/record_watch_time',
        data=json.dumps({
            'video_id': 10101,
            'watch_duration': 5,
            'round_number': 1,
            'current_position': 5
        }),
        content_type='application/json')
    
    # Second segment: after seeking to position 40, watch 5 more seconds
    response = authenticated_client.post('/api/record_watch_time',
        data=json.dumps({
            'video_id': 10101,
            'watch_duration': 5,
            'round_number': 1,
            'current_position': 45
        }),
        content_type='application/json')
    
    # Check response
    assert response.status_code == 200
    
    # Check database record - total should be 10 seconds
    with app.app_context():
        record = WatchingTime.query.filter_by(
            participant_number='10001',
            video_id=10101,
            round_number=1
        ).first()
        
        assert record is not None
        assert record.time_spent == 10  # 5 + 5
        assert record.percentage_watched == pytest.approx(22.22, 0.01)  # 10/45 * 100

def test_record_watch_time_invalid_data(authenticated_client):
    """Test handling of invalid data"""
    # Missing video_id
    response = authenticated_client.post('/api/record_watch_time',
        data=json.dumps({
            'watch_duration': 10,
            'round_number': 1
        }),
        content_type='application/json')
    
    assert response.status_code == 400
    
    # Missing watch_duration
    response = authenticated_client.post('/api/record_watch_time',
        data=json.dumps({
            'video_id': 10101,
            'round_number': 1
        }),
        content_type='application/json')
    
    assert response.status_code == 400
    
    # Invalid JSON
    response = authenticated_client.post('/api/record_watch_time',
        data="invalid json",
        content_type='application/json')
    
    assert response.status_code == 400
