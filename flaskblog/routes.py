import os
import secrets
import googlemaps
from geopy.geocoders import Nominatim
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from flaskblog import app, db, bcrypt, mail, API_KEY
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, RequestResetForm, ResetPasswordForm
from flaskblog.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from geopy.distance import geodesic

# API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
# Initialize the Google Maps client with your API key
gmaps = googlemaps.Client(key=API_KEY)

@app.route("/")
@app.route("/home")
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=7)
    
    lat = 52.4853394
    lon = 13.425923
    user_location = (lat, lon)
    
    # Calculate distance for each post
    for post in posts.items:
        post.distance = round(geodesic(user_location, (post.lat, post.lon)).km, 2)
    
    return render_template('home.html', posts=posts)






@app.route('/about')
def about():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=7)
    post_data = [{'lat': post.lat, 'lon': post.lon, 'title': post.title, 'id': post.id, 'image': post.image_file} for post in posts.items]
    
    lat = 52.4853394 
    lon = 13.425923
    user_location = (lat, lon)  # User's location
    
    distance_data = []
    
    for post in post_data:
        post_location = (post['lat'], post['lon'])
        distance = geodesic(user_location, post_location).km  # Calculate distance using geopy
        post['distance'] = round(distance, 2)
        distance_data.append(post)

    api_key = API_KEY
    print(f'Latitude: {lat}, Longitude: {lon}')
    return render_template('about.html', lat=lat, lon=lon, posts=distance_data, postData=post_data)







@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


def save_picture(form_picture, folder='profile_pics'):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static', folder, picture_fn)

    output_size = (500, 500)  # Adjust if desired
    img = Image.open(form_picture)
    img.thumbnail(output_size)
    img.save(picture_path)

    return picture_fn


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        # Get the address from the form
        address = form.address.data

        # Geocode the address using Google Maps API
        geocode_result = gmaps.geocode(address)

        if geocode_result:
            lat = geocode_result[0]['geometry']['location']['lat']
            lon = geocode_result[0]['geometry']['location']['lng']
            short_name = geocode_result[0]['address_components'][2]['short_name']

        else:
            lat = lon = None  # Handle case if geocoding fails
      
        # Handle the uploaded picture
        picture_file = None
        if form.picture.data:
            picture_file = save_picture(form.picture.data, folder='post_pics')

        # Fallback to the image_choice if no file is uploaded
        if not picture_file:
            if form.image_choice.data == 'image1':
                picture_file = 'path_to_image1.png'
            elif form.image_choice.data == 'image2':
                picture_file = 'path_to_image2.png'
            elif form.image_choice.data == 'image3':
                picture_file = 'path_to_image3.png'
            else:
                picture_file = None  # Default or no image

        post = Post(
            title=form.title.data,
            content=form.content.data,
            image_file=picture_file,  # Updated to use picture_file
            image_choice=form.image_choice.data,  # Stores the choice (image1, image2, or image3)
            author=current_user,
            address=form.address.data,
            lat=lat,
            lon=lon,
            short_name=short_name
        )

        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    
    return render_template('create_post.html', title='New Post', form=form)




@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Reference location (e.g., user's location)
    user_location = (52.4853394, 13.425923)  # Example coordinates
    
    # Post location
    post_location = (post.lat, post.lon)
    
    # Calculate distance
    distance = geodesic(user_location, post_location).km  # in kilometers
    post_distance = round(distance, 2)  # rounded to 2 decimal places
    
    return render_template('post.html', title=post.title, post=post, post_distance=post_distance)



@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        address = form.address.data

        # Geocode the address using Google Maps API
        geocode_result = gmaps.geocode(address)

        if geocode_result:
            lat = geocode_result[0]['geometry']['location']['lat']
            lon = geocode_result[0]['geometry']['location']['lng']
            short_name = geocode_result[0]['address_components'][2]['short_name']

        else:
            lat = lon = None  # Handle case if geocoding fails
            short_name = None
        post.title = form.title.data
        post.content = form.content.data
        post.lon = lon
        post.lat = lat
        post.address = address
        post.short_name = short_name
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request', sender='noreply@demo.com', recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)

@app.route("/reset_password", methods=['GET', 'POST']) #route where user requests to reset the pw
def reset_request():
     if current_user.is_authenticated: 
        return redirect(url_for('home')) #makes sure user is logged out before they reset their pw
     form = RequestResetForm()
     if form.validate_on_submit():
         user = User.query.filter_by(email=form.email.data).first()
         send_reset_email(user)
         flash('An email has been sent with instructions to reset your password.', 'info') #info is a bs class
         return redirect(url_for('login'))
     return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST']) #route where user actually resets the pw
def reset_token(token):
    if current_user.is_authenticated: 
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token.', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)

@app.route("/post/quality/<int:quality_id>", methods=['GET'])
def quality(quality_id):
    search_quality = f'image{quality_id}'
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter(Post.image_choice==search_quality).order_by(Post.date_posted.desc()).paginate(page=page, per_page=7)
   
    lat = 52.4853394
    lon = 13.425923
    user_location = (lat, lon)
    
    # Calculate distance for each post
    for post in posts.items:
        post.distance = round(geodesic(user_location, (post.lat, post.lon)).km, 2)
    return render_template('home.html', posts=posts)

