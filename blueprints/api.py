"""
Blueprint for API routes.
Separates API endpoints from main application routes.
"""
from flask import Blueprint, request, jsonify
from utils import (participant_required, db_handler, create_json_response,
                  validate_api_request_data, parse_request_json, record_watch_time,
                  get_videos_for_categories)
from services import VideoInteractionService

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/user_interaction', methods=['POST'])
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
        from flask import current_app
        current_app.logger.error(f"Error in user_interaction: {str(e)}")
        return create_json_response(False, 'Failed to record interaction', status_code=500)


@api_bp.route('/record_watch_time', methods=['POST'])
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


@api_bp.route('/videos')
@participant_required
def get_videos(participant):
    """Get videos for specified categories."""
    categories = request.args.get('categories', '')
    if not categories:
        return jsonify({'error': 'Categories parameter is required'}), 400
    
    category_names = categories.split(',')
    videos_data = get_videos_for_categories(category_names, limit_per_category=3)
    
    return jsonify({'videos': videos_data})


@api_bp.route('/videos_round2')
@participant_required
def get_videos_round2(participant):
    """Get videos for round 2 with specific requirements."""
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


@api_bp.route('/videos_after_info_cocoons_round2')
@participant_required
def get_videos_after_info_cocoons_round2(participant):
    """Get videos after info cocoons viewing."""
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
