from functools import wraps
import jwt
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import json
import os
from flask import request, jsonify, abort, g
from database import SQL_request

# === Настройка логгера для аудита ===
audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.INFO)

SECRET_KEY = os.getenv("SECRET_KEY")

# Проверяем, существует ли уже обработчик, чтобы не дублировать
if not audit_logger.handlers:
    audit_handler = RotatingFileHandler('audit.log', maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
    audit_formatter = logging.Formatter('%(levelname)s [%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    audit_handler.setFormatter(audit_formatter)
    audit_logger.addHandler(audit_handler)


def auth_decorator(role='user', check_self=True):
    """
    Универсальный декоратор для аутентификации и авторизации.

    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                abort(401, description="JWT токен отсутствует")

            try:
                token = auth_header.split(" ")[1]
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

                # Проверка роли
                if role:
                    user_role = payload.get('role', 'user')
                    allowed_roles = {
                        'developer': ['developer'],
                        'admin': ['developer', 'admin'],
                        'user': ['developer', 'developer', 'user']
                    }

                    if user_role not in allowed_roles.get(role, []):
                        abort(403, description=f"Нет прав: требуется роль {role}")

                    if payload.get('user_id') == 'computer':
                        computer = SQL_request("SELECT * FROM computers WHERE token = ?", params=(token,), fetch='one')
                        if computer:
                            user_role = f"{user_role} {computer['id']}"
                        else:
                            abort(401, description="Компьютер не найден")

                    # Логирование
                    audit_logger.info(
                        f"{payload['login']} ({user_role}) вызвал маршрут {request.path} | IP: {request.remote_addr}"
                    )

                # Получение данных пользователя
                if check_self or role:
                    user_id = payload.get('user_id')
                    if not user_id:
                        abort(401, description="Неверный токен: отсутствует идентификатор пользователя")

                    if user_id == "computer":
                        computer = SQL_request("SELECT * FROM computers WHERE token = ?", params=(token,), fetch='one')
                        g.computer = computer

                    elif user_id == "password":
                        email = payload.get("email")
                        if not email:
                            abort(404, description="Неверный токен: отсутствует почта")
                        user = SQL_request("SELECT * FROM users WHERE email = ?", params=(email,), fetch='one')
                        if not user:
                            abort(404, description="Пользователь не найден")
                        g.user = user

                    else: 
                        user = SQL_request("SELECT * FROM users WHERE id = ?", params=(user_id,), fetch='one')
                        if not user:
                            abort(404, description="Пользователь не найден")
    
                        g.user = user
    
                        # Проверка, что пользователь может редактировать только себя
                        if (check_self and 'user_id' in kwargs and str(kwargs['user_id']) != str(user_id)) or (user_role == 'admin'):
                            abort(403, description="Вы можете управлять только своими данными")

            except jwt.ExpiredSignatureError:
                abort(401, description="Срок действия токена истёк")
            except jwt.InvalidTokenError:
                abort(401, description="Неверный токен")

            return func(*args, **kwargs)
        return wrapper
    return decorator


# === Middleware для автоматической проверки API-ключа и логирования ===
def setup_middleware(app):
    @app.before_request
    def api_key_and_logging_middleware():
        excluded_routes = ['/registration', '/login', '/login/telegram']
        if request.path in excluded_routes or request.method == 'OPTIONS':
            return None

        if request.url_rule and request.url_rule.rule.startswith('/images/'):
            return None

        # Проверка на наличие JWT токена
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            auth_decorator()
            return None


        api_key = request.headers.get('X-API-Key')
        if api_key:
            base = api_key.split(",")
            api_key = base[0]
        if not api_key:
            return jsonify({"error": "API ключ отсутствует"}), 401

        if api_key not in app.config.get('ALLOWED_API_KEYS', []):
            return jsonify({"error": "Неверный API ключ"}), 403

        # Сохраняем время начала запроса
        request._start_time = datetime.now()
        if len(base) > 1:
            telegram_id = base[1].replace("telegram_id=","")
            user = SQL_request("SELECT * FROM users WHERE telegram_id = ?", params=(telegram_id,), fetch='one')
            g.user = user
        return None

    @app.after_request
    def log_request_info(response):
        if hasattr(request, '_start_time'):
            elapsed = (datetime.now() - request._start_time).total_seconds() * 1000  # в мс
            logging.info(f"{request.remote_addr} {request.method} {request.path} → {response.status} за {int(elapsed)}ms")
        return response