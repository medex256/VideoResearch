from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

import sqlitecloud



app  = Flask(__name__)

app.secret_key = "secret-key-here"

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://u3dmiywrwj3ignqx:nbb2d11TheFaD67PbM50@bwdnizuvr3xuibcrnls5-mysql.services.clever-cloud.com:3306/bwdnizuvr3xuibcrnls5"


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db = SQLAlchemy(app)
migrate = Migrate(app,db)