from flask import Flask, render_template, redirect, request, session, flash #, jsonify
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError

from helpers import apology


# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

    # Flask-SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = 'sqlite:///planner.db'    # File-based SQL database
    SQLALCHEMY_TRACK_MODIFICATIONS = False              # Avoids SQLAlchemy warning

    # Flask-User settings
    USER_APP_NAME = "Absence Planner"   # Shown in and email templates and page footers
    USER_ENABLE_EMAIL = False           # Disable email authentication
    USER_ENABLE_USERNAME = True         # Enable username authentication
    USER_ENABLE_REGISTER = False        # Do not allow unregistered users to register.

    # Ensure templates are auto-reloaded
    TEMPLATES_AUTO_RELOAD = True

    # Configure session to use filesystem (instead of signed cookies)
    SESSION_FILE_DIR = mkdtemp()
    SESSION_PERMANENT = False
    SESSION_TYPE = "filesystem"


# Create Flask app load app.config
app = Flask(__name__)
app.config.from_object(__name__+'.ConfigClass')

# Initialize database
db = SQLAlchemy(app)

# Initialize session
Session(app)

# import data-models
import models
# import views
import views

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)