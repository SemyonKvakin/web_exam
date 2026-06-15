import os
import bleach
import markdown
from flask import (Blueprint, render_template, request, flash, redirect,
                   url_for, current_app)
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from models import db, Book, Genre, Cover, Review, ReviewStatus
from tools import CoverSaver, roles_required

bp = Blueprint('books', __name__, url_prefix='/books')

BOOK_PARAMS = ['name', 'short_desc', 'year', 'publisher', 'author', 'pages']

ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'b', 'i', 'u', 'ol', 'ul', 'li',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code',
                'pre', 'a', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td']


def book_params():
    return {p: request.form.get(p) or None for p in BOOK_PARAMS}


def render_md(text):
    return markdown.markdown(bleach.clean(text or '', tags=ALLOWED_TAGS, strip=True))


@bp.route('/<int:book_id>')
def show(book_id):
    book = db.get_or_404(Book, book_id)
    full_desc_html = render_md(book.short_desc)
    approved = [r for r in book.reviews if r.status and r.status.name == 'одобрена']
    approved.sort(key=lambda r: r.created_at, reverse=True)
    for r in approved:
        r.text_html = render_md(r.text)
    user_review = None
    can_write = False
    if current_user.is_authenticated:
        user_review = db.session.execute(
            db.select(Review).filter_by(book_id=book.id, user_id=current_user.id)).scalar()
        if user_review:
            user_review.text_html = render_md(user_review.text)
        else:
            can_write = True
    return render_template('books/show.html',
                           book=book,
                           full_desc_html=full_desc_html,
                           reviews=approved,
                           user_review=user_review,
                           can_write=can_write)


@bp.route('/new')
@roles_required('администратор')
def new():
    book = Book()
    genres = db.session.execute(db.select(Genre)).scalars().all()
    return render_template('books/new.html', book=book, genres=genres,
                           selected_genres=[])


@bp.route('/create', methods=['POST'])
@roles_required('администратор')
def create():
    genres = db.session.execute(db.select(Genre)).scalars().all()
    genre_ids = [int(g) for g in request.form.getlist('genre_ids')]
    f = request.files.get('cover')
    book = Book(**book_params())
    book.short_desc = bleach.clean(request.form.get('short_desc') or '', tags=ALLOWED_TAGS, strip=True)
    book.genres = [g for g in genres if g.id in genre_ids]
    try:
        db.session.add(book)
        db.session.flush()
        if f and f.filename:
            CoverSaver(f, book.id).save()
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
        return render_template('books/new.html', book=book, genres=genres,
                               selected_genres=genre_ids)
    flash(f'Книга {book.name} была успешно добавлена!', 'success')
    return redirect(url_for('books.show', book_id=book.id))


@bp.route('/<int:book_id>/edit')
@roles_required('администратор', 'модератор')
def edit(book_id):
    book = db.get_or_404(Book, book_id)
    genres = db.session.execute(db.select(Genre)).scalars().all()
    selected_genres = [g.id for g in book.genres]
    return render_template('books/edit.html', book=book, genres=genres,
                           selected_genres=selected_genres)


@bp.route('/<int:book_id>/update', methods=['POST'])
@roles_required('администратор', 'модератор')
def update(book_id):
    book = db.get_or_404(Book, book_id)
    genres = db.session.execute(db.select(Genre)).scalars().all()
    genre_ids = [int(g) for g in request.form.getlist('genre_ids')]
    try:
        for p in BOOK_PARAMS:
            setattr(book, p, request.form.get(p) or None)
        book.short_desc = bleach.clean(request.form.get('short_desc') or '', tags=ALLOWED_TAGS, strip=True)
        book.genres = [g for g in genres if g.id in genre_ids]
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
        return render_template('books/edit.html', book=book, genres=genres,
                               selected_genres=genre_ids)
    flash(f'Книга {book.name} была успешно обновлена!', 'success')
    return redirect(url_for('books.show', book_id=book.id))


@bp.route('/<int:book_id>/delete', methods=['POST'])
@roles_required('администратор')
def delete(book_id):
    book = db.get_or_404(Book, book_id)
    name = book.name
    try:
        cover = book.cover
        cover_path = None
        if cover:
            cover_path = os.path.join(current_app.config['UPLOAD_FOLDER'], cover.storage_filename)
        db.session.delete(book)
        db.session.commit()
        if cover_path and os.path.exists(cover_path):
            os.remove(cover_path)
    except SQLAlchemyError:
        db.session.rollback()
        flash('При удалении книги возникла ошибка.', 'danger')
        return redirect(url_for('index'))
    flash(f'Книга {name} была успешно удалена!', 'success')
    return redirect(url_for('index'))


@bp.route('/<int:book_id>/reviews/new')
@login_required
def new_review(book_id):
    book = db.get_or_404(Book, book_id)
    existing = db.session.execute(
        db.select(Review).filter_by(book_id=book.id, user_id=current_user.id)).scalar()
    if existing:
        flash('Вы уже оставляли рецензию на эту книгу.', 'warning')
        return redirect(url_for('books.show', book_id=book.id))
    return render_template('reviews/new.html', book=book)


@bp.route('/<int:book_id>/reviews/create', methods=['POST'])
@login_required
def create_review(book_id):
    book = db.get_or_404(Book, book_id)
    existing = db.session.execute(
        db.select(Review).filter_by(book_id=book.id, user_id=current_user.id)).scalar()
    if existing:
        flash('Вы уже оставляли рецензию на эту книгу.', 'warning')
        return redirect(url_for('books.show', book_id=book.id))
    rating = request.form.get('rating')
    text = request.form.get('text')
    pending = db.session.execute(
        db.select(ReviewStatus).filter_by(name='на рассмотрении')).scalar()
    try:
        review = Review(
            book_id=book.id,
            user_id=current_user.id,
            rating=int(rating),
            text=bleach.clean(text or '', tags=ALLOWED_TAGS, strip=True),
            status_id=pending.id)
        db.session.add(review)
        db.session.commit()
    except (SQLAlchemyError, ValueError, TypeError):
        db.session.rollback()
        flash('При сохранении данных возникла ошибка.', 'danger')
        return render_template('reviews/new.html', book=book)
    flash('Ваша рецензия отправлена на модерацию.', 'success')
    return redirect(url_for('books.show', book_id=book.id))
