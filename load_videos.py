# load_videos.py

from config import app, db
from models import Video, VideoCategory
import pandas as pd

def load_videos_from_excel(file_path):
    df = pd.read_excel(file_path)
    
    # Ensure the DataFrame has the necessary columns
    required_columns = {'title', 'link', 'category', 'id', 'duration', 'Tags', 'Likes', 'Forward'}
    if not required_columns.issubset(df.columns):
        print(f"The Excel file must contain the following columns: {required_columns}")
        return

    with app.app_context():
        # Create a mapping from category names to IDs
        category_mapping = {category.name: category.id for category in VideoCategory.query.all()}
        
        # Check for new categories and add them
        excel_categories = set(df['category'].unique())
        new_categories = excel_categories - set(category_mapping.keys())
        for category_name in new_categories:
            new_category = VideoCategory(name=category_name)
            db.session.add(new_category)
        db.session.commit()
        # Refresh the category mapping after adding new categories
        category_mapping = {category.name: category.id for category in VideoCategory.query.all()}

        videos_to_add = []
        for index, row in df.iterrows():
            category_name = row['category']
            title = row['title']
            url = row['link']
            duration = row['duration']
            tags = row['Tags']
            likes = row['Likes']
            forwards = row['Forward']

            # Get the category ID from the mapping
            category_id = category_mapping.get(category_name)
            if not category_id:
                print(f"Category '{category_name}' not found in the database.")
                continue

            # Create a new Video object
            video = Video(
                category_id=category_id,
                title=title,
                url=url,
                duration=duration,
                tags=tags,
                likes=likes,
                forwards=forwards
            )
            videos_to_add.append(video)

        db.session.bulk_save_objects(videos_to_add)
        db.session.commit()
        print(f"Successfully added {len(videos_to_add)} videos to the database.")

if __name__ == '__main__':
    file_path = 'Douyin_videos.xlsx'
    load_videos_from_excel(file_path)