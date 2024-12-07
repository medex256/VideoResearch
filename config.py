from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy



app  = Flask(__name__)

app.secret_key = "secret-key-here"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydatabase.db"


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app,db)