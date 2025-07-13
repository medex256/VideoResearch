"""
Debug script to test the endpoint
"""
import json
import pytest
import logging

def test_debug_endpoint(authenticated_client, app):
    """Test the endpoint with debug info"""
    app.logger.setLevel(logging.DEBUG)
    
    response = authenticated_client.post('/api/record_watch_time',
        data=json.dumps({
            'video_id': 10101,
            'watch_duration': 10,
            'round_number': 1,
            'current_position': 10
        }),
        content_type='application/json')
    
    # Print debug info
    print(f"Status code: {response.status_code}")
    print(f"Response data: {response.data}")
    
    # List all available routes
    print("\nAvailable routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule}")
        
    assert False  # Force failure to see the debug output
