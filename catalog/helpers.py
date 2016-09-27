from database_setup import Base, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

myEngine = create_engine('sqlite:///restaurant.db')
Base.metadata.bind = myEngine

databaseSession = sessionmaker(bind=myEngine)
mySession = databaseSession()


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    mySession.add(newUser)
    mySession.commit()
    user = mySession.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = mySession.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = mySession.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None