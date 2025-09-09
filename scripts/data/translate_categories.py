# translate_categories.py

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app import app  
from models import VideoCategory, db

# Define your English to Chinese mapping
category_translations = {
    'photography': '摄影',
    'daily_vlog': '日常视频',
    'homemade_drinks': '自制饮品',
    'pets': '宠物',
    'fitness': '健身',
    'makeup': '化妆',
    'livehouse': '现场音乐',
    'popular_science': '科普',
    'street_snap': '街拍',
    'scenery': '风景',
    'dressing': '穿搭',
    'gourmet': '美食',
    'painting': '绘画',
    'hair_braided': '编发',
    'kids': '儿童'
}

with app.app_context():
    # Make sure this function is executed within an app context.
    categories = VideoCategory.query.all()
    for category in categories:
        chinese_name = category_translations.get(category.name)
        if chinese_name:
            category.name_cn = chinese_name
        else:
            category.name_cn = '未知类别'  # Unknown Category
    db.session.commit()
    print("Category names have been successfully translated.")
