```bash
# filepath: c:\Users\Madi\Documents\ResearchVideo\VideoProject\NewPortal\scripts\setup.sh
#!/bin/bash

echo "Starting application setup..."

# Wait for database to be ready (if using external DB)
echo "Waiting for database..."
sleep 5

# Initialize database
echo "Initializing database..."
python -c "from config import app, db; app.app_context().push(); db.create_all()"

# Load videos from Excel
echo "Loading videos to database..."
if [ -f "Douyin_videos.xlsx" ]; then
    python load_videos.py
    echo "Videos loaded successfully"
else
    echo "Warning: Douyin_videos.xlsx not found"
fi

# Update videos if replacement file exists
echo "Checking for video updates..."
if [ -f "Videos_replace.xlsx" ]; then
    python update_video.py
    echo "Video updates applied"
else
    echo "No video updates file found"
fi

# Translate categories
echo "Translating categories..."
python translate_categories.py

# Add info video
echo "Adding info video..."
python -c "
from app import app
from models import Video, db
with app.app_context():
    existing_info_video = Video.query.get(9999)
    if not existing_info_video:
        info_video = Video(
            id=9999,
            title='信息茧房介绍视频',
            url='https://www.douyin.com/video/7277534527801576704',
            duration=228,
            tags='info,education',
            likes='0',
            forwards='0'
        )
        db.session.add(info_video)
        db.session.commit()
        print('Info video added successfully')
    else:
        print('Info video already exists')
"

echo "Setup completed successfully!"
```