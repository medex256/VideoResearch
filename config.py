from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy



app  = Flask(__name__)

app.secret_key = "secret-key-here"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlitecloud://cvrm0nakhz.g4.sqlite.cloud:8860/chinook.sqlite?apikey=28LhdU8oT71PsIIEqoFcgHgl5kL3NQm1Is6IqYHdhAI"


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app,db)