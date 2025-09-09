"""
Simplified Flask application using blueprints for better organization.
This is the main application entry point with clean separation of concerns.
"""
from flask_login import LoginManager
from config import app, db
from models import Participant
from flask_migrate import Migrate

migrate = Migrate(app, db)

# Import blueprints
from blueprints.main import main_bp
from blueprints.api import api_bp
from blueprints.round2 import round2_bp

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)
app.register_blueprint(round2_bp)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return Participant.query.get(user_id)


# Keep legacy routes for testing and development
@app.route('/test_video')
def test_video():
    from flask import render_template
    return render_template('test_video.html')


@app.route('/test_embed')
def test_embed_legacy():
    """Test embed functionality - development only (legacy route)."""
    from flask import render_template
    # Example Douyin video URL
    douyin_video_url = "https://open.douyin.com/player/video?vid=7290445158779276601&autoplay=0"
    return render_template('test_embed.html', video_url=douyin_video_url)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
