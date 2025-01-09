from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash  # Безопасные методы для паролей
import os
from flask_migrate import Migrate

# Инициализация приложения Flask
app = Flask(__name__)

# Настройка базы данных и конфигурации
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)  # Генерация случайного ключа для безопасности

# Инициализация расширений
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Редирект на страницу логина
migrate = Migrate(app, db)  # Инициализация миграций

# Модель для книги
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"Book('{self.title}', {self.price})"


# Модель для пользователя
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    def set_password(self, password):
        """Метод для хеширования пароля"""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Метод для проверки пароля"""
        return check_password_hash(self.password, password)


# Загрузка пользователя
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Главная страница
@app.route("/", methods=["GET", "POST"])
def index():
    search_query = request.args.get("search")  # Получаем поисковый запрос
    if search_query:
        books = Book.query.filter(Book.title.ilike(f"%{search_query}%")).all()  # Фильтруем книги по запросу
    else:
        books = Book.query.all()  # Если нет запроса, выводим все книги
    return render_template('index.html', books=books, search_query=search_query)


# Страница "О нас"
@app.route("/about")
def about():
    return render_template('about.html')


# Страница логина
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):  # Проверка пароля с использованием check_password
            login_user(user)
            flash("Вы успешно вошли в систему!", "success")
            return redirect(url_for('index'))
        else:
            flash('Неверные имя пользователя или пароль', 'danger')  # Сообщение об ошибке

    return render_template('login.html')


# Страница регистрации
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password)

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует.', 'danger')
            return redirect(url_for('signup'))

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)  # Логиним пользователя после регистрации
        flash('Регистрация прошла успешно. Вы вошли в систему.', 'success')
        return redirect(url_for('index'))

    return render_template('signup.html')


# Страница выхода
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# Страница оформления заказа
@app.route("/checkout/<int:book_id>")
def checkout(book_id):
    # Получаем информацию о книге по ID
    book = Book.query.get_or_404(book_id)
    return render_template('checkout.html', book=book)


# Страница завершения оформления заказа
@app.route("/complete_checkout/<int:book_id>", methods=["POST"])
def complete_checkout(book_id):
    book = Book.query.get_or_404(book_id)

    name = request.form['name']
    address = request.form['address']

    flash(f"Покупка книги '{book.title}' прошла успешно! Ваш заказ будет отправлен на адрес: {address}.", "success")

    return redirect(url_for('index'))


# Страница аккаунта
@app.route("/account")
@login_required
def account():
    return render_template('account.html', user=current_user)


# Страница корзины
@app.route("/cart")
@login_required
def cart():
    cart_books = []
    if 'cart' in session:
        cart_books = Book.query.filter(Book.id.in_(session['cart'])).all()

    total_price = sum(book.price for book in cart_books)

    return render_template('cart.html', cart_books=cart_books, total_price=total_price)


# Добавить книгу в корзину
@app.route("/add_to_cart/<int:book_id>")
def add_to_cart(book_id):
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append(book_id)
    session.modified = True
    flash('Книга добавлена в корзину', 'success')
    return redirect(url_for('index'))


# Удалить книгу из корзины
@app.route("/remove_from_cart/<int:book_id>", methods=["POST"])
def remove_from_cart(book_id):
    if 'cart' in session:
        session['cart'] = [book for book in session['cart'] if book != book_id]
        session.modified = True
        flash('Книга удалена из корзины', 'success')
    return redirect(url_for('cart'))


# Очистить корзину
@app.route("/clear_cart")
def clear_cart():
    session.pop('cart', None)
    flash('Корзина очищена', 'success')
    return redirect(url_for('cart'))


# Создание базы данных и начальные данные
@app.before_request
def create_tables():
    db.create_all()

    if User.query.count() == 0:
        # Добавление стандартного пользователя
        user = User(username="admin", password=generate_password_hash("admin"))
        db.session.add(user)
        db.session.commit()

    if Book.query.count() == 0:
        books = [
            Book(title="The Great Gatsby", price=10.99, description="A novel by F. Scott Fitzgerald."),
            Book(title="1984", price=8.99, description="A dystopian novel by George Orwell."),
            Book(title="To Kill a Mockingbird", price=12.49, description="A novel by Harper Lee."),
            Book(title="Pride and Prejudice", price=6.99, description="A classic novel by Jane Austen."),
            Book(title="The Catcher in the Rye", price=9.99, description="A novel by J.D. Salinger."),
            Book(title="Moby Dick", price=11.99, description="A novel by Herman Melville."),
            Book(title="War and Peace", price=14.99, description="A historical novel by Leo Tolstoy."),
            Book(title="The Odyssey", price=7.49, description="An epic poem by Homer."),
            Book(title="The Hobbit", price=13.99, description="A fantasy novel by J.R.R. Tolkien.")
        ]
        db.session.bulk_save_objects(books)
        db.session.commit()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)  # Указываем хост и порт явно


