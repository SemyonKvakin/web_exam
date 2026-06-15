import os
from typing import Optional, List
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from flask import url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Text, Integer, MetaData, Table, Column, func


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": 'ix_%(column_0_label)s',
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    })


db = SQLAlchemy(model_class=Base)


book_genres = Table(
    'book_genres',
    Base.metadata,
    Column('book_id', ForeignKey('books.id', ondelete='CASCADE'), primary_key=True),
    Column('genre_id', ForeignKey('genres.id', ondelete='CASCADE'), primary_key=True),
)


class Role(Base):
    __tablename__ = 'roles'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)

    def __repr__(self):
        return '<Role %r>' % self.name


class User(Base, UserMixin):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    last_name: Mapped[str] = mapped_column(String(100))
    first_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[Optional[str]] = mapped_column(String(100))
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id'))

    role: Mapped['Role'] = relationship(lazy=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return ' '.join([self.last_name, self.first_name, self.middle_name or ''])

    @property
    def is_admin(self):
        return self.role and self.role.name == 'администратор'

    @property
    def is_moderator(self):
        return self.role and self.role.name == 'модератор'

    @property
    def is_user(self):
        return self.role and self.role.name == 'пользователь'

    def __repr__(self):
        return '<User %r>' % self.login


class Genre(Base):
    __tablename__ = 'genres'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    def __repr__(self):
        return '<Genre %r>' % self.name


class Cover(Base):
    __tablename__ = 'covers'

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(100))
    mime_type: Mapped[str] = mapped_column(String(100))
    md5_hash: Mapped[str] = mapped_column(String(100), unique=True)
    book_id: Mapped[int] = mapped_column(ForeignKey('books.id', ondelete='CASCADE'))

    @property
    def storage_filename(self):
        _, ext = os.path.splitext(self.file_name)
        return self.id + ext

    @property
    def url(self):
        return url_for('cover', cover_id=self.id)

    def __repr__(self):
        return '<Cover %r>' % self.file_name


class Book(Base):
    __tablename__ = 'books'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    short_desc: Mapped[str] = mapped_column(Text)
    year: Mapped[int] = mapped_column(Integer)
    publisher: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(200))
    pages: Mapped[int] = mapped_column(Integer)

    genres: Mapped[List['Genre']] = relationship(secondary=book_genres, lazy=False)
    cover: Mapped[Optional['Cover']] = relationship(
        backref='book', cascade='all, delete-orphan', single_parent=True)
    reviews: Mapped[List['Review']] = relationship(
        back_populates='book', cascade='all, delete-orphan')

    @property
    def rating(self):
        approved = [r for r in self.reviews if r.status and r.status.name == 'одобрена']
        if approved:
            return sum(r.rating for r in approved) / len(approved)
        return 0

    @property
    def reviews_count(self):
        return len([r for r in self.reviews if r.status and r.status.name == 'одобрена'])

    def __repr__(self):
        return '<Book %r>' % self.name


class ReviewStatus(Base):
    __tablename__ = 'review_statuses'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    def __repr__(self):
        return '<ReviewStatus %r>' % self.name


class Review(Base):
    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey('books.id', ondelete='CASCADE'))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    status_id: Mapped[int] = mapped_column(ForeignKey('review_statuses.id'))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    book: Mapped['Book'] = relationship(back_populates='reviews')
    user: Mapped['User'] = relationship()
    status: Mapped['ReviewStatus'] = relationship(lazy=False)

    RATING_LABELS = {
        5: 'отлично',
        4: 'хорошо',
        3: 'удовлетворительно',
        2: 'неудовлетворительно',
        1: 'плохо',
        0: 'ужасно',
    }

    @property
    def rating_label(self):
        return self.RATING_LABELS.get(self.rating, '')

    def __repr__(self):
        return '<Review %r>' % self.id
