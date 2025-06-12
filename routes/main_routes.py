from database import SQL_request, insert_user
from flask import Blueprint, jsonify, request, abort, g, send_file
from functools import wraps
import jwt
import logging
from middleware import setup_middleware, auth_decorator
import config
from utils import *
import io
from datetime import datetime


SECRET_KEY = config.SECRET_KEY
UPLOAD_FOLDER = config.UPLOAD_FOLDER
ALLOWED_EXTENSIONS = config.ALLOWED_EXTENSIONS

api = Blueprint('api', __name__)


@api.route('/', methods=['GET'])
def example():
    return jsonify({"message": f"API Работает. Версия: {config.VERSION}"}), 200