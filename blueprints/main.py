"""
Blueprint for main application routes.
Contains all the main user-facing routes for the video research application.
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user
from config import db
from models import Participant
from utils import (participant_required, db_handler, validate_category_selection, 
                  save_preferences, generate_unique_participant_number, 
                  validate_group_number, get_categories_excluding_info, GROUP_MESSAGES)
from services import (VideoSelectionService, ParticipantService, 
                     AdditionalInfoService, StrategyRedirectService)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    return "Hello, PythonAnywhere!"


@main_bp.route('/intro/<int:group_number>')
def show_intro(group_number):
    if not validate_group_number(group_number):
        flash('无效组别编号。', 'danger')
        return redirect(url_for('main.show_intro', group_number=1))
    return render_template('index.html', group_number=group_number)


@main_bp.route('/initial_selection/<int:group_number>', methods=['GET', 'POST'])
def initial_selection(group_number):
    if not validate_group_number(group_number):
        flash('无效组别编号。', 'danger')
        return redirect(url_for('main.show_intro', group_number=1))
    
    try:
        participant_number = generate_unique_participant_number()
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('main.show_intro', group_number=1))

    participant = Participant(participant_number=participant_number, group_number=group_number)
    db.session.add(participant)
    db.session.commit()
    session['participant_number'] = participant_number
    login_user(participant)

    return redirect(url_for('main.select_categories'))


@main_bp.route('/select_categories')
@participant_required
def select_categories(participant):
    """Display category selection page."""
    categories = get_categories_excluding_info()
    return render_template('select_categories.html', categories=categories)


@main_bp.route('/submit_categories', methods=['POST'])
@participant_required
def submit_categories(participant):
    """Handle initial category submission."""
    # Use validation helper from utils
    error_msg, validated_data = validate_category_selection(request.form)
    if error_msg:
        flash(error_msg, 'danger')
        return redirect(url_for('main.select_categories'))
    
    # Use save_preferences helper (which uses db_handler internally)
    if save_preferences(participant.participant_number, 1, validated_data):
        flash('第一轮类别已成功提交。', 'success')
        return redirect(url_for('main.video_viewing_1'))
    else:
        # If save_preferences fails, it will handle the error logging and db rollback
        return redirect(url_for('main.select_categories'))


@main_bp.route('/video_viewing_1')
@participant_required
def video_viewing_1(participant):
    """Display round 1 video viewing page."""
    preferences = ParticipantService.get_participant_preferences(participant.participant_number, 1)
    selected_categories = [pref.category.name for pref in preferences]
    return render_template('video_viewing_1.html', selected_categories=selected_categories)


@main_bp.route('/end_video_viewing_1')
@participant_required
def end_video_viewing_1(participant):
    return redirect(url_for('main.additional_information'))


@main_bp.route('/additional_information', methods=['GET', 'POST'])
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
                from flask import current_app
                current_app.logger.info(f"Successfully processed {len(records_to_add)} records for participant {participant.participant_number}")
            
            # Handle redirects based on strategy
            redirect_route = AdditionalInfoService.determine_redirect_route(chosen_strategy)
            return redirect(url_for(f'main.{redirect_route}'))
        
        except Exception as e:
            # db_handler will handle rollback
            from flask import current_app
            current_app.logger.error(f"Error in additional_information for participant {participant.participant_number}: {str(e)}")
            flash('处理请求时发生错误，请稍后再试。', 'danger')
            return redirect(url_for('main.additional_information'))

    # GET request - render the template
    return render_template('additional_information.html',
                           message=GROUP_MESSAGES.get(group_num, ''),
                           group_num=group_num)


@main_bp.route('/coping_strategy', methods=['GET', 'POST'])
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
        return redirect(url_for(f'main.{redirect_route}'))

    return render_template('coping_strategy.html')


@main_bp.route('/continue_same_categories')
@participant_required
def continue_same_categories(participant):
    """Continue viewing videos from the same categories as round 1."""
    # Get participant's round 1 preferences
    prefs_round1 = ParticipantService.get_participant_preferences(participant.participant_number, 1)
    
    if len(prefs_round1) != 3:
        flash('尚未完成初次类别选择。', 'danger')
        return redirect(url_for('main.select_categories'))

    try:
        chosen_videos, selected_categories = VideoSelectionService.select_videos_for_preferences(
            participant.participant_number, prefs_round1
        )
        return render_template('continue_same_categories.html', 
                             videos=chosen_videos, 
                             selected_categories=selected_categories)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('main.select_categories'))


@main_bp.route('/info_cocoons')
@participant_required 
def info_cocoons(participant):
    """Display info cocoons educational video."""
    video_link = "https://www.douyin.com/video/7277534527801576704"
    return render_template('info_cocoons.html', video_link=video_link)


@main_bp.route('/end_study')
@participant_required
def end_study(participant):
    return render_template('end_study.html', participant_number=participant.participant_number)
