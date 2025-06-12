from .main_routes import *
from werkzeug.utils import secure_filename
import uuid

UPLOAD_IMAGE = f"{UPLOAD_FOLDER}/books/image"
UPLOAD_BOOKS = f"{UPLOAD_FOLDER}/books"
ALLOWED_BOOK_EXTENSIONS = config.ALLOWED_BOOK_EXTENSIONS


def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def generate_filename(original_filename):
    # Генерируем уникальное имя файла: timestamp + uuid + оригинальное расширение
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4().hex)[:8]
    extension = original_filename.rsplit('.', 1)[1].lower()
    return f"{timestamp}_{unique_id}.{extension}"

@api.route('/books/add', methods=['POST'])
@auth_decorator()
def add_book():
    try:
        # Создаем необходимые директории, если они не существуют
        os.makedirs(UPLOAD_IMAGE, exist_ok=True)
        os.makedirs(UPLOAD_BOOKS, exist_ok=True)
   
        # Обработка изображения
        if 'image' not in request.files:
            return jsonify({"error": "Отсутствует изображение"}), 400
        
        image_file = request.files['image']
        
        if image_file.filename == '':
            return jsonify({"error": "Не выбрано изображение"}), 400
            
        if not allowed_file(image_file.filename, ALLOWED_EXTENSIONS):
            return jsonify({"error": "Тип изображения не поддерживается"}), 400
        
        # Обработка файла книги
        if 'book_file' not in request.files:
            return jsonify({"error": "Отсутствует файл книги"}), 400
        
        book_file = request.files['book_file']
        
        if book_file.filename == '':
            return jsonify({"error": "Не выбран файл книги"}), 400
            
        if not allowed_file(book_file.filename, ALLOWED_BOOK_EXTENSIONS):
            return jsonify({"error": "Тип файла книги не поддерживается"}), 400

        
        # Генерируем уникальные имена файлов
        image_filename = generate_filename(image_file.filename)
        book_filename = generate_filename(book_file.filename)
        
        # Сохраняем файлы
        image_path = os.path.join(UPLOAD_IMAGE, image_filename)
        book_path = os.path.join(UPLOAD_BOOKS, book_filename)
        
        image_file.save(image_path)
        book_file.save(book_path)
        
        # Получаем остальные данные формы
        name = request.form.get('name')
        if not name:
            return jsonify({"error": "Название книги обязательно"}), 400
        
        author = request.form.get('author', '')
        description = request.form.get('description', '')
        
        user = g.user
        # Вставляем книгу в базу данных
        SQL_request(
            "INSERT INTO books (name, author, description, image, file_path, created_at, user_create) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, author, description, image_filename, book_filename, datetime('now'), int(user['id']))
        )
        print("Тут")
        
        # Получаем ID добавленной книги
        book_id = SQL_request("SELECT last_insert_rowid()")[0][0]
        
        return jsonify({
            "message": "Книга успешно добавлена",
            "book_id": book_id,
            "image_path": image_path,
            "book_path": book_path
        }), 201

    except Exception as e:
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500