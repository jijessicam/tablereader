#----------------------------------------------------#
# IMPORTS
#----------------------------------------------------#

from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy 
from flask_migrate import Migrate 
import os, json, boto3
from flask_bootstrap import Bootstrap 

#----------------------------------------------------#
# CONFIG
#----------------------------------------------------#

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bootstrap = Bootstrap(app)

from app import routes, models, errors