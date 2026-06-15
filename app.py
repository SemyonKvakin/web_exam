from flask import Flask, render_template, send_from_directory, request
from flask_migrate import Migrate
from sqlalchemy.exc import SQLAlchemyError
from models import db, Book, Cover
from auth import bp as auth_bp, init_login_manager
from books import bp as books_bp
from reviews import bp as reviews_bp

app = Flask(__name__)
application = app

app.config.from_pyfile('config.py')

db.init_app(app)
migrate = Migrate(app, db)

init_login_manager(app)


@app.errorhandler(SQLAlchemyError)
def handle_sqlalchemy_error(err):
    error_msg = ('Возникла ошибка при подключении к базе данных. '
                 'Повторите попытку позже.')
    return f'{error_msg} (Подробнее: {err})', 500


app.register_blueprint(auth_bp)
app.register_blueprint(books_bp)
app.register_blueprint(reviews_bp)


@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    query = db.select(Book).order_by(Book.year.desc(), Book.id.desc())
    pagination = db.paginate(query, page=page, per_page=app.config['PER_PAGE'])
    return render_template('index.html',
                           books=pagination.items,
                           pagination=pagination)


@app.route('/covers/<cover_id>')
def cover(cover_id):
    img = db.get_or_404(Cover, cover_id)
    return send_from_directory(app.config['UPLOAD_FOLDER'], img.storage_filename)
