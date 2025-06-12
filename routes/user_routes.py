from .main_routes import *

@api.route('/registration', methods=['POST'])
def registration():
    data = request.get_json()
    
    required_fields = ['login', 'password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"Поле '{field}' обязательно"}), 400

    login = data['login']
    password = data['password']

    # Проверяем, существует ли пользователь
    existing_user = SQL_request("SELECT id FROM users WHERE login = ?", params=(login,), fetch='one')
    if existing_user:
        return jsonify({"error": "Этот логин занят"}), 400

    password = generate_password_hash(password)

    try:
        insert_user(login, password)
        user = SQL_request("SELECT * FROM users WHERE login = ?;", (login,), fetch='one')

        token = jwt.encode({
            'user_id': user["id"],
            'login': login,
            'role': "user",
            'exp': datetime.utcnow() + timedelta(days=365)
        }, SECRET_KEY, algorithm="HS256")

        del user['password']
        return jsonify({"token": token, "user": user}), 200

    except Exception as e:
        logging.error(f"Ошибка регистрации: {e}")
        return jsonify({"error": "Ошибка регистрации"}), 500
    return jsonify({"message": "Успешная регистрация"}), 200


@api.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    required_fields = ['login', 'password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"Поле '{field}' обязательно"}), 400

    login = data['login']
    password = data['password']
    user = SQL_request("SELECT * FROM users WHERE login = ?;", (login,), fetch='one')

    if not user:
        return jsonify({"error": "Неверный логин или пароль"}), 401

    if not check_password_hash(user['password'], password):
        return jsonify({"error": "Неверный логин или пароль"}), 401

    token = jwt.encode({
            'user_id': user["id"],
            'login': login,
            'role': "user",
            'exp': datetime.utcnow() + timedelta(days=365)
        }, SECRET_KEY, algorithm="HS256")

    del user['password']
    return jsonify({"token": token, "user": user}), 200

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