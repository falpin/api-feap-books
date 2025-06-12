from database import *
import logging
from logging.handlers import RotatingFileHandler
import random
import string
import secrets
import json
from datetime import datetime, timedelta
import secrets
import string
import jwt
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import SECRET_KEY, JWT_ACCESS_EXPIRES_HOURS, ALLOWED_API_KEYS

formatter = logging.Formatter('%(levelname)s [%(asctime)s]   %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
try:
    file_handler = RotatingFileHandler('/var/log/olympiad/api.log', maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
except:
    file_handler = RotatingFileHandler('api.log', maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
file_handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)




def add_time_to_datetime(old_time_str, time_delta_str):
    if old_time_str is None:
        dt = datetime.now()
    else:
        dt = datetime.strptime(old_time_str, "%Y-%m-%d %H:%M:%S")

    hours, minutes = map(int, time_delta_str.split(':'))
    delta = timedelta(hours=hours, minutes=minutes)

    new_dt = dt + delta

    return new_dt.strftime("%Y-%m-%d %H:%M:%S")


# Вспомогательные функции
def validate_required_fields(data, required_fields):
    """Проверяет наличие обязательных полей в данных."""
    for field in required_fields:
        if not data.get(field):
            return ({"error": f"Поле '{field}' обязательно"}), 400
    return None

def authenticate_user(login, password=None, telegram_id=None):
    """Аутентифицирует пользователя по паролю или telegram_id."""
    if password is not None:
        user = SQL_request("SELECT * FROM users WHERE login = ?;", (login,), fetch='one')
        if not user:
            new_password = generate_password_hash(password)
            insert_user(login, new_password)
            user = SQL_request("SELECT * FROM users WHERE login = ?;", (login,), fetch='one')
        
        if user["password"]:
            if not check_password_hash(user['password'], password):
                return ({"error": "Неверный логин или пароль"}), 401
        else:
            return ({"error": "Неверный логин или пароль"}), 401
    else:
        user = SQL_request("SELECT * FROM users WHERE login = ?;", (login,), fetch='one')
        if not user:
            insert_user(login, telegram_id=telegram_id)
            user = SQL_request("SELECT * FROM users WHERE login = ?;", (login,), fetch='one')
        if not user['telegram_id']:
                SQL_request("UPDATE users SET telegram_id = ? WHERE login = ?", (telegram_id, login))

        SQL_request("UPDATE users SET login = ? WHERE telegram_id = ?", (login, telegram_id))
    
    return user

def generate_auth_response(user):
    """Генерирует JWT токен и формирует ответ."""
    token = jwt.encode({
        'user_id': user["id"],
        'login': user['login'],
        'role': user['role'],
        'exp': datetime.utcnow() + timedelta(days=365)
    }, SECRET_KEY, algorithm="HS256")
    
    user_data = user.copy()
    if 'password' in user_data:
        del user_data['password']
    
    return {
        "message": "Успешный вход",
        "token": token,
        "user": user_data
    }, 200