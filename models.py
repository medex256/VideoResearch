from config import db
from sqlalchemy.orm import declared_attr, declarative_mixin

from flask_login import UserMixin
from datetime import datetime


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    participant_number = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(200), unique=True, nullable=False)
    ip = db.Column(db.String(200), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    group = db.Column(db.Integer, nullable=False)
    
    preferences = db.relationship('Preference', backref='user', lazy=True)
    video_interactions = db.relationship('VideoInteraction', backref='user', lazy=True)
    coping_strategies = db.relationship('CopingStrategy', backref='user', lazy=True)
    message_times = db.relationship('PersuasiveMessageTime', backref='user', lazy=True)
    watching_times = db.relationship('VideoWatchingTime', backref='user', lazy=True)
    consistency_answers = db.relationship('ConsistencyAnswer', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class Preference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_number = db.Column(db.String(50), db.ForeignKey('user.participant_number'), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)  # 1 or 2
    category = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=True)  # Optional if ratings are provided
    
    def __repr__(self):
        return f'<Preference {self.category} Round {self.round_number}>'

class VideoInteraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_number = db.Column(db.String(50), db.ForeignKey('user.participant_number'), nullable=False)
    video_id = db.Column(db.String(200), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # 'like', 'dislike', 'collect', 'comment'
    content = db.Column(db.String, nullable=True)  # Comment content if applicable
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Interaction {self.action} on Video {self.video_id}>'

class CopingStrategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_number = db.Column(db.String(50), db.ForeignKey('user.participant_number'), nullable=False)
    strategy = db.Column(db.String(50), nullable=False)  # 'watch_other', 'learn_more', 'avoidance'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CopingStrategy {self.strategy}>'

class PersuasiveMessageTime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_number = db.Column(db.String(50), db.ForeignKey('user.participant_number'), nullable=False)
    time_spent = db.Column(db.Float, nullable=False)  # Time in seconds
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MessageTime {self.time_spent} seconds>'

class VideoWatchingTime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_number = db.Column(db.String(50), db.ForeignKey('user.participant_number'), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)  # 1 or 2
    time_spent = db.Column(db.Float, nullable=False)  # Time in seconds
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<WatchingTime Round {self.round_number} - {self.time_spent} seconds>'

class ConsistencyAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_number = db.Column(db.String(50), db.ForeignKey('user.participant_number'), nullable=False)
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ConsistencyAnswer {self.question}>'

# Existing Models Revised

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(200), nullable=False)
    ip = db.Column(db.String(200), nullable=False)
    video_id = db.Column(db.String(200), nullable=False)
    like = db.Column(db.Boolean, nullable=True)
    dislike = db.Column(db.Boolean, nullable=True)
    comments = db.Column(db.String, nullable=True)
    group = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Note {self.id}>'

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(200), nullable=False)
    ip = db.Column(db.String(200), nullable=False)
    video_id = db.Column(db.String(200), nullable=False)
    percent_watched = db.Column(db.Float, nullable=True)
    paused = db.Column(db.Boolean, nullable=True)
    finished = db.Column(db.Boolean, nullable=True)

    def __repr__(self):
        return f'<Activity {self.id}>'







