from functools import wraps
from flask import session, flash, redirect, url_for, jsonify, current_app, request
from config import db
from models import Participant, Preference, Video, WatchingTime, VideoCategory
import random

# Group messages moved to utils for reusability
GROUP_MESSAGES = {
    0: "您已完成第一轮视频浏览，接下来请您点击下列按钮进入后续步骤。\n\n"
        "• 若您点击\"观看多样化视频\"，则需从未浏览的12类视频中再次选择三类您感兴趣的视频进行浏览。\n\n"
        "• 若您点击\"了解更多信息茧房\"，则需观看一个与信息茧房相关的科普视频并再次做出您的类型偏好选择。\n\n"
        "• 若您点击\"观看相同类型视频\"，则会继续浏览与您之前所选类型相同的视频内容。",
    1: "【！！系统检测到您已经浏览了大量同质化的视频内容。长期暴露于同质化的信息被证实能够强化人们的认知偏差和思维局限，甚至会导致偏激的思想和行为。\n\n 为了避免信息茧房危害，我们建议您观看多样化的视频内容。】",
    2: "【！！系统检测到您已经浏览了大量同质化的视频内容。\n\n 我们十分理解并认同您对某一类视频的喜爱，我们同样希望您能通过浏览短视频获得充分的放松和愉悦。我们相信，重复单调的信息并不能满足您对于大千世界的好奇和探索欲，您完全有能力对多样化信息进行充分获取和吸收。为了进一步提升您的内容体验，我们建议您观看多样化的视频内容。】",
    3: "【！！系统检测到您已经浏览了大量同质化的视频内容。\n\n 信息行为研究者花费了多年时间和数以万计的成本来提高人们的信息茧房风险意识并帮助其远离信息茧房危害。您主动的多样化内容选择是帮助我们实现破茧的关键一环。为了协助我们抵御信息茧房风险，我们建议您观看多样化的视频内容。】",
    4: "【！！系统检测到您已经浏览了大量同质化的视频内容。\n\n 开放多元的信息环境是平台管理者和广大网民的共同愿望。各大主流短视频平台近年纷纷推出内容管理功能鼓励用户自主调节多元内容推送比例，同时，超过85%的短视频平台用户在得知信息茧房风险之后都选择观看不同类型的视频。为了共同构建包容和谐、丰富多彩的网络环境，我们建议您观看多样化的视频内容。】",
    5: "【！！系统检测到您已经浏览了大量同质化的视频内容。\n\n 请问您在多大程度上同意信息茧房可能对您造成危害: 0-10请问您在多大程度上同意观看多种类型的视频是保护自己远离信息茧房的有效手段: 0-10您的选择表明您对于信息茧房及其缓解策略有较为清晰的认知。基于您的选择，我们建议您观看多样化的视频内容。】",
    6: "【！！系统检测到您已经浏览了大量同质化的视频内容。\n\n 哈佛大学法学院教授、著名行为经济学家Sunstein在其著作《信息乌托邦》中深刻阐明了信息茧房对于个人身心和思维的危害并强调了浏览多样化信息内容对于缓解信息茧房的有效作用。依据权威人士的建议，我们建议您接下来观看多样化的视频内容。】",
    7: "【！！系统检测到您已经浏览了大量同质化的视频内容。\n\n 陷入信息茧房的人们往往是无意识的，推荐算法结合个人喜好源源不断地为用户推荐符合兴趣的内容，这使得您几乎没有机会立即分辨并主动远离信息茧房。此次实验是帮助您认识信息茧房风险并主动跳出信息茧房的难得机会，我们建议您把握此次机会，在接下来观看多样化的视频内容。】",
}

def get_route_with_participant_check(required_message='未找到参与者信息。'):
    """
    Helper to reduce repetitive participant checking in routes.
    Returns (participant_number, None) on success, (None, redirect_response) on failure.
    """
    participant_number = session.get('participant_number')
    if not participant_number:
        flash(required_message, 'danger')
        return None, redirect(url_for('main.show_intro', group_number=1))
    return participant_number, None

def generate_unique_participant_number():
    """Generates a unique 4-digit participant number."""
    MAX_ATTEMPTS = 100
    for _ in range(MAX_ATTEMPTS):
        number = str(random.randint(1000, 9999)).zfill(4)
        if not Participant.query.get(number):
            return number
    raise ValueError("无法生成唯一的参与者编号。请稍后再试。")

def get_participant_or_redirect():
    """
    Retrieves the participant from the session. If not found or invalid,
    flashes an error and returns a redirect object.
    Returns (participant, None) on success, and (None, redirect_response) on failure.
    """
    participant_number = session.get('participant_number')
    if not participant_number:
        flash('未找到参与者信息或会话已过期。', 'danger')
        return None, redirect(url_for('main.show_intro', group_number=1))
    
    participant = Participant.query.get(participant_number)
    if not participant:
        flash('参与者信息无效。', 'danger')
        session.pop('participant_number', None)  # Clean up bad session data
        return None, redirect(url_for('main.show_intro', group_number=1))
        
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

def get_videos_for_categories(category_names, participant_number=None, exclude_watched_round=None, limit_per_category=None):
    """
    Fetches videos for a given list of category names, with options to exclude watched videos and limit results.
    """
    videos_query = db.session.query(Video, VideoCategory).join(
        VideoCategory, Video.category_id == VideoCategory.id
    ).filter(VideoCategory.name.in_(category_names))

    # If requested, exclude videos the participant has already watched in a specific round
    if participant_number and exclude_watched_round:
        watched_video_ids = db.session.query(WatchingTime.video_id).filter(
            WatchingTime.participant_number == participant_number,
            WatchingTime.round_number == exclude_watched_round
        ).all()
        watched_ids = [row[0] for row in watched_video_ids]
        if watched_ids:
            videos_query = videos_query.filter(~Video.id.in_(watched_ids))

    available_videos = videos_query.all()

    # Group videos by category to handle limits correctly
    videos_by_category = {}
    for video, category in available_videos:
        if category.name not in videos_by_category:
            videos_by_category[category.name] = []
        videos_by_category[category.name].append(video)

    # Select a limited number of videos from each category if a limit is set
    videos_data = []
    for category_name in category_names:
        category_videos = videos_by_category.get(category_name, [])
        
        if limit_per_category:
            selected_videos = random.sample(category_videos, min(limit_per_category, len(category_videos)))
        else:
            selected_videos = category_videos  # Take all available if no limit

        for video in selected_videos:
            videos_data.append({
                'id': video.id,
                'title': video.title,  # Add title field for backward compatibility
                'link': video.url,
                'category': category_name
            })
    
    random.shuffle(videos_data)
    return videos_data

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
                return redirect(url_for('main.select_categories'))
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


def validate_group_number(group_number):
    """Validate group number is within acceptable range."""
    return 0 <= group_number <= 7


def get_categories_excluding_info():
    """Get all video categories except 'info'."""
    from models import VideoCategory
    return VideoCategory.query.filter(VideoCategory.name != 'info').all()


def create_json_response(success=True, message="", data=None, status_code=200):
    """Create standardized JSON responses for API endpoints."""
    response_data = {
        'success': success,
        'message': message,
        'status': 'success' if success else 'fail'  # Backward compatibility
    }
    if data is not None:
        response_data.update(data)
    
    return jsonify(response_data), status_code


def validate_api_request_data(data, required_fields):
    """
    Validate that required fields are present in API request data.
    
    Args:
        data: The request data dictionary
        required_fields: List of required field names
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not data:
        return False, "No data provided"
    
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, ""


def parse_request_json(request_obj):
    """
    Safely parse JSON from request object.
    
    Returns:
        tuple: (data, error_message)
    """
    try:
        import json
        data = json.loads(request_obj.data.decode('utf-8'))
        return data, None
    except (TypeError, json.JSONDecodeError) as e:
        current_app.logger.error(f"JSON decode error: {e}")
        return None, "Invalid JSON data"
