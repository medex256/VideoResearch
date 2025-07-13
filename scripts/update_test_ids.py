"""
Update video IDs in test files
"""
import os
import re

def update_test_file(file_path):
    """Updates video IDs in a test file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update video IDs (specific replacements)
    content = content.replace("'video_id': 101,", "'video_id': 10101,")
    content = content.replace("'video_id': 102,", "'video_id': 10102,")
    content = content.replace("'video_id': 103,", "'video_id': 10103,")
    content = content.replace("'video_id': 104,", "'video_id': 10104,")
    content = content.replace("'video_id': 9999,", "'video_id': 19999,")
    
    # Update references in assertions and queries
    content = content.replace("video_id=101,", "video_id=10101,")
    content = content.replace("video_id=102,", "video_id=10102,")
    content = content.replace("video_id=103,", "video_id=10103,")
    content = content.replace("video_id=104,", "video_id=10104,")
    content = content.replace("video_id=9999,", "video_id=19999,")
    
    # Update references to category IDs
    content = content.replace("category_id=1", "category_id=10001")
    content = content.replace("category_id=2", "category_id=10002")
    content = content.replace("category_id=3", "category_id=10003")
    content = content.replace("category_id=4", "category_id=10004")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    """Updates all test files"""
    tests_dir = r'c:\Users\Madi\Documents\ResearchVideo\VideoProject\NewPortal\tests'
    
    # Get all test files
    test_files = [os.path.join(tests_dir, f) for f in os.listdir(tests_dir) 
                 if f.startswith('test_') and f.endswith('.py')]
    
    # Update each file
    for file_path in test_files:
        print(f"Updating {file_path}")
        update_test_file(file_path)
    
    print("All files updated!")

if __name__ == "__main__":
    main()
