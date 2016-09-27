from flask import Flask, render_template, request, url_for, redirect, make_response
from flask import session as login_session, flash, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem, User
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from helpers import getUserID, createUser, getUserInfo
import httplib2
import json
import requests
import helpers
import random
import string


app = Flask(__name__)


engine = create_engine('sqlite:///restaurant.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('index.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != '138944603325-7mba070k8hkk28qs3a4lsj499iq2cdqh.apps.googleusercontent.com':
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 15em; height: 15em;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token', None)
    if access_token is None:
        print 'Access Token is None'
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session[
        'access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return redirect(url_for('showLogin'))
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/restaurants')
def restaurants():
    restaurants = session.query(Restaurant).all()
    creators = session.query(User).all()
    current_user = login_session.get('user_id', None)
    return render_template('restaurants.html', restaurants=restaurants, creators=creators, current_user=current_user)


@app.route('/restaurant/<int:restaurant_id>/menu')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    creator = session.query(User).filter_by(id=restaurant.user_id).one()
    current_user = login_session.get('user_id', None)
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    return render_template('menu.html', restaurant=restaurant, items=items, creator = creator, current_user=current_user)


@app.route('/newrestaurant', methods=['GET', 'POST'])
def newRestaurant():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'GET':
        return render_template('newRestaurant.html')
    else:
        newRestaurant = Restaurant(
            name=request.form['name'], user_id=login_session['user_id'])
        session.add(newRestaurant)
        session.commit()
        return redirect(url_for('restaurants'))


@app.route('/restaurant/<int:restaurant_id>/newmenuitem', methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'GET':
        return render_template('newMenuItem.html')
    else:
        newItem = MenuItem(name=request.form['name'], description=request.form['description'], price=request.form[
                           'price'], course=request.form['course'], restaurant_id=restaurant_id, user_id=restaurant.user_id)
        session.add(newItem)
        session.commit()
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant.id))


@app.route('/restaurant/<int:restaurant_id>/edit', methods=['GET', 'POST'])
def editRestaurant(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    current_user = login_session.get('user_id', None)
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'GET':
        return render_template('editRestaurant.html', restaurant=restaurant, current_user = current_user)
    else:
        if login_session['user_id'] != restaurant.user_id:
            return redirect(url_for('restaurants'))
        if request.form['name']:
            restaurant.name = request.form['name']
            session.add(restaurant)
            session.commit()
    return redirect(url_for('restaurants'))


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_item_id>/edit', methods=['GET', 'POST'])
def editMenuItem(restaurant_id, menu_item_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    menuItem = session.query(MenuItem).filter_by(id=menu_item_id).one()
    current_user = login_session.get('user_id', None)
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'GET':
        return render_template('editMenuItem.html', restaurant=restaurant, menuItem=menuItem, current_user = current_user)
    else:
        if login_session['user_id'] != menuItem.user_id:
            return redirect(url_for('restaurants'))
        if request.form['name']:
            menuItem.name = request.form['name']
        if request.form['description']:
            menuItem.description = request.form['description']
        if request.form['course']:
            menuItem.course = request.form['course']
        if request.form['price']:
            menuItem.price = request.form['price']
        session.add(menuItem)
        session.commit()
    return redirect(url_for('restaurantMenu', restaurant_id=restaurant.id))


@app.route('/restaurant/<int:restaurant_id>/delete', methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    current_user = login_session.get('user_id', None)
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'GET':
        restaurant = session.query(
            Restaurant).filter_by(id=restaurant_id).one()
        return render_template('deleteRestaurant.html', restaurant=restaurant, current_user = current_user)
    else:
        if login_session['user_id'] != restaurant.user_id:
            return redirect(url_for('restaurants'))
        for item in items:
            session.delete(item)
        session.delete(restaurant)
        session.commit()
        return redirect(url_for('restaurants'))


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_item_id>/delete', methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_item_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    menuItem = session.query(MenuItem).filter_by(id=menu_item_id).one()
    current_user = login_session.get('user_id', None) 
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'GET':
        return render_template('deleteMenuItem.html', restaurant=restaurant, menuItem=menuItem, current_user = current_user)
    else:
        if login_session['user_id'] != menuItem.user_id:
            return redirect(url_for('restaurants'))
        session.delete(menuItem)
        session.commit()
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant.id))

@app.route('/restaurants/JSON')
def restaurantsJSON():
    restaurants = session.query(Restaurant).all()
    return jsonify(restaurants=[restaurant.serialize for restaurant in restaurants])

@app.route('/restaurant/<int:restaurant_id>/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    return jsonify(restaurant_menu=[item.serialize for item in items])


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(restaurant_id, menu_id):
    menuItem = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(menu_item=menuItem.serialize)


if __name__ == '__main__':
    app.secret_key = "KLj03ROjDCNOM0OBQ3-_ON4Q"
    app.debug = True
    app.run(host='0.0.0.0', port=5000)