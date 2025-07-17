from flask import Flask, jsonify, render_template, redirect, url_for, request, flash, session, make_response, Response, current_app
from flask_login import LoginManager, login_user, login_required, current_user
from config import app, db
from functools import wraps
from collections import Counter
import random
import json
from models import Participant,VideoCategory,Video,Preference,VideoInteraction,WatchingTime,CopingStrategy,ConsistencyAnswer,MessageTime
from utils import (participant_required, db_handler, validate_category_selection, 
                  save_preferences, record_watch_time, generate_unique_participant_number, 
                  get_videos_for_categories, get_route_with_participant_check, GROUP_MESSAGES,
                  validate_group_number, get_categories_excluding_info, create_json_response,
                  validate_api_request_data, parse_request_json)
from services import (VideoInteractionService, VideoSelectionService, ParticipantService, 
                     AdditionalInfoService, StrategyRedirectService)

from load_videos import load_videos_from_excel  # ensure load_videos.py defines a load_videos() function



login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return Participant.query.get(user_id)



@app.route('/')
def home():
    return "Hello, PythonAnywhere!"


@app.route('/intro/<int:group_number>')
def show_intro(group_number):
    if not validate_group_number(group_number):
        flash('无效组别编号。', 'danger')
        return redirect(url_for('show_intro', group_number=1))
    return render_template('index.html', group_number=group_number)


@app.route('/initial_selection/<int:group_number>', methods=['GET', 'POST'])
def initial_selection(group_number):
    if not validate_group_number(group_number):
        flash('无效组别编号。', 'danger')
        return redirect(url_for('show_intro', group_number=1))
    
    try:
        participant_number = generate_unique_participant_number()
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('show_intro', group_number=1))

    participant = Participant(participant_number=participant_number, group_number=group_number)
    db.session.add(participant)
    db.session.commit()
    session['participant_number'] = participant_number
    login_user(participant)

    return redirect(url_for('select_categories'))


@app.route('/submit_categories', methods=['POST'])
@participant_required
def submit_categories(participant):
    # Use validation helper from utils
    error_msg, validated_data = validate_category_selection(request.form)
    if error_msg:
        flash(error_msg, 'danger')
        return redirect(url_for('select_categories'))
    
    # Use save_preferences helper (which uses db_handler internally)
    if save_preferences(participant.participant_number, 1, validated_data):
        flash('第一轮类别已成功提交。', 'success')
        return redirect(url_for('video_viewing_1'))
    else:
        # If save_preferences fails, it will handle the error logging and db rollback
        return redirect(url_for('select_categories'))



@app.route('/video_viewing_1')
@participant_required
def video_viewing_1(participant):
    """Display round 1 video viewing page."""
    preferences = ParticipantService.get_participant_preferences(participant.participant_number, 1)
    selected_categories = [pref.category.name for pref in preferences]
    return render_template('video_viewing_1.html', selected_categories=selected_categories)



@app.route('/end_video_viewing_1')
@participant_required
def end_video_viewing_1(participant):
    return redirect(url_for('additional_information'))


@app.route('/api/user_interaction', methods=['POST'])
@participant_required
@db_handler
def user_interaction(participant):
    """Handle video interaction API requests (like, dislike, star, comment)."""
    data = request.get_json()
    
    # Validate required fields
    is_valid, error_msg = validate_api_request_data(data, ['video_id', 'action'])
    if not is_valid:
        return create_json_response(False, error_msg, status_code=400)

    video_id = data['video_id']
    action = data['action']
    comment_text = data.get('comment', '')

    try:
        # Delegate to service layer based on action type
        if action in ['like', 'dislike']:
            VideoInteractionService.handle_like_dislike(participant.participant_number, video_id, action)
        
        elif action in ['remove_like', 'remove_dislike']:
            VideoInteractionService.handle_remove_action(participant.participant_number, video_id, action)
        
        elif action in ['star', 'star_remove']:
            VideoInteractionService.handle_star_action(participant.participant_number, video_id, action)
        
        elif action == 'comment':
            if not VideoInteractionService.handle_comment(participant.participant_number, video_id, comment_text):
                return create_json_response(False, 'Comment text is required', status_code=400)
        
        else:
            return create_json_response(False, 'Invalid action', status_code=400)

        return create_json_response(True, 'Interaction recorded')
    
    except Exception as e:
        current_app.logger.error(f"Error in user_interaction: {str(e)}")
        return create_json_response(False, 'Failed to record interaction', status_code=500)



@app.route('/api/record_watch_time', methods=['POST'])
@participant_required
@db_handler
def record_watch_time_endpoint(participant):
    """API endpoint to record watch time for videos."""
    data, error_msg = parse_request_json(request)
    if error_msg:
        return create_json_response(False, error_msg, status_code=400)

    # Validate required fields
    required_fields = ['video_id', 'watch_duration', 'round_number']
    is_valid, validation_error = validate_api_request_data(data, required_fields)
    if not is_valid:
        return create_json_response(False, validation_error, status_code=400)

    video_id = data['video_id']
    watch_duration = data['watch_duration']
    round_number = data['round_number']
    current_position = data.get('current_position')  # Optional parameter

    # Use the helper function to record watch time
    success, message = record_watch_time(
        participant.participant_number, 
        video_id, 
        watch_duration, 
        round_number,
        current_position
    )
    
    return create_json_response(success, message, status_code=200 if success else 400)

@app.route('/api/videos')
@participant_required
def get_videos(participant):
    categories = request.args.get('categories', '')
    if not categories:
        return jsonify({'error': 'Categories parameter is required'}), 400
    
    category_names = categories.split(',')
    videos_data = get_videos_for_categories(category_names, limit_per_category=5)
    
    return jsonify({'videos': videos_data})

@app.route('/select_categories')
@participant_required
def select_categories(participant):
    """Display category selection page."""
    categories = get_categories_excluding_info()
    return render_template('select_categories.html', categories=categories)



@app.route('/coping_strategy', methods=['GET', 'POST'])
@participant_required
@db_handler
def coping_strategy(participant):
    """Handle coping strategy selection and redirect."""
    if request.method == 'POST':
        chosen_strategy = request.form.get('strategy')
        if not chosen_strategy:
            flash('请选择一个策略。', 'danger')
            return render_template('coping_strategy.html')

        # Record user's chosen strategy using service
        strategy_record = AdditionalInfoService.process_strategy_choice(
            participant.participant_number, chosen_strategy
        )
        if strategy_record:
            db.session.add(strategy_record)
        
        # Redirect based on strategy using service
        redirect_route = StrategyRedirectService.get_redirect_route(chosen_strategy)
        return redirect(url_for(redirect_route))

    return render_template('coping_strategy.html')


@app.route('/select_categories_round2', methods=['GET'])
@participant_required
def select_categories_round2(participant):
    """Display round 2 category selection excluding round 1 choices."""
    remaining_categories = ParticipantService.get_remaining_categories(participant.participant_number, 1)
    return render_template('select_categories_round2.html', categories=remaining_categories)

@app.route('/submit_categories_round2', methods=['POST'])
@participant_required
def submit_categories_round2(participant):
    """Handle round 2 category submission."""
    # Use validation helper from utils
    error_msg, validated_data = validate_category_selection(request.form)
    if error_msg:
        flash(error_msg, 'danger')
        return redirect(url_for('select_categories_round2'))
    
    # Use save_preferences helper (which uses db_handler internally)
    if save_preferences(participant.participant_number, 2, validated_data):
        flash('第二轮类别已成功提交。', 'success')
        return redirect(url_for('video_viewing_2'))
    else:
        # If save_preferences fails, it will handle the error logging and db rollback
        return redirect(url_for('select_categories_round2'))


@app.route('/video_viewing_2')
@participant_required
def video_viewing_2(participant):
    """Display round 2 video viewing page."""
    preferences_round2 = ParticipantService.get_participant_preferences(participant.participant_number, 2)
    selected_categories = [pref.category.name for pref in preferences_round2]
    return render_template('video_viewing_2.html', selected_categories=selected_categories)


@app.route('/api/videos_round2')
@participant_required
def get_videos_round2(participant):
    categories = request.args.get('categories', '')
    if not categories:
        return jsonify({'error': 'Categories parameter is required'}), 400
        
    category_names = categories.split(',')
    if len(category_names) != 3:
        return jsonify({'error': 'Exactly 3 categories are required'}), 400

    videos_data = get_videos_for_categories(
        category_names,
        participant_number=participant.participant_number,
        exclude_watched_round=1,
        limit_per_category=1
    )
    
    return jsonify({'videos': videos_data})

@app.route('/end_video_viewing_2')
@participant_required
def end_video_viewing_2(participant):
    """End round 2 video viewing."""
    flash('感谢您的参与！', 'success')
    return redirect(url_for('end_study'))


@app.route('/info_cocoons')
@participant_required 
def info_cocoons(participant):
    """Display info cocoons educational video."""
    video_link = "https://www.douyin.com/video/7277534527801576704"
    return render_template('info_cocoons.html', video_link=video_link)

@app.route('/continue_same_categories')
@participant_required
def continue_same_categories(participant):
    """Continue viewing videos from the same categories as round 1."""
    # Get participant's round 1 preferences
    prefs_round1 = ParticipantService.get_participant_preferences(participant.participant_number, 1)
    
    if len(prefs_round1) != 3:
        flash('尚未完成初次类别选择。', 'danger')
        return redirect(url_for('select_categories'))

    try:
        chosen_videos, selected_categories = VideoSelectionService.select_videos_for_preferences(
            participant.participant_number, prefs_round1
        )
        return render_template('continue_same_categories.html', 
                             videos=chosen_videos, 
                             selected_categories=selected_categories)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('select_categories'))


@app.route('/select_categories_after_info_cocoons_round2', methods=['GET'])
@participant_required
def select_categories_after_info_cocoons_round2(participant):
    """Display category selection after info cocoons video."""
    # Allow selection from all categories again 
    remaining_categories = get_categories_excluding_info()
    return render_template('select_categories_after_info_cocoons_round2.html', categories=remaining_categories)


@app.route('/submit_categories_after_info_cocoons_round2', methods=['POST'])
@participant_required
def submit_categories_after_info_cocoons_round2(participant):
    """Handle category submission after info cocoons video."""
    # Use validation helper from utils
    error_msg, validated_data = validate_category_selection(request.form)
    if error_msg:
        flash(error_msg, 'danger')
        return redirect(url_for('select_categories_after_info_cocoons_round2'))
    
    # Use save_preferences helper (which uses db_handler internally)
    if save_preferences(participant.participant_number, 2, validated_data):
        flash('第二次信息视频后类别选择已成功提交。', 'success')
        return redirect(url_for('video_viewing_after_info_cocoons_2'))
    else:
        # If save_preferences fails, it will handle the error logging and db rollback
        return redirect(url_for('select_categories_after_info_cocoons_round2'))


@app.route('/video_viewing_after_info_cocoons_2')
@participant_required
def video_viewing_after_info_cocoons_2(participant):
    """Display video viewing page after info cocoons."""
    preferences_after_info = ParticipantService.get_participant_preferences(participant.participant_number, 2)
    selected_categories = [pref.category.name for pref in preferences_after_info]
    return render_template('video_viewing_after_info_cocoons_2.html', selected_categories=selected_categories)


@app.route('/api/videos_after_info_cocoons_round2')
@participant_required
def get_videos_after_info_cocoons_round2(participant):
    categories = request.args.get('categories', '')
    if not categories:
        return jsonify({'error': 'Categories parameter is required'}), 400
        
    category_names = categories.split(',')
    if len(category_names) != 3:
        return jsonify({'error': 'Exactly 3 categories are required'}), 400

    videos_data = get_videos_for_categories(
        category_names,
        participant_number=participant.participant_number,
        exclude_watched_round=1,
        limit_per_category=1
    )
    
    return jsonify({'videos': videos_data})



@app.route('/additional_information', methods=['GET', 'POST'])
@participant_required
@db_handler
def additional_information(participant):
    """Handle additional information form processing and strategy redirection."""
    group_num = participant.group_number

    if request.method == 'POST':
        try:
            records_to_add = []
            
            # Process time spent
            time_spent_record = AdditionalInfoService.process_time_spent(
                participant.participant_number, 
                request.form.get('timeSpent', '0')
            )
            if time_spent_record:
                records_to_add.append(time_spent_record)

            # Process group-specific consistency questions for group 5
            if group_num == 5:
                consistency_records = AdditionalInfoService.process_consistency_answers(
                    participant.participant_number,
                    request.form.get('q1'),
                    request.form.get('q2')
                )
                records_to_add.extend(consistency_records)
            
            # Process strategy choice
            chosen_strategy = request.form.get('strategy')
            strategy_record = AdditionalInfoService.process_strategy_choice(
                participant.participant_number, chosen_strategy
            )
            if strategy_record:
                records_to_add.append(strategy_record)

            # Add all records to the session
            if records_to_add:
                for record in records_to_add:
                    db.session.add(record)
                current_app.logger.info(f"Successfully processed {len(records_to_add)} records for participant {participant.participant_number}")
            
            # Handle redirects based on strategy
            redirect_route = AdditionalInfoService.determine_redirect_route(chosen_strategy)
            return redirect(url_for(redirect_route))
        
        except Exception as e:
            # db_handler will handle rollback
            current_app.logger.error(f"Error in additional_information for participant {participant.participant_number}: {str(e)}")
            flash('处理请求时发生错误，请稍后再试。', 'danger')
            return redirect(url_for('additional_information'))

    # GET request - render the template
    return render_template('additional_information.html',
                           message=GROUP_MESSAGES.get(group_num, ''),
                           group_num=group_num)

@app.route('/end_study')
@participant_required
def end_study(participant):
    return render_template('end_study.html', participant_number=participant.participant_number)

@app.route('/test_embed')
@participant_required
def test_embed(participant):
    """Test embed functionality - development only."""
    # Example Douyin video URL
    douyin_video_url = "https://open.douyin.com/player/video?vid=7290445158779276601&autoplay=0"
    return render_template('test_embed.html', video_url=douyin_video_url)


@app.route('/test_video')
def test_video():
    return render_template('test_video.html')

if __name__ =="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)



