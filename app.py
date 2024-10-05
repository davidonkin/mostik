from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Настройки базы данных (SQLite для простоты)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(10), default='user')  # Роль пользователя (user, partner, admin)
    projects = db.relationship('Project', backref='user', lazy=True)

# Модель проекта
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    daily_limit = db.Column(db.Integer, nullable=False)
    sources = db.Column(db.String(500), nullable=False)  # Храним источники как строку с разделителями
    status = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Создаем таблицы
with app.app_context():
    db.create_all()

    # Создаем администратора, если он еще не существует
    if not User.query.filter_by(phone='admin').first():
        admin_user = User(
            phone='admin', 
            password=generate_password_hash('admin'),  # Используем хешированный пароль
            email='admin@example.com', 
            role='admin'
        )
        db.session.add(admin_user)
        db.session.commit()

# Главная страница (по умолчанию – login)
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        user = User.query.filter_by(phone=phone).first()
        if user and check_password_hash(user.password, password):  # Используем хеш для проверки пароля
            session['user'] = user.phone  # Сохраняем телефон пользователя в сессии
            session['role'] = user.role  # Сохраняем роль пользователя в сессии
            if user.role == 'admin':
                return jsonify({'redirect': url_for('admin_panel')})  # Перенаправление на страницу админ-панели
            else:
                return jsonify({'redirect': url_for('project_management')})  # Перенаправление на страницу управления проектами
        return jsonify({'message': 'Неверный телефон или пароль'}), 400  # Ошибка
    return render_template('login.html')

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        email = request.form['email']
        if User.query.filter_by(phone=phone).first():
            return jsonify({'message': 'Пользователь с таким телефоном уже существует'}), 400
        new_user = User(phone=phone, password=generate_password_hash(password), email=email)  # Хешируем пароль
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# Функция для валидации источников
def validate_sources(sources):
    regex = r'^(https?://)?([a-z0-9-]+\.)+[a-z]{2,6}([/\w.-]*)*/?$'  # Regex для веб-сайтов
    phone_regex = r'^7\d{10}$'  # Regex для номера телефона в формате 79999999999
    errors = []

    # Проверка на дубли
    unique_sources = set(sources)
    if len(unique_sources) < 5:
        errors.append('Пожалуйста, введите как минимум 5 уникальных источников.')

    # Проверка формата источников
    for source in unique_sources:
        if not (re.match(regex, source) or re.match(phone_regex, source)):
            errors.append(f'{source} не является корректным веб-сайтом или номером телефона.')

    return errors

# Маршрут для страницы управления проектами
@app.route('/project_management', methods=['GET', 'POST'])
def project_management():
    if 'user' not in session:
        return redirect(url_for('login'))  # если пользователь не авторизован, перенаправляем на login

    user = User.query.filter_by(phone=session['user']).first()
    if request.method == 'POST':
        data = request.get_json()
        project_name = data.get('project_name')
        daily_limit = data.get('daily_limit')
        sources = data.get('sources', [])  # Здесь sources передаются как массив

        # Валидация источников
        validation_errors = validate_sources(sources)
        if validation_errors:
            return jsonify({'message': 'Ошибка в источниках: ' + ', '.join(validation_errors)}), 400

        # Сохраняем источники как строку, объединяя массив через запятую
        new_project = Project(
            name=project_name,
            daily_limit=daily_limit,
            sources=','.join(sources),  # Источники объединяются через запятую
            user_id=user.id
        )
        db.session.add(new_project)
        db.session.commit()

        return jsonify({'message': 'Проект успешно создан!', 'project_id': new_project.id})

    projects = Project.query.filter_by(user_id=user.id).all()
    return render_template('project_management.html', projects=projects)

# Редактирование проекта
@app.route('/project_management/<int:project_id>', methods=['PUT'])
def edit_project(project_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    project = Project.query.get_or_404(project_id)
    if project.user.phone != session['user']:
        return abort(403)  # Запрет доступа, если проект не принадлежит пользователю

    data = request.get_json()
    project.name = data.get('project_name')
    project.daily_limit = data.get('daily_limit')
    project.sources = ','.join(data.get('sources', []))  # Обновляем источники
    db.session.commit()
    return jsonify({'message': 'Проект успешно обновлен!'})

# Удаление проекта
@app.route('/project_management/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    project = Project.query.get_or_404(project_id)
    if project.user.phone != session['user']:
        return abort(403)  # Запрет доступа, если проект не принадлежит пользователю

    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Проект успешно удален!'})

# Копирование проекта
@app.route('/project_management/<int:project_id>/copy', methods=['POST'])
def copy_project(project_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    original_project = Project.query.get_or_404(project_id)
    if original_project.user.phone != session['user']:
        return abort(403)  # Запрет доступа, если проект не принадлежит пользователю

    new_project = Project(
        name=f'Копия {original_project.name}',
        daily_limit=original_project.daily_limit,
        sources=original_project.sources,
        user_id=original_project.user_id
    )
    db.session.add(new_project)
    db.session.commit()
    return jsonify({'message': 'Проект успешно скопирован!', 'project_id': new_project.id})

# Переключение статуса проекта
@app.route('/project_management/<int:project_id>/status', methods=['PATCH'])
def change_project_status(project_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    project = Project.query.get_or_404(project_id)
    if project.user.phone != session['user']:
        return abort(403)  # Запрет доступа, если проект не принадлежит пользователю

    data = request.get_json()
    project.status = data.get('status', False)
    db.session.commit()
    return jsonify({'message': 'Статус проекта успешно обновлен!'})

# Маршрут для админ-панели
@app.route('/admin_panel')
def admin_panel():
    if 'user' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))  # Перенаправление на страницу логина, если не админ

    users = User.query.all()  # Получение всех пользователей для админ-панели
    return render_template('admin_panel.html', users=users)

# Выход
@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('role', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
