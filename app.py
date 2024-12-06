
from flask import Flask, render_template, redirect, url_for, request,flash
from flask_login import LoginManager, login_user, login_required, current_user
from config import app,db
from models import Participant




login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)




@app.route('/')
def index():
    return render_template('index.html')






if __name__ =="__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)