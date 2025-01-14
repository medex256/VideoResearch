from flask import Flask, jsonify, render_template, redirect, url_for, request, flash, session, make_response, Response
from flask_login import LoginManager, login_user, login_required, current_user
from config import app, db
from functools import wraps
from collections import Counter
from models import Participant,VideoCategory,Video,Preference,VideoInteraction,WatchingTime




import random
import re
import json
import requests

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return Participant.query.get(user_id)

def login_required_custom(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'participant_number' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function



def generate_unique_participant_number():
    MAX_ATTEMPTS = 100
    for _ in range(MAX_ATTEMPTS):
        number = str(random.randint(0, 9999)).zfill(4)
        if not Participant.query.get(number):
            return number
    raise ValueError("无法生成唯一的参与者编号。请稍后再试。")




@app.route('/')
def index():
    return render_template('index.html')


@app.route('/start', methods=['POST'])
def start():
    try:
        participant_number = generate_unique_participant_number()
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('index'))
    group_number = random.randint(1, 7)
    participant = Participant(participant_number=participant_number, group_number=group_number)
    db.session.add(participant)
    db.session.commit()
    session['participant_number'] = participant_number
    login_user(participant)
    return redirect(url_for('select_categories'))


@app.route('/submit_categories', methods=['POST'])
@login_required_custom
def submit_categories():
    # Extract category IDs and their corresponding ratings
    selected_ids = []
    ratings = []
    
    for key, value in request.form.items():
        if key.startswith('rating_'):
            try:
                category_id = int(key.split('_')[1])
                rating = int(value)
                selected_ids.append(category_id)
                ratings.append(rating)
            except (IndexError, ValueError):
                flash('无效的类别ID或评分。', 'danger')
                return redirect(url_for('select_categories'))
    
    # Validate that exactly three categories are selected
    if len(selected_ids) != 3:
        flash('请确保选择了三个类别并为其分配评分。', 'danger')
        return redirect(url_for('select_categories'))
    
    # Validate that all ratings are between 1 and 10
    if not all(1 <= rating <= 10 for rating in ratings):
        flash('评分必须在1到10之间。', 'danger')
        return redirect(url_for('select_categories'))
    
    participant_number = session.get('participant_number')
    participant = Participant.query.get(participant_number)
    
    if participant:
        try:
            # Remove existing preferences for round 1 if any
            Preference.query.filter_by(participant_number=participant_number, round_number=1).delete()
            
            for category_id, rating in zip(selected_ids, ratings):
                preference = Preference(
                    participant_number=participant_number,
                    round_number=1,  # first round
                    category_id=category_id,
                    rating=rating
                )
                db.session.add(preference)
            db.session.commit()
            flash('类别已成功提交。', 'success')
            return redirect(url_for('next_step'))
        except Exception as e:
            db.session.rollback()
            flash('提交时发生错误，请稍后再试。', 'danger')
            return redirect(url_for('select_categories'))
    else:
        flash('参与者未找到。', 'danger')
        return redirect(url_for('index'))





@app.route('/video_viewing_1')
@login_required_custom
def next_step():
    participant_number = session.get('participant_number')
    preferences = Preference.query.filter_by(participant_number=participant_number, round_number=1).all()
    selected_categories = [pref.category.name for pref in preferences]
    return render_template('video_viewing_1.html', selected_categories=selected_categories)


"""@app.route('/proxy_video')
@login_required_custom
def proxy_video():
    original_link = request.args.get('url', '')
    if not original_link:
        return jsonify({'error': 'No URL provided.'}), 400

    # Prepare the API URL
    final_url = f"https://api.douyin.wtf/api/hybrid/video_data?url={original_link}&minimal=true"
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/112.0.0.0 Safari/537.36'
        ),
        'Accept': 'application/json',
        'Referer': 'https://www.douyin.com/',  # Include Referer if required by the API
    }

    try:
        response = requests.get(final_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        app.logger.error(f"HTTP error occurred: {http_err}")
        if response is not None:
            app.logger.error(f"Response status: {response.status_code}")
            app.logger.error(f"Response content: {response.text}")
        return jsonify({'error': 'Failed to fetch video data.'}), response.status_code if response else 500
    except Exception as err:
        app.logger.error(f"Other error occurred: {err}")
        return jsonify({'error': 'An unexpected error occurred.'}), 500

    # Assuming the API returns JSON
    try:
        data = response.json()
    except ValueError:
        app.logger.error("Response content is not valid JSON.")
        return jsonify({'error': 'Invalid response format.'}), 500

    return jsonify(data)"""



@app.route('/stream_video')
@login_required_custom
def stream_video():
    original_link = request.args.get('url', '')
    if not original_link:
        return jsonify({'error': 'No URL provided.'}), 400

    # Prepare the API URL to get the MP4 link
    final_url = f"https://api.douyin.wtf/api/hybrid/video_data?url={original_link}&minimal=true"
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/112.0.0.0 Safari/537.36'
        ),
        'Accept': 'application/json',
        #'Referer': 'https://www.douyin.com/',  # Include Referer if required by the API
    }

    app.logger.info(f"Fetching video data from: {final_url}")
    try:
        response = requests.get(final_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        app.logger.error(f"HTTP error occurred while fetching video data: {http_err}")
        if response is not None and response.text:
            app.logger.error(f"Response status: {response.status_code}")
            app.logger.error(f"Response content: {response.text}")
        return jsonify({'error': 'Failed to fetch video data.'}), response.status_code if response else 500
    except Exception as err:
        app.logger.error(f"Other error occurred while fetching video data: {err}")
        return jsonify({'error': 'An unexpected error occurred.'}), 500

    # Parse the JSON response to extract the MP4 link
    try:
        data = response.json()
    except ValueError:
        app.logger.error("Response content is not valid JSON.")
        return jsonify({'error': 'Invalid response format.'}), 500

    mp4_link = data.get('data', {}).get('video_data', {}).get('nwm_video_url')
    if not mp4_link:
        app.logger.error("No MP4 link found in the API response.")
        return jsonify({'error': 'No MP4 link found.'}), 400

    app.logger.info(f"MP4 Link extracted: {mp4_link}")

    # Fetch the actual MP4 content
    try:
        video_response = requests.get(mp4_link, headers={
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/112.0.0.0 Safari/537.36'
            ),
            'Referer': 'https://www.douyin.com/',  # Include Referer if required by the CDN
        }, stream=True)
        video_response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        app.logger.error(f"HTTP error occurred while fetching video content: {http_err}")
        app.logger.error(f"Response status: {video_response.status_code}")
        app.logger.error(f"Response content: {video_response.text}")
        return jsonify({'error': 'Failed to fetch video content.'}), video_response.status_code if video_response else 500
    except Exception as err:
        app.logger.error(f"Other error occurred while fetching video content: {err}")
        return jsonify({'error': 'An unexpected error occurred while fetching video.'}), 500

    # Generator to stream video content
    def generate():
        try:
            for chunk in video_response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        except GeneratorExit:
            video_response.close()
            app.logger.info("Client disconnected, stopping video stream.")
        except Exception as e:
            app.logger.error(f"Error while streaming video: {e}")
            video_response.close()

    # Extract filename from mp4_link
    filename = mp4_link.split('/')[-1].split('?')[0] if '/' in mp4_link else 'video.mp4'

    return Response(
        generate(),
        content_type=video_response.headers.get('Content-Type', 'video/mp4'),
        headers={
            'Access-Control-Allow-Origin': '*',
            'Content-Disposition': f'inline; filename="{filename}"',
        }
    )



@app.route('/api/user_interaction', methods=['POST'])
@login_required_custom
def user_interaction():
    data = request.get_json()
    video_id = data.get('video_id')
    action = data.get('action')        # 'like', 'dislike', 'star', 'star_remove', 'remove_like', 'remove_dislike', 'comment'
    comment_text = data.get('comment') # Text if action == 'comment'

    if not video_id or not action:
        return jsonify({'success': False, 'message': 'Missing parameters'}), 400

    participant_number = session.get('participant_number')

    # Handle 'like' and 'dislike' actions
    if action in ['like', 'dislike']:
        # Remove existing 'like' or 'dislike'
        VideoInteraction.query.filter_by(
            participant_number=participant_number,
            video_id=video_id,
            action='like'
        ).delete()
        VideoInteraction.query.filter_by(
            participant_number=participant_number,
            video_id=video_id,
            action='dislike'
        ).delete()

        # Add the new interaction
        new_interaction = VideoInteraction(
            participant_number=participant_number,
            video_id=video_id,
            action=action,
            content=''
        )
        db.session.add(new_interaction)

    # Handle 'remove_like' and 'remove_dislike' actions
    elif action in ['remove_like', 'remove_dislike']:
        target_action = action.split('_')[1]  # 'like' or 'dislike'
        interaction = VideoInteraction.query.filter_by(
            participant_number=participant_number,
            video_id=video_id,
            action=target_action
        ).first()
        if interaction:
            db.session.delete(interaction)

    # Handle 'star' and 'star_remove' actions
    elif action in ['star', 'star_remove']:
        existing_star = VideoInteraction.query.filter_by(
            participant_number=participant_number,
            video_id=video_id,
            action='star'
        ).first()
        if action == 'star':
            if not existing_star:
                # Add a new star
                new_interaction = VideoInteraction(
                    participant_number=participant_number,
                    video_id=video_id,
                    action='star',
                    content=''
                )
                db.session.add(new_interaction)
        elif action == 'star_remove':
            if existing_star:
                # Remove the existing star
                db.session.delete(existing_star)

    # Handle 'comment' action
    elif action == 'comment':
        if not comment_text.strip():
            return jsonify({'success': False, 'message': 'Comment text cannot be empty.'}), 400
        new_interaction = VideoInteraction(
            participant_number=participant_number,
            video_id=video_id,
            action=action,
            content=comment_text.strip()
        )
        db.session.add(new_interaction)

    else:
        return jsonify({'success': False, 'message': 'Invalid action.'}), 400

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Interaction recorded'}), 200
    except Exception as e:
        db.session.rollback()
        # Log the exception for debugging
        app.logger.error(f"Database error: {e}")
        return jsonify({'success': False, 'message': 'Database error'}), 500


@app.route('/api/record_watch_time', methods=['POST'])
@login_required_custom
def record_watch_time():
    try:
        # Attempt to parse JSON data manually
        data = json.loads(request.data.decode('utf-8'))
    except (TypeError, json.JSONDecodeError) as e:
        app.logger.error(f"JSON decode error: {e}")
        return jsonify({'status': 'fail', 'message': 'Invalid JSON data'}), 400

    video_id = data.get('video_id')
    watch_duration = data.get('watch_duration')
    round_number = data.get('round_number')

    # Validate incoming data
    if not video_id or watch_duration is None or round_number is None:
        return jsonify({'status': 'fail', 'message': 'Invalid data'}), 400

    participant_number = session.get('participant_number')
    if not participant_number:
        return jsonify({'status': 'fail', 'message': 'Participant not found'}), 400

    # Verify that the video exists
    video = Video.query.get(video_id)
    if not video:
        return jsonify({'status': 'fail', 'message': 'Video not found'}), 404

    # Create a new WatchingTime record
    interaction = WatchingTime(
        participant_number=participant_number,
        video_id=video_id,
        round_number=round_number,
        time_spent=watch_duration
    )

    try:
        db.session.add(interaction)
        db.session.commit()
        app.logger.info(f"Watch Time Recorded: Participant {participant_number}, Video {video_id}, Round {round_number}, Time Spent {watch_duration} seconds")
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Database error: {e}")
        return jsonify({'status': 'fail', 'message': 'Database error'}), 500




@app.route('/api/videos')
@login_required_custom
def get_videos():
    categories = request.args.get('categories')
    limit = 20  # Total number of videos
    category_names = categories.split(',')

    # Get the ratings for the selected categories
    participant_number = session.get('participant_number')
    preferences = Preference.query.filter_by(participant_number=participant_number, round_number=1).all()
    category_ratings = {pref.category.name: pref.rating for pref in preferences}

    # Total ratings sum
    total_ratings = sum(category_ratings.values())

    # Calculate number of videos per category
    videos_per_category = {}
    total_videos_assigned = 0
    for category_name in category_names:
        rating = category_ratings.get(category_name, 0)
        num_videos = round((rating / total_ratings) * limit) if total_ratings > 0 else 0
        videos_per_category[category_name] = num_videos
        total_videos_assigned += num_videos

    # Adjust if total_videos_assigned is not equal to limit due to rounding
    difference = limit - total_videos_assigned
    if difference != 0 and total_ratings > 0:
        # Adjust the category with the highest rating
        max_category = max(category_ratings, key=category_ratings.get)
        videos_per_category[max_category] += difference

    # Get category IDs
    categories = VideoCategory.query.filter(VideoCategory.name.in_(category_names)).all()
    category_ids = {cat.name: cat.id for cat in categories}

    # Collect videos
    videos_data = []
    for category_name, num_videos in videos_per_category.items():
        cat_id = category_ids.get(category_name)
        if not cat_id:
            continue
        videos_in_category = Video.query.filter_by(category_id=cat_id).all()
        if len(videos_in_category) == 0:
            continue
        selected_videos = random.sample(videos_in_category, min(num_videos, len(videos_in_category)))
        for video in selected_videos:
            # Extract video ID from the URL if necessary
            match = re.search(r'/video/(\d+)', video.url)
            if match:
                douyin_vid = match.group(1)
                embed_url = f"https://open.douyin.com/player/video?vid={douyin_vid}&autoplay=0"
                final_url = f"https://www.douyin.com/video/{douyin_vid}"
            else:
                embed_url = video.url  # Fallback if pattern doesn't match

            videos_data.append({
                'id': video.id,          # Include the database video ID
                'title': video.title,
                'link': final_url,
            })

    # Shuffle the videos
    random.shuffle(videos_data)

    return jsonify({'videos': videos_data})


@app.route('/select_categories')
@login_required_custom
def select_categories():
    categories = VideoCategory.query.all()
    return render_template('select_categories.html', categories=categories)



@app.route('/test_embed')
@login_required_custom
def test_embed():
    # Example Douyin video URL
    douyin_video_url = "https://open.douyin.com/player/video?vid=7290445158779276601&autoplay=0"
    return render_template('test_embed.html', video_url=douyin_video_url)


@app.route('/test_video')
@login_required_custom
def test_video():
    test_tiktok_id = "7376832111149468934"
    embed_url = f"https://www.tiktok.com/player/v1/{test_tiktok_id}/"
    embed_d_url = f"https://www.douyin.com/video/7290445158779276601"
    return render_template('test_video.html', original_link=embed_d_url)

if __name__ =="__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)



