
from flask import Flask, render_template, redirect, url_for, request,flash
from flask_login import LoginManager, login_user, login_required, current_user
from config import app,db
from models import User




login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return render_template('index.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        # Implement authentication logic here
        user = User.query.filter_by(username=username).first()
        if user:
            login_user(user)
            return redirect(url_for('select_categories', round_number=1))
        else:
            flash('Invalid username')
    return render_template('login.html')



if __name__ =="__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)