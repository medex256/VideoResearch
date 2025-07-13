"""
Debug test to check info_cocoons content
"""
import json
import pytest

def test_debug_info_cocoons(authenticated_client):
    """Debugs the info_cocoons response"""
    response = authenticated_client.get('/info_cocoons')
    print("\nStatus code:", response.status_code)
    print("\nResponse data (first 200 chars):", response.data[:200])
    print("\nLooking for specific content...")
    
    # Check for various possible strings
    test_strings = [
        b'douyin', b'video', b'info', b'cocoon', 
        b'https://', b'www', b'select_categories_after_info_cocoons_round2'
    ]
    
    for s in test_strings:
        found = s in response.data
        print(f"'{s.decode()}' found: {found}")
    
    # Force failure to see output
    assert False
