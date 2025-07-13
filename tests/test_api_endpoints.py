"""
Tests for API endpoints
"""
import json
import pytest
from models import VideoInteraction, WatchingTime

def test_api_record_watch_time(authenticated_client):
    """Test the record_watch_time API endpoint"""
    response = authenticated_client.post('/api/record_watch_time',
        data=json.dumps({
            'video_id': 10101,
            'watch_duration': 15,
            'round_number': 1,
            'current_position': 15
        }),
        content_type='application/json')
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'

def test_api_record_watch_time_invalid_json(authenticated_client):
    """Test record_watch_time API with invalid JSON"""
    response = authenticated_client.post('/api/record_watch_time',
        data="not valid json",
        content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'fail'

def test_api_record_watch_time_missing_data(authenticated_client):
    """Test record_watch_time API with missing required data"""
    # Missing video_id
    response = authenticated_client.post('/api/record_watch_time',
        data=json.dumps({
            'watch_duration': 15,
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
    
    # Missing round_number
    response = authenticated_client.post('/api/record_watch_time',
        data=json.dumps({
            'video_id': 10101,
            'watch_duration': 15
        }),
        content_type='application/json')
    
    assert response.status_code == 400

def test_api_get_videos(authenticated_client, app):
    """Test fetching videos API endpoint"""
    with app.app_context():
        response = authenticated_client.get('/api/videos?categories=humor,food,travel')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'videos' in data
        assert isinstance(data['videos'], list)
        
        # Should return videos from the requested categories
        if len(data['videos']) > 0:
            # Check some properties of returned videos
            video = data['videos'][0]
            assert 'id' in video
            assert 'title' in video
            assert 'link' in video

def test_api_videos_round2(authenticated_client, app):
    """Test fetching round 2 videos API endpoint"""
    with app.app_context():
        response = authenticated_client.get('/api/videos_round2?categories=humor,food,travel')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'videos' in data
        
        # Round 2 might exclude videos watched in round 1
        if len(data['videos']) > 0:
            video = data['videos'][0]
            assert 'id' in video
            assert 'title' in video
            assert 'link' in video

def test_api_user_interaction_like(authenticated_client, app):
    """Test user interaction API for like action"""
    response = authenticated_client.post('/api/user_interaction',
        json={
            'video_id': 10101,
            'action': 'like'
        })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Check database record
    with app.app_context():
        interaction = VideoInteraction.query.filter_by(
            participant_number='1001',
            video_id=10101,
            action='like'
        ).first()
        
        assert interaction is not None

def test_api_user_interaction_dislike(authenticated_client, app):
    """Test user interaction API for dislike action"""
    response = authenticated_client.post('/api/user_interaction',
        json={
            'video_id': 10101,
            'action': 'dislike'
        })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Check database record
    with app.app_context():
        interaction = VideoInteraction.query.filter_by(
            participant_number='1001',
            video_id=10101,
            action='dislike'
        ).first()
        
        assert interaction is not None
        
        # Verify that like was removed (if it existed)
        like = VideoInteraction.query.filter_by(
            participant_number='1001',
            video_id=10101,
            action='like'
        ).first()
        
        assert like is None

def test_api_user_interaction_star(authenticated_client, app):
    """Test user interaction API for star action"""
    response = authenticated_client.post('/api/user_interaction',
        json={
            'video_id': 10101,
            'action': 'star'
        })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Check database record
    with app.app_context():
        interaction = VideoInteraction.query.filter_by(
            participant_number='1001',
            video_id=10101,
            action='star'
        ).first()
        
        assert interaction is not None

def test_api_user_interaction_comment(authenticated_client, app):
    """Test user interaction API for comment action"""
    response = authenticated_client.post('/api/user_interaction',
        json={
            'video_id': 10101,
            'action': 'comment',
            'comment': 'This is a test comment'
        })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Check database record
    with app.app_context():
        interaction = VideoInteraction.query.filter_by(
            participant_number='1001',
            video_id=10101,
            action='comment'
        ).first()
        
        assert interaction is not None
        assert interaction.content == 'This is a test comment'

def test_api_user_interaction_remove_actions(authenticated_client, app):
    """Test removing user interactions"""
    # First add a like
    authenticated_client.post('/api/user_interaction',
        json={
            'video_id': 10102,
            'action': 'like'
        })
    
    # Then remove it
    response = authenticated_client.post('/api/user_interaction',
        json={
            'video_id': 10102,
            'action': 'remove_like'
        })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Check that it was removed from database
    with app.app_context():
        interaction = VideoInteraction.query.filter_by(
            participant_number='1001',
            video_id=10102,
            action='like'
        ).first()
        
        assert interaction is None

def test_api_user_interaction_invalid_action(authenticated_client):
    """Test user interaction API with invalid action"""
    response = authenticated_client.post('/api/user_interaction',
        json={
            'video_id': 10101,
            'action': 'invalid_action'
        })
    
    assert response.status_code == 400

def test_api_user_interaction_empty_comment(authenticated_client):
    """Test user interaction API with empty comment"""
    response = authenticated_client.post('/api/user_interaction',
        json={
            'video_id': 10101,
            'action': 'comment',
            'comment': '   '  # Empty or whitespace comment
        })
    
    assert response.status_code == 400
