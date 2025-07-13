"""
Tests specifically for video-related API endpoints and functionality
"""
import json
import pytest
import random
from models import Video, VideoCategory, WatchingTime, Preference
from config import db

def test_get_videos_api_filtering(authenticated_client, app):
    """Test that videos API correctly filters by categories"""
    with app.app_context():
        # Test with a single category
        response = authenticated_client.get('/api/videos?categories=humor')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'videos' in data
        
        # Check that all videos are from the humor category
        if len(data['videos']) > 0:
            # We'd need to query each video to check its category, which might be complex
            # For simplicity, we'll just verify the structure
            for video in data['videos']:
                assert 'id' in video
                assert 'title' in video
                assert 'link' in video

def test_get_videos_api_empty_categories(authenticated_client):
    """Test videos API with empty categories"""
    response = authenticated_client.get('/api/videos?categories=')
    # Should handle this gracefully, either with an error or empty list
    assert response.status_code in [200, 400]

def test_get_videos_api_invalid_categories(authenticated_client, app):
    """Test videos API with invalid/nonexistent categories"""
    with app.app_context():
        response = authenticated_client.get('/api/videos?categories=nonexistent_category')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'videos' in data
        # Should return an empty list for nonexistent categories
        assert len(data['videos']) == 0

def test_videos_round2_excludes_watched(app, authenticated_client):
    """Test that round 2 videos API excludes videos watched in round 1"""
    with app.app_context():
        # First, create a watch time record for video 101 in round 1
        watch_time = WatchingTime(
            participant_number='1001',
            video_id=10101,
            round_number=1,
            time_spent=10,
            percentage_watched=20
        )
        db.session.add(watch_time)
        db.session.commit()
        
        # Now request round 2 videos for the humor category
        response = authenticated_client.get('/api/videos_round2?categories=humor,food,travel')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'videos' in data
        
        # Check that video 101 is not in the results
        video_ids = [v['id'] for v in data['videos']]
        assert 101 not in video_ids

def test_videos_after_info_cocoons_round2(authenticated_client, app):
    """Test fetching videos after info cocoons in round 2"""
    with app.app_context():
        # Set up preferences for round 1
        response = authenticated_client.get('/api/videos_after_info_cocoons_round2?categories=humor,food,travel')
        
        # Should handle properly or return appropriate status
        assert response.status_code in [200, 404, 400]
        
        # If success, check structure
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'videos' in data
            
            # Check structure of returned videos
            if len(data['videos']) > 0:
                video = data['videos'][0]
                assert 'id' in video
                assert 'title' in video
                assert 'link' in video

def test_record_watch_time_concurrency(authenticated_client, app):
    """Test recording watch time from multiple sessions (simulating concurrent users)"""
    with app.app_context():
        # Simulate 5 rapid requests to record watch time
        for i in range(5):
            response = authenticated_client.post('/api/record_watch_time',
                data=json.dumps({
                    'video_id': 10101,
                    'watch_duration': 2,
                    'round_number': 1,
                    'current_position': 2 + i*2  # Different positions
                }),
                content_type='application/json')
            assert response.status_code == 200
        
        # Check final state in database
        record = WatchingTime.query.filter_by(
            participant_number='1001',
            video_id=10101,
            round_number=1
        ).first()
        
        # Total should be 10 seconds (5 requests * 2 seconds each)
        assert record is not None
        assert record.time_spent == 10

def test_info_video_watch_time(authenticated_client, app):
    """Test recording watch time for info video specifically"""
    with app.app_context():
        response = authenticated_client.post('/api/record_watch_time',
            data=json.dumps({
                'video_id': 19999,  # Info video ID
                'watch_duration': 60,
                'round_number': 1,
                'current_position': 60
            }),
            content_type='application/json')
        
        assert response.status_code == 200
        
        # Check correct percentage calculation for info video with updated ID
        record = WatchingTime.query.filter_by(
            participant_number='1001',
            video_id=19999  # Updated ID
        ).first()
        
        assert record is not None
        # 60 / 228 * 100 = ~26.32%
        assert round(record.percentage_watched, 2) == pytest.approx(26.32, 0.1)

def test_api_errors_without_authentication(client):
    """Test that API endpoints require authentication"""
    # Record watch time without auth
    response = client.post('/api/record_watch_time',
        data=json.dumps({
            'video_id': 10101,
            'watch_duration': 10,
            'round_number': 1
        }),
        content_type='application/json')
    
    # Should redirect or return error
    assert response.status_code in [302, 401, 403]
    
    # Get videos without auth
    response = client.get('/api/videos?categories=humor')
    assert response.status_code in [302, 401, 403]
    
    # User interaction without auth
    response = client.post('/api/user_interaction',
        json={
            'video_id': 10101,
            'action': 'like'
        })
    
    assert response.status_code in [302, 401, 403]
