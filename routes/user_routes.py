from .main_routes import *


@api.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    required_fields = ['login', 'password']
    if error := validate_required_fields(data, required_fields):
        return error
    
    login = data['login']
    password = data['password']
    
    user = authenticate_user(login, password=password)
    if isinstance(user, tuple):
        return user

    return jsonify(generate_auth_response(user))

@api.route('/login/telegram', methods=['POST'])
def login_telegram():
    data = request.get_json()
    
    # Проверка обязательных полей
    required_fields = ['login', 'telegram_id']
    if error := validate_required_fields(data, required_fields):
        return error
    
    login = data['login']
    telegram_id = data['telegram_id']
    
    user = authenticate_user(login, telegram_id=telegram_id)
    if isinstance(user, tuple):
        return user
    
    SQL_request("UPDATE users SET login = ? WHERE telegram_id = ?", (login, telegram_id))

    return jsonify(generate_auth_response(user))


@api.route('/profile', methods=['GET'])
def profile():
    try:
        user = g.user
        SQL_request(
                "UPDATE users SET last_login = datetime('now') WHERE id = ?",
                params=(user['id'],),
                fetch='none'
            )
        return jsonify({"message": user}), 200
    except:
        return jsonify({"error": f"Ошибка на сервере"}), 500