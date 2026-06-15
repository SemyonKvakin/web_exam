import bleach
import markdown
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from models import db, Review, ReviewStatus
from tools import roles_required

bp = Blueprint('reviews', __name__, url_prefix='/reviews')

ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'b', 'i', 'u', 'ol', 'ul', 'li',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code',
                'pre', 'a', 'hr']


def render_md(text):
    return markdown.markdown(bleach.clean(text or '', tags=ALLOWED_TAGS, strip=True))


@bp.route('/my')
@roles_required('пользователь')
def my():
    reviews = db.session.execute(
        db.select(Review).filter_by(user_id=current_user.id)
        .order_by(Review.created_at.desc())).scalars().all()
    for r in reviews:
        r.text_html = render_md(r.text)
    return render_template('reviews/my.html', reviews=reviews)


@bp.route('/moderation')
@roles_required('модератор')
def moderation():
    page = request.args.get('page', 1, type=int)
    pending = db.session.execute(
        db.select(ReviewStatus).filter_by(name='на рассмотрении')).scalar()
    query = (db.select(Review).filter_by(status_id=pending.id)
             .order_by(Review.created_at.desc()))
    pagination = db.paginate(query, page=page)
    return render_template('moderation/index.html',
                           reviews=pagination.items,
                           pagination=pagination)


@bp.route('/<int:review_id>/moderate')
@roles_required('модератор')
def moderate(review_id):
    review = db.get_or_404(Review, review_id)
    review.text_html = render_md(review.text)
    return render_template('moderation/show.html', review=review)


@bp.route('/<int:review_id>/approve', methods=['POST'])
@roles_required('модератор')
def approve(review_id):
    return _change_status(review_id, 'одобрена', 'Рецензия одобрена.')


@bp.route('/<int:review_id>/reject', methods=['POST'])
@roles_required('модератор')
def reject(review_id):
    return _change_status(review_id, 'отклонена', 'Рецензия отклонена.')


def _change_status(review_id, status_name, message):
    review = db.get_or_404(Review, review_id)
    status = db.session.execute(
        db.select(ReviewStatus).filter_by(name=status_name)).scalar()
    try:
        review.status_id = status.id
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash('При изменении статуса возникла ошибка.', 'danger')
        return redirect(url_for('reviews.moderation'))
    flash(message, 'success')
    return redirect(url_for('reviews.moderation'))
