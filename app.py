from flask import Flask, jsonify, render_template, redirect, url_for, request, flash, session, make_response, Response
from flask_login import LoginManager, login_user, login_required, current_user
from config import app, db
from functools import wraps
from collections import Counter
from models import Participant,VideoCategory,Video,Preference,VideoInteraction,WatchingTime,CopingStrategy,ConsistencyAnswer,MessageTime
from utils import participant_required, db_handler, validate_category_selection, save_preferences, record_watch_time


from load_videos import load_videos_from_excel  # ensure load_videos.py defines a load_videos() function



import random
import re
import json
import requests
import os

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return Participant.query.get(user_id)

# Using the participant_required decorator from utils.py
# Keeping this for backward compatibility
def login_required_custom(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'participant_number' not in session:
            flash('无效的会话。', 'danger')
            return redirect(url_for('show_intro', group_number=1))
        return f(*args, **kwargs)
    return decorated_function



def generate_unique_participant_number():
    MAX_ATTEMPTS = 1000
    for _ in range(MAX_ATTEMPTS):
        number = str(random.randint(10000, 99999)).zfill(5)
        if not Participant.query.get(number):
            return number
    raise ValueError("无法生成唯一的参与者编号。请稍后再试。")



@app.route('/')
def home():
    return "Hello, PythonAnywhere!"


@app.route('/intro/<int:group_number>')
def show_intro(group_number):
    if group_number < 0 or group_number > 7:
        flash('无效组别编号。', 'danger')
        # Fallback to group_number=1 instead of "index"
        return redirect(url_for('show_intro', group_number=1))
    return render_template('index.html', group_number=group_number)


@app.route('/initial_selection/<int:group_number>', methods=['GET', 'POST'])
def initial_selection(group_number):
    if group_number < 0 or group_number > 7:
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

    # Redirect to category selection or wherever you need next
    return redirect(url_for('select_categories'))


@app.route('/submit_categories', methods=['POST'])
@login_required_custom
def submit_categories():
    participant_number = session.get('participant_number')
    if not participant_number:
        flash('未找到参与者信息。', 'danger')
        return redirect(url_for('show_intro', group_number=1))
    
    # Use validation helper from utils
    error_msg, validated_data = validate_category_selection(request.form)
    if error_msg:
        flash(error_msg, 'danger')
        return redirect(url_for('select_categories'))
    
    # Use save_preferences helper (which uses db_handler internally)
    if save_preferences(participant_number, 1, validated_data):
        flash('第一轮类别已成功提交。', 'success')
        return redirect(url_for('video_viewing_1'))
    else:
        # If save_preferences fails, it will handle the error logging and db rollback
        return redirect(url_for('select_categories'))



@app.route('/video_viewing_1')
@login_required_custom
def video_viewing_1():
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


@app.route('/api/user_interaction', methods=['POST'])
@login_required_custom
@db_handler
def user_interaction():
    data = request.get_json()
    video_id = data.get('video_id')
    action = data.get('action')
    comment_text = data.get('comment')

    if not video_id or not action:
        return jsonify({'success': False, 'message': 'Missing parameters'}), 400

    participant_number = session.get('participant_number')

    if action in ['like', 'dislike']:
        # Single efficient DELETE operation
        VideoInteraction.query.filter_by(
            participant_number=participant_number,
            video_id=video_id
        ).filter(VideoInteraction.action.in_(['like', 'dislike'])).delete()
        
        # Add new interaction
        new_interaction = VideoInteraction(
            participant_number=participant_number,
            video_id=video_id,
            action=action,
            content=''
        )
        db.session.add(new_interaction)

    elif action in ['remove_like', 'remove_dislike']:
        target_action = action.split('_')[1]
        VideoInteraction.query.filter_by(
            participant_number=participant_number,
            video_id=video_id,
            action=target_action
        ).delete()

    elif action in ['star', 'star_remove']:
        if action == 'star':
            # Use INSERT IGNORE pattern
            existing = VideoInteraction.query.filter_by(
                participant_number=participant_number,
                video_id=video_id,
                action='star'
            ).first()
            if not existing:
                db.session.add(VideoInteraction(
                    participant_number=participant_number,
                    video_id=video_id,
                    action='star',
                    content=''
                ))
        else:  # star_remove
            VideoInteraction.query.filter_by(
                participant_number=participant_number,
                video_id=video_id,
                action='star'
            ).delete()

    elif action == 'comment':
        if not comment_text.strip():
            return jsonify({'success': False, 'message': 'Comment text cannot be empty.'}), 400
        db.session.add(VideoInteraction(
            participant_number=participant_number,
            video_id=video_id,
            action=action,
            content=comment_text.strip()
        ))

    else:
        return jsonify({'success': False, 'message': 'Invalid action.'}), 400

    # db_handler will handle commit and error handling
    return jsonify({'success': True, 'message': 'Interaction recorded'}), 200



@app.route('/api/record_watch_time', methods=['POST'])
@login_required_custom
@db_handler
def record_watch_time_endpoint():
    """
    API endpoint to record watch time for videos.
    """
    try:
        data = json.loads(request.data.decode('utf-8'))
    except (TypeError, json.JSONDecodeError) as e:
        app.logger.error(f"JSON decode error: {e}")
        return jsonify({'status': 'fail', 'message': 'Invalid JSON data'}), 400

    video_id = data.get('video_id')
    watch_duration = data.get('watch_duration')
    round_number = data.get('round_number')
    current_position = data.get('current_position')  # New parameter to track seeking behavior

    # Validate incoming data
    if not video_id or watch_duration is None or round_number is None:
        return jsonify({'status': 'fail', 'message': 'Invalid data'}), 400

    participant_number = session.get('participant_number')
    if not participant_number:
        return jsonify({'status': 'fail', 'message': 'Participant not found'}), 400
    
    # Use the helper function to record watch time
    success, message = record_watch_time(
        participant_number, 
        video_id, 
        watch_duration, 
        round_number,
        current_position
    )
    
    if success:
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'fail', 'message': message}), 400

@app.route('/api/videos')
@login_required_custom
def get_videos():
    categories = request.args.get('categories')
    category_names = categories.split(',')

    videos_query = db.session.query(Video, VideoCategory).join(
        VideoCategory, Video.category_id == VideoCategory.id
    ).filter(VideoCategory.name.in_(category_names)).all()
    
    # Group videos by category
    videos_by_category = {}
    for video, category in videos_query:
        if category.name not in videos_by_category:
            videos_by_category[category.name] = []
        videos_by_category[category.name].append(video)
    
    # Select 5 videos per category
    videos_data = []
    for category_name in category_names:
        category_videos = videos_by_category.get(category_name, [])
        selected_videos = random.sample(category_videos, min(5, len(category_videos)))
        for video in selected_videos:
            videos_data.append({
                'id': video.id,
                'title': video.title,
                'link': video.url,
            })

    random.shuffle(videos_data)
    return jsonify({'videos': videos_data})

@app.route('/select_categories')
@login_required_custom
def select_categories():
    categories = VideoCategory.query.filter(VideoCategory.name != 'info').all()
    return render_template('select_categories.html', categories=categories)



@app.route('/coping_strategy', methods=['GET', 'POST'])
@login_required_custom
@db_handler
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
        # db_handler will handle the commit
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
    
    # Use validation helper from utils
    error_msg, validated_data = validate_category_selection(request.form)
    if error_msg:
        flash(error_msg, 'danger')
        return redirect(url_for('select_categories_round2'))
    
    # Use save_preferences helper (which uses db_handler internally)
    if save_preferences(participant_number, 2, validated_data):
        flash('第二轮类别已成功提交。', 'success')
        return redirect(url_for('video_viewing_2'))
    else:
        # If save_preferences fails, it will handle the error logging and db rollback
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
    category_names = categories.split(',')
    participant_number = session.get('participant_number')

    if not participant_number or len(category_names) != 3:
        return jsonify({'error': 'Invalid request'}), 400

    # Get the list of watched video IDs first
    watched_video_ids = db.session.query(WatchingTime.video_id).filter(
        WatchingTime.participant_number == participant_number,
        WatchingTime.round_number == 1
    ).all()
    
    # Extract IDs from result tuples
    watched_ids = [row[0] for row in watched_video_ids]
    
    # Query available videos, excluding watched ones
    available_videos = db.session.query(Video, VideoCategory).join(
        VideoCategory, Video.category_id == VideoCategory.id
    ).filter(
        VideoCategory.name.in_(category_names)
    )
    
    if watched_ids:  # Only apply filter if there are watched videos
        available_videos = available_videos.filter(
            ~Video.id.in_(watched_ids)
        )
    
    available_videos = available_videos.all()

    # Group by category and select one per category
    videos_by_category = {}
    for video, category in available_videos:
        if category.name not in videos_by_category:
            videos_by_category[category.name] = []
        videos_by_category[category.name].append(video)

    videos_data = []
    for category_name in category_names:
        category_videos = videos_by_category.get(category_name, [])
        if not category_videos:
            # Fallback: get any video from this category that hasn't been watched
            fallback_query = Video.query.join(VideoCategory).filter(
                VideoCategory.name == category_name
            )
            
            if watched_ids:
                fallback_query = fallback_query.filter(
                    ~Video.id.in_(watched_ids)
                )
                
            fallback_videos = fallback_query.all()
            category_videos = fallback_videos

        if category_videos:
            selected_video = random.choice(category_videos)
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

    # Get participant's round 1 preferences
    prefs_round1 = Preference.query.filter_by(
        participant_number=participant_number, 
        round_number=1
    ).all()
    
    if len(prefs_round1) != 3:
        flash('尚未完成初次类别选择。', 'danger')
        return redirect(url_for('select_categories'))

    category_ids = [pref.category_id for pref in prefs_round1]
    
    watched_videos_subquery = db.session.query(Video.id).join(
        WatchingTime, Video.id == WatchingTime.video_id
    ).filter(
        WatchingTime.participant_number == participant_number,
        WatchingTime.round_number == 1,
        Video.category_id.in_(category_ids)
    ).subquery()
    
    available_videos = Video.query.filter(
        Video.category_id.in_(category_ids),
        ~Video.id.in_(watched_videos_subquery)
    ).all()
    
    # Group by category
    videos_by_category = {}
    for video in available_videos:
        if video.category_id not in videos_by_category:
            videos_by_category[video.category_id] = []
        videos_by_category[video.category_id].append(video)
    
    # Select one video per category
    chosen_videos = []
    selected_categories = []
    for pref in prefs_round1:
        category_videos = videos_by_category.get(pref.category_id, [])
        if not category_videos:
            # Fallback: get any video from this category
            category_videos = Video.query.filter_by(category_id=pref.category_id).all()
        
        if category_videos:
            video = random.choice(category_videos)
            chosen_videos.append({
                'id': video.id,
                'title': video.title,
                'link': video.url,
            })
            selected_categories.append(pref.category.name)

    return render_template('continue_same_categories.html', 
                         videos=chosen_videos, 
                         selected_categories=selected_categories)


@app.route('/select_categories_after_info_cocoons_round2', methods=['GET'])
@login_required_custom
def select_categories_after_info_cocoons_round2():
    participant_number = session.get('participant_number')
    if not participant_number:
        flash('未找到参与者信息。', 'danger')
        return redirect(url_for('show_intro', group_number=1))
    
    # simply allow selection from all categories again 
    remaining_categories = VideoCategory.query.filter(VideoCategory.name != 'info').all()
    
    return render_template('select_categories_after_info_cocoons_round2.html', categories=remaining_categories)


@app.route('/submit_categories_after_info_cocoons_round2', methods=['POST'])
@login_required_custom
def submit_categories_after_info_cocoons_round2():
    participant_number = session.get('participant_number')
    if not participant_number:
        flash('未找到参与者信息。', 'danger')
        return redirect(url_for('show_intro', group_number=1))
    
    # Use validation helper from utils
    error_msg, validated_data = validate_category_selection(request.form)
    if error_msg:
        flash(error_msg, 'danger')
        return redirect(url_for('select_categories_after_info_cocoons_round2'))
    
    # Use save_preferences helper (which uses db_handler internally)
    if save_preferences(participant_number, 2, validated_data):
        flash('第二次信息视频后类别选择已成功提交。', 'success')
        return redirect(url_for('video_viewing_after_info_cocoons_2'))
    else:
        # If save_preferences fails, it will handle the error logging and db rollback
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
@db_handler
def additional_information():
    participant_number = session.get('participant_number')
    participant = Participant.query.get(participant_number)
    if not participant:
        flash('参与者未找到。', 'danger')
        return redirect(url_for('show_intro', group_number=1))

    group_num = participant.group_number

    group_messages = {
        0: "",
        1: "【!! 系统检测到您已浏览了大量同质化的视频内容, 有一定概率陷入信息茧房】",
        2: "【!! 系统检测到您已浏览了大量同质化的视频内容, 有一定概率陷入信息茧房\n\n 我们十分理解并认同您对某一类视频的喜爱，我们同样希望您能通过浏览短视频获得充分的放松和愉悦。我们相信，重复单调的信息并不能满足您对于大千世界的好奇和探索欲，您完全有能力对多样化信息进行充分获取和吸收。为了进一步提升您的内容体验，我们建议您观看多样化的视频内容。】",
        3: "【!! 系统检测到您已浏览了大量同质化的视频内容, 有一定概率陷入信息茧房\n\n 信息行为研究者花费了多年时间和数以万计的成本来提高人们的信息茧房风险意识并帮助其远离信息茧房危害。您主动的多样化内容选择是帮助我们实现破茧的关键一环。为了协助我们抵御信息茧房风险，我们建议您观看多样化的视频内容。】",
        4: "【!! 系统检测到您已浏览了大量同质化的视频内容, 有一定概率陷入信息茧房\n\n 开放多元的信息环境是平台管理者和广大网民的共同愿望。各大主流短视频平台近年纷纷推出内容管理功能鼓励用户自主调节多元内容推送比例，同时，超过85%的短视频平台用户在得知信息茧房风险之后都选择观看不同类型的视频。为了共同构建包容和谐、丰富多彩的网络环境，我们建议您观看多样化的视频内容。】",
        5: "【!! 系统检测到您已浏览了大量同质化的视频内容, 有一定概率陷入信息茧房】",
        6: "【!! 系统检测到您已浏览了大量同质化的视频内容, 有一定概率陷入信息茧房\n\n 哈佛大学法学院教授、著名行为经济学家Sunstein在其著作《信息乌托邦》中深刻阐明了信息茧房对于个人身心和思维的危害并强调了浏览多样化信息内容对于缓解信息茧房的有效作用。依据权威人士的建议，我们建议您接下来观看多样化的视频内容。】",
        7: "【!! 系统检测到您已浏览了大量同质化的视频内容, 有一定概率陷入信息茧房\n\n 陷入信息茧房的人们往往是无意识的，推荐算法结合个人喜好源源不断地为用户推荐符合兴趣的内容，这使得您几乎没有机会立即分辨并主动远离信息茧房。此次实验是帮助您认识信息茧房风险并主动跳出信息茧房的难得机会，我们建议您把握此次机会，在接下来观看多样化的视频内容。】",
    }

    if request.method == 'POST':
        try:
            records_to_add = []
            chosen_strategy = None
            
            time_spent_str = request.form.get('timeSpent', '0')
            try:
                time_spent = float(time_spent_str)
                if time_spent > 0:
                    records_to_add.append(MessageTime(
                        participant_number=participant_number,
                        time_spent=time_spent
                    ))
                    app.logger.info(f"Time spent recorded: {time_spent}s for participant {participant_number}")
            except ValueError:
                app.logger.warning(f"Invalid timeSpent value: {time_spent_str} for participant {participant_number}")

            if group_num == 5:
                q1 = request.form.get('q1')
                q2 = request.form.get('q2')
                if q1 is not None and q2 is not None:
                    try:
                        records_to_add.extend([
                            ConsistencyAnswer(
                                participant_number=participant_number,
                                question_number=1,
                                answer=int(q1)
                            ),
                            ConsistencyAnswer(
                                participant_number=participant_number,
                                question_number=2,
                                answer=int(q2)
                            )
                        ])
                        app.logger.info(f"Consistency answers recorded: q1={q1}, q2={q2} for participant {participant_number}")
                    except ValueError:
                        app.logger.warning(f"Invalid consistency answers: q1={q1}, q2={q2} for participant {participant_number}")
            
            chosen_strategy = request.form.get('strategy')
            if chosen_strategy:
                records_to_add.append(CopingStrategy(
                    participant_number=participant_number,
                    strategy=chosen_strategy
                ))
                app.logger.info(f"Strategy recorded: {chosen_strategy} for participant {participant_number}")

            # 4. Add all records to the session
            if records_to_add:
                for record in records_to_add:
                    db.session.add(record)
                # db_handler will handle the commit
                app.logger.info(f"Successfully added {len(records_to_add)} records for participant {participant_number}")
            
            # 5. Handle redirects based on strategy
            if chosen_strategy:
                if chosen_strategy == 'watch_other':
                    return redirect(url_for('select_categories_round2'))
                elif chosen_strategy == 'learn_more':
                    return redirect(url_for('info_cocoons'))
                else:  # 'avoidance' or other strategies
                    return redirect(url_for('continue_same_categories'))
            
            # Fallback if no strategy selected
            return redirect(url_for('coping_strategy'))
        
        except Exception as e:
            # db_handler will handle rollback
            app.logger.error(f"Error in additional_information for participant {participant_number}: {str(e)}")
            flash('处理请求时发生错误，请稍后再试。', 'danger')
            return redirect(url_for('additional_information'))

    # GET request - render the template
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



