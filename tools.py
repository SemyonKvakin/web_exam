import hashlib
import uuid
import os
from functools import wraps
from werkzeug.utils import secure_filename
from flask import current_app, flash, redirect, url_for
from flask_login import current_user
from models import db, Cover


class CoverSaver:
    def __init__(self, file, book_id):
        self.file = file
        self.book_id = book_id

    def save(self):
        self.md5_hash = hashlib.md5(self.file.read()).hexdigest()
        self.file.seek(0)
        existing = db.session.execute(
            db.select(Cover).filter(Cover.md5_hash == self.md5_hash)).scalar()
        if existing is not None:
            return existing
        file_name = secure_filename(self.file.filename)
        cover = Cover(
            id=str(uuid.uuid4()),
            file_name=file_name,
            mime_type=self.file.mimetype,
            md5_hash=self.md5_hash,
            book_id=self.book_id)
        db.session.add(cover)
        db.session.flush()
        self.file.save(
            os.path.join(current_app.config['UPLOAD_FOLDER'], cover.storage_filename))
        return cover


def roles_required(*role_names):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Для выполнения данного действия необходимо пройти процедуру аутентификации.', 'warning')
                return redirect(url_for('auth.login'))
            if current_user.role.name not in role_names:
                flash('У вас недостаточно прав для выполнения данного действия.', 'warning')
                return redirect(url_for('index'))
            return func(*args, **kwargs)
        return wrapper
    return decorator
