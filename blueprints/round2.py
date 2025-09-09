"""
Blueprint for round 2 specific routes.
Handles all functionality related to the second round of video viewing.
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash
from utils import (participant_required, validate_category_selection, 
                  save_preferences, get_categories_excluding_info)
from services import ParticipantService

round2_bp = Blueprint('round2', __name__, url_prefix='/round2')


@round2_bp.route('/select_categories', methods=['GET'])
@participant_required
def select_categories_round2(participant):
    """Display round 2 category selection excluding round 1 choices."""
    remaining_categories = ParticipantService.get_remaining_categories(participant.participant_number, 1)
    return render_template('select_categories_round2.html', categories=remaining_categories)


@round2_bp.route('/submit_categories', methods=['POST'])
@participant_required
def submit_categories_round2(participant):
    """Handle round 2 category submission."""
    # Use validation helper from utils
    error_msg, validated_data = validate_category_selection(request.form)
    if error_msg:
        flash(error_msg, 'danger')
        return redirect(url_for('round2.select_categories_round2'))
    
    # Use save_preferences helper (which uses db_handler internally)
    if save_preferences(participant.participant_number, 2, validated_data):
        flash('第二轮类别已成功提交。', 'success')
        return redirect(url_for('round2.video_viewing_2'))
    else:
        # If save_preferences fails, it will handle the error logging and db rollback
        return redirect(url_for('round2.select_categories_round2'))


@round2_bp.route('/video_viewing')
@participant_required
def video_viewing_2(participant):
    """Display round 2 video viewing page."""
    preferences_round2 = ParticipantService.get_participant_preferences(participant.participant_number, 2)
    selected_categories = [pref.category.name for pref in preferences_round2]
    return render_template('video_viewing_2.html', selected_categories=selected_categories)


@round2_bp.route('/end_viewing')
@participant_required
def end_video_viewing_2(participant):
    """End round 2 video viewing."""
    flash('感谢您的参与！', 'success')
    return redirect(url_for('main.end_study'))


@round2_bp.route('/select_categories_after_info_cocoons', methods=['GET'])
@participant_required
def select_categories_after_info_cocoons_round2(participant):
    """Display category selection after info cocoons video."""
    # Allow selection from all categories again 
    remaining_categories = get_categories_excluding_info()
    return render_template('select_categories_after_info_cocoons_round2.html', categories=remaining_categories)


@round2_bp.route('/submit_categories_after_info_cocoons', methods=['POST'])
@participant_required
def submit_categories_after_info_cocoons_round2(participant):
    """Handle category submission after info cocoons video."""
    # Use validation helper from utils
    error_msg, validated_data = validate_category_selection(request.form)
    if error_msg:
        flash(error_msg, 'danger')
        return redirect(url_for('round2.select_categories_after_info_cocoons_round2'))
    
    # Use save_preferences helper (which uses db_handler internally)
    if save_preferences(participant.participant_number, 2, validated_data):
        flash('第二次信息视频后类别选择已成功提交。', 'success')
        return redirect(url_for('round2.video_viewing_after_info_cocoons_2'))
    else:
        # If save_preferences fails, it will handle the error logging and db rollback
        return redirect(url_for('round2.select_categories_after_info_cocoons_round2'))


@round2_bp.route('/video_viewing_after_info_cocoons')
@participant_required
def video_viewing_after_info_cocoons_2(participant):
    """Display video viewing page after info cocoons."""
    preferences_after_info = ParticipantService.get_participant_preferences(participant.participant_number, 2)
    selected_categories = [pref.category.name for pref in preferences_after_info]
    return render_template('video_viewing_after_info_cocoons_2.html', selected_categories=selected_categories)
