
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, login_user, login_required, current_user
from config import app, db
from functools import wraps
from models import Participant,VideoCategory,Video,Preference
import random
import uuid


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
    selected_ids = request.form.getlist('categories')  # Get list of selected category IDs
    if len(selected_ids) != 3:
        flash('请确保选择了三个类别并为其分配排名。', 'danger')
        return redirect(url_for('select_categories'))
    
    ratings = []
    for category_id in selected_ids:
        rating = request.form.get(f'rating_{category_id}')
        if not rating or not rating.isdigit():
            flash('请为所有选择的类别分配有效的排名。', 'danger')
            return redirect(url_for('select_categories'))
        ratings.append(int(rating))
    
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
                    round_number=1,  #first round
                    category_id=category_id,
                    rating=rating
                )
                db.session.add(preference)
            db.session.commit()
            flash('类别已成功提交。', 'success')
            return redirect(url_for('next_step'))  # Test
        except Exception as e:
            db.session.rollback()
            flash('提交时发生错误，请稍后再试。', 'danger')
            return redirect(url_for('select_categories'))
    else:
        flash('参与者未找到。', 'danger')
        return redirect(url_for('index'))





@app.route('/next_step')
@login_required_custom
def next_step():
    #For Testing
    return render_template('next_step.html')


@app.route('/select_categories')
@login_required_custom
def select_categories():
    categories = VideoCategory.query.all()
    return render_template('select_categories.html', categories=categories)


if __name__ =="__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)