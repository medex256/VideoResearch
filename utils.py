from functools import wraps
from flask import session, flash, redirect, url_for, jsonify, current_app, request
from config import db
from models import Participant, Preference, Video, WatchingTime

def get_participant_or_redirect():
    """
    Retrieves the participant from the session. If not found or invalid,
    flashes an error and returns a redirect object.
    Returns (participant, None) on success, and (None, redirect_response) on failure.
    """
    participant_number = session.get('participant_number')
    if not participant_number:
        flash('未找到参与者信息或会话已过期。', 'danger')
        return None, redirect(url_for('show_intro', group_number=1))
    
    participant = Participant.query.get(participant_number)
    if not participant:
        flash('参与者信息无效。', 'danger')
        session.pop('participant_number', None)  # Clean up bad session data
        return None, redirect(url_for('show_intro', group_number=1))
        
    return participant, None

def participant_required(f):
    """
    Decorator that checks for a valid participant in the session.
    If successful, it passes the participant object to the decorated function.
    Otherwise, it redirects to the intro page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        participant, response = get_participant_or_redirect()
        if response:
            return response
        # Pass participant as the first argument to the decorated function
        return f(participant, *args, **kwargs)
    return decorated_function

def db_handler(f):
    """
    A decorator to handle database session commit and rollback.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            db.session.commit()
            return result
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in {f.__name__}: {str(e)}")
            # For web pages, flash a message and redirect
            if request.endpoint and 'api' not in request.endpoint:
                flash('处理您的请求时发生数据库错误。请稍后再试。', 'danger')
                # Redirect to a safe page, e.g., the last known good step
                # This is a generic fallback
                return redirect(url_for('select_categories'))
            # For API endpoints, return a JSON error
            return jsonify({'success': False, 'message': 'Database error'}), 500
    return decorated_function

def validate_category_selection(form_data, required_count=3):
    """
    Validates submitted category selections and ratings from a form.
    Returns (error_message, None) on validation failure, 
    and (None, selected_data) on success.
    """
    selected_data = []
    for key, value in form_data.items():
        if key.startswith('rating_'):
            try:
                category_id = int(key.split('_')[1])
                rating = int(value)
                if rating > 0:
                    selected_data.append({'category_id': category_id, 'rating': rating})
            except (IndexError, ValueError):
                return '无效的类别ID或评分格式。', None

    if len(selected_data) != required_count:
        return f'请确保您恰好选择了 {required_count} 个类别。', None

    ratings = [item['rating'] for item in selected_data]
    if not all(1 <= rating <= 10 for rating in ratings):
        return '评分必须在1到10之间。', None

    if len(set(ratings)) < required_count:
        return '请为三个类别提供不同的评分，不能重复。', None

    return None, selected_data

@db_handler
def save_preferences(participant_number, round_number, preferences_data):
    """
    Saves participant's category preferences for a given round.
    This function is decorated with @db_handler to manage the session.
    """
    # Clear previous preferences for this round to handle resubmissions
    Preference.query.filter_by(
        participant_number=participant_number, 
        round_number=round_number
    ).delete(synchronize_session=False) # `synchronize_session=False` is often safer with bulk operations

    new_preferences = [
        Preference(
            participant_number=participant_number,
            round_number=round_number,
            category_id=item['category_id'],
            rating=item['rating']
        ) for item in preferences_data
    ]
    
    db.session.bulk_save_objects(new_preferences)
    current_app.logger.info(
        f"Saved {len(new_preferences)} preferences for participant {participant_number} in round {round_number}."
    )
    return True # Indicate success

@db_handler
def record_watch_time(participant_number, video_id, watch_duration, round_number, current_position=None):
    """
    Records or updates video watch time for a participant.
    
    Args:
        participant_number: The participant's ID
        video_id: The video's ID
        watch_duration: Time watched in seconds
        round_number: The viewing round (1 or 2)
        current_position: The current playback position in seconds (optional)
        
    Returns:
        tuple: (success boolean, message string)
    """
    if not participant_number or not video_id or watch_duration is None or round_number is None:
        return False, "Missing required parameters"
    
    # Calculate percentage watched based on video type
    percentage_watched = None
    INFO_VIDEO_DURATION = 228  # Hardcoded duration for info video (ID 9999)
    
    if video_id == 9999:  
        # For info video, use hardcoded duration
        if watch_duration > 0:
            percentage_watched = min((watch_duration / INFO_VIDEO_DURATION) * 100, 100)
    else:
        # For regular videos
        video = Video.query.get(video_id)
        if not video:
            return False, "Video not found"
            
        if video.duration and video.duration > 0:
            percentage_watched = min((watch_duration / video.duration) * 100, 100)
    
    # Check if an entry already exists for this participant, video, and round
    existing_record = WatchingTime.query.filter_by(
        participant_number=participant_number,
        video_id=video_id,
        round_number=round_number
    ).first()
    
    position_info = f", Position: {current_position}s" if current_position is not None else ""
    
    if existing_record:
        # Update existing record
        existing_record.time_spent += watch_duration
        
        # Update percentage watched based on video type
        if video_id == 9999:
            if existing_record.time_spent > 0:
                existing_record.percentage_watched = min((existing_record.time_spent / INFO_VIDEO_DURATION) * 100, 100)
        else:
            if video.duration and video.duration > 0:
                existing_record.percentage_watched = min((existing_record.time_spent / video.duration) * 100, 100)
        
        # Format percentage for logging
        percentage_str = f"{existing_record.percentage_watched:.1f}" if existing_record.percentage_watched is not None else "N/A"
        
        current_app.logger.info(f"Updated Watch Time: Participant {participant_number}, Video {video_id}, "
                              f"Round {round_number}, Total Time Spent {existing_record.time_spent} seconds, "
                              f"Percentage {percentage_str}%{position_info}")
    else:
        # Create a new record
        new_record = WatchingTime(
            participant_number=participant_number,
            video_id=video_id,
            round_number=round_number,
            time_spent=watch_duration,
            percentage_watched=percentage_watched
        )
        db.session.add(new_record)
        
        # Format percentage for logging
        percentage_str = f"{percentage_watched:.1f}" if percentage_watched is not None else "N/A"
        
        current_app.logger.info(f"New Watch Time Record: Participant {participant_number}, Video {video_id}, "
                              f"Round {round_number}, Time Spent {watch_duration} seconds, "
                              f"Percentage {percentage_str}%{position_info}")
    
    return True, "Watch time recorded successfully"
