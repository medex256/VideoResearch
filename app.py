from flask import Flask, jsonify, render_template, redirect, url_for, request, flash, session, make_response, Response
from flask_login import LoginManager, login_user, login_required, current_user
from config import app, db
from functools import wraps
from collections import Counter
from models import Participant,VideoCategory,Video,Preference,VideoInteraction,WatchingTime,CopingStrategy,ConsistencyAnswer,MessageTime


from load_videos import load_videos_from_excel  # ensure load_videos.py defines a load_videos() function



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
            flash('无效的会话。', 'danger')
            return redirect(url_for('show_intro', group_number=1))
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
def home():
    return "Hello, PythonAnywhere!"




@app.route('/intro/<int:group_number>')
def show_intro(group_number):
    if group_number < 1 or group_number > 7:
        flash('无效组别编号。', 'danger')
        # Fallback to group_number=1 instead of "index"
        return redirect(url_for('show_intro', group_number=1))
    return render_template('index.html', group_number=group_number)


@app.route('/initial_selection/<int:group_number>', methods=['GET', 'POST'])
def initial_selection(group_number):
    if group_number < 1 or group_number > 7:
        flash('无效组别编号。', 'danger')
        redirect(url_for('show_intro', group_number=1))
    try:
        participant_number = generate_unique_participant_number()
    except ValueError as e:
        flash(str(e), 'danger')
        redirect(url_for('show_intro', group_number=1))

    participant = Participant(participant_number=participant_number, group_number=group_number)
    db.session.add(participant)
    db.session.commit()
    session['participant_number'] = participant_number
    login_user(participant)

    # Redirect to category selection or wherever you need next
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
    

    if len(set(ratings)) < 3:
        flash('请给三个视频不同的评分，不能有重复。', 'danger')
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
        return redirect(url_for('show_intro', group_number=1))





@app.route('/video_viewing_1')
@login_required_custom
def next_step():
    participant_number = session.get('participant_number')
    preferences = Preference.query.filter_by(participant_number=participant_number, round_number=1).all()
    selected_categories = [pref.category.name for pref in preferences]
    return render_template('video_viewing_1.html', selected_categories=selected_categories)



@app.route('/end_video_viewing_1')
@login_required_custom
def end_video_viewing_1():
    participant_number = session.get('participant_number')
    participant = Participant.query.get(participant_number)
    if not participant:
        flash('参与者未找到。', 'danger')
        redirect(url_for('show_intro', group_number=1))
    return redirect(url_for('additional_information'))



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
        #'Referer': 'https://www.douyin.com/',  
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
            'Referer': 'https://www.douyin.com/',  
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

    elif action in ['remove_like', 'remove_dislike']:
        target_action = action.split('_')[1]  # 'like' or 'dislike'
        interaction = VideoInteraction.query.filter_by(
            participant_number=participant_number,
            video_id=video_id,
            action=target_action
        ).first()
        if interaction:
            db.session.delete(interaction)

    #'star' and 'star_remove' actions
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
    
    if video_id!=9999:
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




"""@app.route('/api/videos')
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

    return jsonify({'videos': videos_data})"""


@app.route('/api/videos')
@login_required_custom
def get_videos():
    # Previously limit = 20
    # We now directly select 5 videos per category (3 categories × 5 = 15):
    categories = request.args.get('categories')
    category_names = categories.split(',')

    videos_data = []
    for category_name in category_names:
        cat_obj = VideoCategory.query.filter_by(name=category_name).first()
        if not cat_obj:
            continue
        videos_in_category = Video.query.filter_by(category_id=cat_obj.id).all()
        selected_videos = random.sample(videos_in_category, min(5, len(videos_in_category)))
        for video in selected_videos:
            videos_data.append({
                'id': video.id,
                'title': video.title,
                'link': video.url,
            })

    # Shuffle the videos
    random.shuffle(videos_data)

    return jsonify({'videos': videos_data})


@app.route('/select_categories')
@login_required_custom
def select_categories():
    categories = VideoCategory.query.filter(VideoCategory.name != 'info').all()
    return render_template('select_categories.html', categories=categories)



@app.route('/coping_strategy', methods=['GET', 'POST'])
@login_required_custom
def coping_strategy():
    if request.method == 'POST':
        chosen_strategy = request.form.get('strategy')
        participant_number = session.get('participant_number')
        if not participant_number:
            flash('未找到参与者信息。', 'danger')
            return redirect(url_for('index'))

        # Record user’s chosen strategy
        new_strategy = CopingStrategy(
            participant_number=participant_number,
            strategy=chosen_strategy
        )
        db.session.add(new_strategy)
        db.session.commit()

        # Redirect based on strategy
        if chosen_strategy == 'watch_other':
            # Exclude previously chosen categories and let user pick again
            return redirect(url_for('select_categories_round2'))
        elif chosen_strategy == 'learn_more':
            return redirect(url_for('info_cocoons'))
        else:
            # 'avoidance' -> watch same categories
            return redirect(url_for('continue_same_categories'))    

    return render_template('coping_strategy.html')





@app.route('/select_categories_round2', methods=['GET'])
@login_required_custom
def select_categories_round2():
    participant_number = session.get('participant_number')
    if not participant_number:
        flash('未找到参与者信息。', 'danger')
        redirect(url_for('show_intro', group_number=1))
    
    # Get already selected categories from round 1
    selected_round1 = Preference.query.filter_by(participant_number=participant_number, round_number=1).all()
    selected_round1_ids = [pref.category_id for pref in selected_round1]
    
    # Get remaining categories excluding round 1 selections
    remaining_categories = VideoCategory.query.filter(
        VideoCategory.name != 'info',
        ~VideoCategory.id.in_(selected_round1_ids)
    ).all()
    
    return render_template('select_categories_round2.html', categories=remaining_categories)

@app.route('/submit_categories_round2', methods=['POST'])
@login_required_custom
def submit_categories_round2():
    participant_number = session.get('participant_number')
    if not participant_number:
        flash('未找到参与者信息。', 'danger')
        return redirect(url_for('show_intro', group_number=1))
    
    # Extract category ratings from form
    selected_ids = []
    ratings = []
    
    for key, value in request.form.items():
        if key.startswith('rating_'):
            try:
                category_id = int(key.split('_')[1])
                rating = int(value)
                if rating > 0:
                    selected_ids.append(category_id)
                    ratings.append(rating)
            except (IndexError, ValueError):
                flash('无效的类别ID或评分。', 'danger')
                return redirect(url_for('select_categories_round2'))
    
    # Validate that exactly three categories are selected
    if len(selected_ids) != 3:
        flash('请确保选择了三个类别并为其分配评分。', 'danger')
        return redirect(url_for('select_categories_round2'))
    
    # Validate that all ratings are between 1 and 10
    if not all(1 <= rating <= 10 for rating in ratings):
        flash('评分必须在1到10之间。', 'danger')
        return redirect(url_for('select_categories_round2'))
    
    try:
        # Remove existing preferences for round 2 if any
        Preference.query.filter_by(participant_number=participant_number, round_number=2).delete()
        
        for category_id, rating in zip(selected_ids, ratings):
            preference = Preference(
                participant_number=participant_number,
                round_number=2,  # Second round
                category_id=category_id,
                rating=rating
            )
            db.session.add(preference)
        db.session.commit()
        flash('第二轮类别已成功提交。', 'success')
        return redirect(url_for('video_viewing_2'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in submit_categories_round2: {e}")
        flash('提交时发生错误，请稍后再试。', 'danger')
        return redirect(url_for('select_categories_round2'))



@app.route('/video_viewing_2')
@login_required_custom
def video_viewing_2():
    participant_number = session.get('participant_number')
    preferences_round2 = Preference.query.filter_by(participant_number=participant_number, round_number=2).all()
    selected_categories = [pref.category.name for pref in preferences_round2]
    return render_template('video_viewing_2.html', selected_categories=selected_categories)



@app.route('/api/videos_round2')
@login_required_custom
def get_videos_round2():
    categories = request.args.get('categories')
    limit = 3  # Total number of videos (one from each category)
    category_names = categories.split(',')

    participant_number = session.get('participant_number')
    if not participant_number:
        return jsonify({'error': 'Participant not found.'}), 400

    # Ensure that selected categories are exactly 3
    if len(category_names) != 3:
        return jsonify({'error': 'Exactly three categories must be selected.'}), 400

    # Get category IDs
    categories = VideoCategory.query.filter(VideoCategory.name.in_(category_names)).all()
    category_ids = {cat.name: cat.id for cat in categories}

    videos_data = []
    for category_name in category_names:
        cat_id = category_ids.get(category_name)
        if not cat_id:
            continue
        # Exclude videos already watched in round 1
        watched_videos_round1 = WatchingTime.query.join(Video).filter(
            WatchingTime.participant_number == participant_number,
            WatchingTime.round_number == 1,
            Video.category_id == cat_id
        ).with_entities(Video.id).all()
        watched_video_ids = [vid.id for vid in watched_videos_round1]

        videos_query = Video.query.filter_by(category_id=cat_id).filter(~Video.id.in_(watched_video_ids)).all()
        if not videos_query:
            # If all videos have been watched, allow repeats or handle accordingly
            videos_query = Video.query.filter_by(category_id=cat_id).all()

        if len(videos_query) == 0:
            continue

        selected_video = random.choice(videos_query)
        videos_data.append({
            'id': selected_video.id,
            'title': selected_video.title,
            'link': selected_video.url,
        })

    return jsonify({'videos': videos_data})


@app.route('/end_video_viewing_2')
@login_required_custom
def end_video_viewing_2():
    flash('感谢您的参与！', 'success')
    return redirect(url_for('end_study'))



@app.route('/info_cocoons')
@login_required_custom 
def info_cocoons():
    video_link = "https://www.douyin.com/video/7277534527801576704"
    return render_template('info_cocoons.html', video_link=video_link)


@app.route('/continue_same_categories')
@login_required_custom
def continue_same_categories():
    participant_number = session.get('participant_number')
    if not participant_number:
        return redirect(url_for('show_intro', group_number=1))

    # Fetch the participant’s initial category preferences
    prefs_round1 = Preference.query.filter_by(participant_number=participant_number, round_number=1).all()
    if len(prefs_round1) != 3:
        flash('尚未完成初次类别选择。', 'danger')
        return redirect(url_for('select_categories'))

    selected_categories = [pref.category.name for pref in prefs_round1]
    chosen_videos = []
    for pref in prefs_round1:
        # Exclude previously watched videos
        watched_videos = WatchingTime.query.join(Video).filter(
            WatchingTime.participant_number == participant_number,
            WatchingTime.round_number == 1,
            Video.category_id == pref.category_id
        ).with_entities(Video.id).all()
        watched_ids = [x.id for x in watched_videos]
        video_query = Video.query.filter_by(category_id=pref.category_id).filter(
            ~Video.id.in_(watched_ids)
        ).all()
        if not video_query:
            # If no unwatched videos remain, allow repeats or handle accordingly
            video_query = Video.query.filter_by(category_id=pref.category_id).all()
        if video_query:
            video = random.choice(video_query)
            chosen_videos.append({
                'id': video.id,
                'title': video.title,
                'link': video.url,
            })

    return render_template('continue_same_categories.html', videos=chosen_videos, selected_categories=selected_categories)





@app.route('/add_info_video')
def add_info_video():
    # Check if 'info' category already exists
    info_cat = VideoCategory.query.filter_by(name='info').first()
    if not info_cat:
        info_cat = VideoCategory(
            name='info',
            name_cn='信息视频',
        )
        db.session.add(info_cat)
        db.session.commit()

    # Check if the video already exists
    existing_video = Video.query.filter_by(url='https://www.douyin.com/video/7277534527801576704').first()
    if not existing_video:
        info_video = Video(
            title='信息茧房介绍',
            url='https://www.douyin.com/video/7277534527801576704',
            category_id=info_cat.id
        )
        db.session.add(info_video)
        db.session.commit()

    return 'Info video added successfully.'





@app.route('/select_categories_after_info_cocoons_round2', methods=['GET'])
@login_required_custom
def select_categories_after_info_cocoons_round2():
    participant_number = session.get('participant_number')
    if not participant_number:
        flash('未找到参与者信息。', 'danger')
        return redirect(url_for('show_intro', group_number=1))
    
    # simply allow selection from all categories again if that's the requirement
    remaining_categories = VideoCategory.query.filter(VideoCategory.name != 'info').all()
    
    return render_template('select_categories_after_info_cocoons_round2.html', categories=remaining_categories)





@app.route('/submit_categories_after_info_cocoons_round2', methods=['POST'])
@login_required_custom
def submit_categories_after_info_cocoons_round2():
    participant_number = session.get('participant_number')
    if not participant_number:
        flash('未找到参与者信息。', 'danger')
        return redirect(url_for('show_intro', group_number=1))
    
    selected_ids = []
    ratings = []
    
    for key, value in request.form.items():
        if key.startswith('rating_'):
            try:
                category_id = int(key.split('_')[1])
                rating = int(value)
                if rating > 0:
                    selected_ids.append(category_id)
                    ratings.append(rating)
            except (IndexError, ValueError):
                flash('无效的类别ID或评分。', 'danger')
                return redirect(url_for('select_categories_after_info_cocoons_round2'))
    
    if len(selected_ids) != 3:
        flash('请确保选择了三个类别并为其分配评分。', 'danger')
        return redirect(url_for('select_categories_after_info_cocoons_round2'))
    
    if not all(1 <= rating <= 10 for rating in ratings):
        flash('评分必须在1到10之间。', 'danger')
        return redirect(url_for('select_categories_after_info_cocoons_round2'))
    
    try:
        Preference.query.filter_by(participant_number=participant_number, round_number=2).delete()
        for category_id, rating in zip(selected_ids, ratings):
            preference = Preference(
                participant_number=participant_number,
                round_number=2,
                category_id=category_id,
                rating=rating
            )
            db.session.add(preference)
        db.session.commit()
        flash('第二次信息视频后类别选择已成功提交。', 'success')
        return redirect(url_for('video_viewing_after_info_cocoons_2'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in submit_categories_after_info_cocoons_round2: {e}")
        flash('提交时发生错误，请稍后再试。', 'danger')
        return redirect(url_for('select_categories_after_info_cocoons_round2'))
    



@app.route('/video_viewing_after_info_cocoons_2')
@login_required_custom
def video_viewing_after_info_cocoons_2():
    participant_number = session.get('participant_number')
    preferences_after_info = Preference.query.filter_by(participant_number=participant_number, round_number=2).all()
    selected_categories = [pref.category.name for pref in preferences_after_info]
    return render_template('video_viewing_after_info_cocoons_2.html', selected_categories=selected_categories)


@app.route('/api/videos_after_info_cocoons_round2')
@login_required_custom
def get_videos_after_info_cocoons_round2():
    categories = request.args.get('categories')
    limit = 3  # 3 videos total
    category_names = categories.split(',')

    participant_number = session.get('participant_number')
    if not participant_number:
        return jsonify({'error': 'Participant not found.'}), 400

    if len(category_names) != 3:
        return jsonify({'error': 'Exactly three categories must be selected.'}), 400

    cat_objs = VideoCategory.query.filter(VideoCategory.name.in_(category_names)).all()
    category_ids = {cat.name: cat.id for cat in cat_objs}

    videos_data = []
    for category_name in category_names:
        cat_id = category_ids.get(category_name)
        if not cat_id:
            continue
        watched_videos_round1 = WatchingTime.query.join(Video).filter(
            WatchingTime.participant_number == participant_number,
            WatchingTime.round_number == 1,  # Exclude previously watched, if desired
            Video.category_id == cat_id
        ).with_entities(Video.id).all()
        watched_ids = [vid.id for vid in watched_videos_round1]
        possible_videos = Video.query.filter_by(category_id=cat_id).filter(~Video.id.in_(watched_ids)).all()
        if not possible_videos:
            # Fallback if user watched all
            possible_videos = Video.query.filter_by(category_id=cat_id).all()

        selected_video = random.choice(possible_videos) if possible_videos else None
        if selected_video:
            videos_data.append({
                'id': selected_video.id,
                'title': selected_video.title,
                'link': selected_video.url,
            })

    return jsonify({'videos': videos_data})



@app.route('/additional_information', methods=['GET', 'POST'])
@login_required_custom
def additional_information():
    participant_number = session.get('participant_number')
    participant = Participant.query.get(participant_number)
    if not participant:
        flash('参与者未找到。', 'danger')
        return redirect(url_for('show_intro', group_number=1))

    group_num = participant.group_number

    # Example Chinese messages for each treatment group (2..7).
    # Adjust them as needed.
    group_messages = {
        1: "【！！系统检测到您已经浏览了大量同质化的视频内容。\n长期暴露于同质化的信息被证实能够强化人们的认知偏差和思维局限，甚至会导致偏激的思想和行为。\n为了避免信息茧房危害，我们建议您观看多样化的视频内容。】",
        2: "【！！系统检测到您已经浏览了大量同质化的视频内容。\n长期暴露于同质化的信息被证实能够强化人们的认知偏差和思维局限，甚至会导致偏激的思想和行为。\n我们十分理解并认同您对某一类视频的喜爱，我们同样希望您能通过浏览短视频获得充分的放松和愉悦。但为了避免信息茧房对您造成危害，我们建议您观看多样化的视频内容。】",
        3: "【！！系统检测到您已经浏览了大量同质化的视频内容。\n长期暴露于同质化的信息被证实能够强化人们的认知偏差和思维局限，甚至会导致偏激的思想和行为。\n作为信息行为研究者，我们一直致力于提高人们的信息茧房风险意识并帮助其远离信息茧房危害。为了协助我们降低信息茧房对您可能造成的危害，我们建议您观看多样化的视频内容。】",
        4: "【！！系统检测到您已经浏览了大量同质化的视频内容。\n长期暴露于同质化的信息被证实能够强化人们的认知偏差和思维局限，甚至会导致偏激的思想和行为。\n85%的短视频平台用户在得知信息茧房风险之后都选择观看不同类型的视频来缓解信息茧房可能带来的危害，我们建议您也这样做。】",
        5: "【！！系统检测到您已经浏览了大量同质化的视频内容。\n长期暴露于同质化的信息被证实能够强化人们的认知偏差和思维局限，甚至会导致偏激的思想和行为。\n请问您在多大程度上同意信息茧房可能对您造成上述危害（0表示完全不同意，10表示完全同意）：\n\n\n请问您在多大程度上同意观看多种类型的视频是保护自己远离信息茧房的有效手段：（0表示完全不同意，10表示完全同意）：\n\n\n为了避免信息茧房对您造成危害，我们建议您观看多样化的视频内容。】",
        6: "【！！系统检测到您已经浏览了大量同质化的视频内容。\n长期暴露于同质化的信息被证实能够强化人们的认知偏差和思维局限，甚至会导致偏激的思想和行为。\n哈佛大学法学院Sunstein教授在其著作中深刻阐明了信息茧房的危害并强调了多样化信息在缓解信息茧房中的重要作用(来源：https://hls.harvard.edu/today/danger-internet-echo-chamber/)。为了避免信息茧房对您造成危害，我们建议您观看多样化的视频内容。】",
        7: "【！！系统检测到您已经浏览了大量同质化的视频内容。\n长期暴露于同质化的信息被证实能够强化人们的认知偏差和思维局限，甚至会导致偏激的思想和行为。\n此次实验是帮助您认识信息茧房风险并主动跳出信息茧房的难得机会，我们建议您观看多样化的视频内容。】",
    }

    if request.method == 'POST':
        time_spent_str = request.form.get('timeSpent', '0')
        try:
            time_spent = float(time_spent_str)
            if time_spent > 0:
                msg_record = MessageTime(
                    participant_number=participant_number,
                    time_spent=time_spent
                )
                db.session.add(msg_record)
                db.session.commit()
        except ValueError:
            pass

        if group_num == 5:
            q1 = request.form.get('q1')
            q2 = request.form.get('q2')
            if q1 is not None and q2 is not None:
                db.session.add(ConsistencyAnswer(
                    participant_number=participant_number,
                    question_number=1,
                    answer=int(q1)
                ))
                db.session.add(ConsistencyAnswer(
                    participant_number=participant_number,
                    question_number=2,
                    answer=int(q2)
                ))
                db.session.commit()
        
        chosen_strategy = request.form.get('strategy')
        if chosen_strategy:
            # Record user's chosen strategy
            new_strategy = CopingStrategy(
                participant_number=participant_number,
                strategy=chosen_strategy
            )
            db.session.add(new_strategy)
            db.session.commit()

            # Redirect based on strategy
            if chosen_strategy == 'watch_other':
                # Exclude previously chosen categories and let user pick again
                return redirect(url_for('select_categories_round2'))
            elif chosen_strategy == 'learn_more':
                return redirect(url_for('info_cocoons'))
            else:
                # 'avoidance' -> watch same categories
                return redirect(url_for('continue_same_categories'))    

        # If no strategy selected (fallback), redirect to coping_strategy page
        return redirect(url_for('coping_strategy'))
    return render_template('additional_information.html',
                           message=group_messages.get(group_num, ''),
                           group_num=group_num)



@app.route('/end_study')
@login_required_custom
def end_study():
    participant_number = session.get('participant_number')
    return render_template('end_study.html', participant_number=participant_number)

@app.route('/test_embed')
@login_required_custom
def test_embed():
    # Example Douyin video URL
    douyin_video_url = "https://open.douyin.com/player/video?vid=7290445158779276601&autoplay=0"
    return render_template('test_embed.html', video_url=douyin_video_url)


@app.route('/test_video')
def test_video():
    return render_template('test_video.html')

if __name__ =="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)



