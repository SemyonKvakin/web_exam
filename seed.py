from app import app
from models import db, Role, User, Genre, ReviewStatus


def seed():
    with app.app_context():
        db.create_all()

        if not db.session.execute(db.select(Role)).scalars().first():
            roles = [
                Role(name='администратор', description='Суперпользователь, полный доступ к системе'),
                Role(name='модератор', description='Может редактировать данные книг и модерировать рецензии'),
                Role(name='пользователь', description='Может оставлять рецензии'),
            ]
            db.session.add_all(roles)
            db.session.flush()

            statuses = [
                ReviewStatus(name='на рассмотрении'),
                ReviewStatus(name='одобрена'),
                ReviewStatus(name='отклонена'),
            ]
            db.session.add_all(statuses)

            genres = [Genre(name=n) for n in
                      ['Роман', 'Фантастика', 'Детектив', 'Поэзия', 'Научная литература']]
            db.session.add_all(genres)

            admin = User(login='admin', last_name='Квакин', first_name='Семён',
                         middle_name='Дмитриевич', role=roles[0])
            admin.set_password('admin')
            moder = User(login='moder', last_name='Иванов', first_name='Иван',
                         middle_name='Иванович', role=roles[1])
            moder.set_password('moder')
            user = User(login='user', last_name='Петров', first_name='Пётр',
                        middle_name='Петрович', role=roles[2])
            user.set_password('user')
            db.session.add_all([admin, moder, user])

            db.session.commit()
            print('База данных наполнена.')
        else:
            print('Данные уже существуют.')


if __name__ == '__main__':
    seed()
