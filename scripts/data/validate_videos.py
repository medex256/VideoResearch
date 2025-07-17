import requests
import sqlite3
import time
import csv
import re
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config import app
from models import Video, db

def extract_video_id(url):
    """Extract numeric video ID from Douyin URL"""
    parts = url.split("/")
    possible_id = parts[-1]
    video_id = re.sub(r'\D', '', possible_id)
    return video_id

def get_cloudfront_url(video_id):
    """Convert video ID to CloudFront URL"""
    return f"https://d47xsu9sfg2co.cloudfront.net/videos/{video_id}.mp4"

def check_video(video_data):
    """Check if video exists and is accessible via CloudFront"""
    video_id, douyin_url, video_db_id = video_data
    cloudfront_url = get_cloudfront_url(video_id)
    
    try:
        # Use HEAD request to check if video exists without downloading content
        response = requests.head(cloudfront_url, timeout=10)
        
        # Get content length if available
        content_length = int(response.headers.get('Content-Length', 0)) if response.ok else 0
        content_type = response.headers.get('Content-Type', '')
        
        status = {
            'video_id': video_id,
            'douyin_url': douyin_url,
            'db_id': video_db_id,
            'cloudfront_url': cloudfront_url,
            'status_code': response.status_code,
            'content_length': content_length,
            'content_type': content_type,
            'error': None,
            'is_valid': response.ok and content_type.startswith('video/')
        }
    except requests.RequestException as e:
        status = {
            'video_id': video_id,
            'douyin_url': douyin_url,
            'db_id': video_db_id,
            'cloudfront_url': cloudfront_url,
            'status_code': None,
            'content_length': 0,
            'content_type': '',
            'error': str(e),
            'is_valid': False
        }
    
    # Print progress
    status_str = '✓' if status['is_valid'] else '✗'
    print(f"[{status_str}] Video {video_id}: {status['status_code']}")
    
    return status

def main():
    print("Starting video validation...")
    
    # Initialize results storage
    results = []
    video_count = 0
    error_count = 0
    
    # Get videos from database
    with app.app_context():
        videos = db.session.query(Video).all()
        video_data = [(extract_video_id(v.url), v.url, v.id) for v in videos]
        video_count = len(videos)
    
    print(f"Found {video_count} videos in database")
    
    # Check videos in parallel
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(check_video, video_data))
    
    # Count errors
    errors = [r for r in results if not r['is_valid']]
    error_count = len(errors)
    
    # Create directory for reports if it doesn't exist
    report_dir = os.path.join('misc', 'video_reports')
    os.makedirs(report_dir, exist_ok=True)
    
    # Write results to CSV
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    results_file = os.path.join(report_dir, f'video_validation_{timestamp}.csv')
    with open(results_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['db_id', 'video_id', 'douyin_url', 'cloudfront_url', 'status_code', 
                      'content_length', 'content_type', 'is_valid', 'error']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in sorted(results, key=lambda x: (x['is_valid'], x['video_id'])):
            writer.writerow(r)
    
    # Write errors to separate file for easy access
    if errors:
        errors_file = os.path.join(report_dir, f'video_errors_{timestamp}.csv')
        with open(errors_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['db_id', 'video_id', 'douyin_url', 'cloudfront_url', 'status_code', 
                          'content_length', 'content_type', 'is_valid', 'error']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for r in errors:
                writer.writerow(r)
    
    duration = time.time() - start_time
    print(f"\nValidation complete in {duration:.2f} seconds")
    print(f"Total videos: {video_count}")
    print(f"Valid videos: {video_count - error_count}")
    print(f"Error videos: {error_count}")
    print(f"Results saved to: {results_file}")
    if errors:
        print(f"Errors saved to: {errors_file}")
        print("\nTop errors:")
        for e in errors[:5]:
            print(f"- Video ID {e['video_id']}: {e['status_code']} {e['error'] or ''}")
    
    return results

if __name__ == '__main__':
    main()