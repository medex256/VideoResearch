from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

import sqlitecloud



app  = Flask(__name__)

app.secret_key = "secret-key-here"

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://admin:Lol2002004!@database-1.cf86gyawodle.ap-southeast-1.rds.amazonaws.com:3306/"


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db = SQLAlchemy(app)
migrate = Migrate(app,db)