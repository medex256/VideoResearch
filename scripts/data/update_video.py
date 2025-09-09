import pandas as pd
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config import app, db
from models import Video
import os
import sys

def update_videos_from_excel():
    """Update video records with new data from the Excel file."""
    print("Starting video update process...")
    
    # Path to the Excel file
    excel_path = os.path.join(os.path.dirname(__file__), 'Videos_replace.xlsx')
    
    if not os.path.exists(excel_path):
        print(f"Excel file not found: {excel_path}")
        return False
    
    try:
        # Read the Excel file
        df = pd.read_excel(excel_path)
        print(f"Successfully read Excel file with {len(df)} rows")
        
        # Process each row in the Excel file
        updated_count = 0
        not_found_count = 0
        error_count = 0
        
        with app.app_context():
            for index, row in df.iterrows():
                try:
                    # Extract video information from Excel row
                    video_id = int(row['id']) if 'id' in row and pd.notna(row['id']) else None
                    title = row['title'] if 'title' in row and pd.notna(row['title']) else None
                    url = row['link'] if 'link' in row and pd.notna(row['link']) else None
                    
                    # Find the video by title or ID
                    video = None
                    if title:
                        video = Video.query.filter_by(title=title).first()
                    if not video and url:
                        video = Video.query.filter_by(url=url).first()
                    if not video and video_id:
                        video = Video.query.filter_by(id=video_id).first()
                    
                    if not video:
                        print(f"Row {index+2}: Video not found with title='{title}', url='{url}'")
                        not_found_count += 1
                        continue
                    
                    # Update video fields if present in the Excel
                    if 'id' in row and pd.notna(row['id']):
                        video.id = int(row['id'])
                    if 'link' in row and pd.notna(row['link']):
                        video.url = row['link']
                    if 'duration' in row and pd.notna(row['duration']):
                        video.duration = int(row['duration'])
                    if 'tags' in row and pd.notna(row['tags']):
                        video.tags = row['tags']
                    if 'likes' in row and pd.notna(row['likes']):
                        video.likes = row['likes']
                    if 'forwards' in row and pd.notna(row['forwards']):
                        video.forwards = row['forwards']
                    
                    # Commit the changes
                    db.session.commit()
                    print(f"Row {index+2}: Updated video '{video.title}' (ID: {video.id})")
                    updated_count += 1
                    
                except Exception as e:
                    print(f"Row {index+2}: Error updating video: {str(e)}")
                    db.session.rollback()
                    error_count += 1
        
        # Print summary
        print("\nUpdate Summary:")
        print(f"Total records in Excel: {len(df)}")
        print(f"Successfully updated: {updated_count}")
        print(f"Not found in database: {not_found_count}")
        print(f"Errors: {error_count}")
        
        return error_count == 0
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    success = update_videos_from_excel()
    sys.exit(0 if success else 1) #trig
