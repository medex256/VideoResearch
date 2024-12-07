from config import db
from sqlalchemy.orm import declared_attr, declarative_mixin



from flask_login import UserMixin
from datetime import datetime
import uuid


class Participant(UserMixin, db.Model):
    participant_number = db.Column(db.String(4), primary_key=True, default=lambda: '0000')
    group_number = db.Column(db.Integer, nullable=False)  # Assigned group (1-7)
    # Relationships
    preferences = db.relationship('Preference', backref='participant', lazy=True)
    interactions = db.relationship('VideoInteraction', backref='participant', lazy=True)
    coping_strategies = db.relationship('CopingStrategy', backref='participant', lazy=True)
    message_times = db.relationship('MessageTime', backref='participant', lazy=True)
    watching_times = db.relationship('WatchingTime', backref='participant', lazy=True)
    consistency_answers = db.relationship('ConsistencyAnswer', backref='participant', lazy=True)

    def get_id(self):
        return self.participant_number

class VideoCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_cn = db.Column(db.String(100), nullable=True)
    # Relationships
    videos = db.relationship('Video', backref='category', lazy=True)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('video_category.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    duration = db.Column(db.Integer)
    tags = db.Column(db.String(500))
    likes = db.Column(db.String(50))
    forwards = db.Column(db.String(50))

class Preference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_number = db.Column(db.String(50), db.ForeignKey('participant.participant_number'), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)  # 1 or 2
    category_id = db.Column(db.Integer, db.ForeignKey('video_category.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # Rating from 1 to 10
    # Relationships
    category = db.relationship('VideoCategory')

class CopingStrategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_number = db.Column(db.String(50), db.ForeignKey('participant.participant_number'), nullable=False)
    strategy = db.Column(db.String(50), nullable=False)  # Options: 'watch_other', 'learn_more', 'avoidance'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class VideoInteraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_number = db.Column(db.String(50), db.ForeignKey('participant.participant_number'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # 'like', 'dislike', 'collect', 'comment'
    content = db.Column(db.String, nullable=True)  # For comments
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class MessageTime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_number = db.Column(db.String(50), db.ForeignKey('participant.participant_number'), nullable=False)
    time_spent = db.Column(db.Float, nullable=False)  # Time in seconds
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class WatchingTime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_number = db.Column(db.String(50), db.ForeignKey('participant.participant_number'), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)  # 1 or 2
    time_spent = db.Column(db.Float, nullable=False)  # Time in seconds
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ConsistencyAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_number = db.Column(db.String(50), db.ForeignKey('participant.participant_number'), nullable=False)
    question_number = db.Column(db.Integer, nullable=False)  # To identify which question (1 or 2)
    answer = db.Column(db.Integer, nullable=False)  # Rating from 0 to 10
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)







