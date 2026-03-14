from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'THE_BOYS_SECRET_KEY'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///projects.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    is_premium = db.Column(db.Boolean, default=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    tutorial_link = db.Column(db.String(200))
    votes = db.Column(db.Integer, default=0)
    submitter_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    image_path = db.Column(db.String(200))
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def index():
    projects = Project.query.order_by(Project.votes.desc()).all()
    return render_template('index.html', projects=projects)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registered successfully! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            flash('Logged in successfully!')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out!')
    return redirect(url_for('index'))

@app.route('/submit', methods=['GET','POST'])
def submit():
    if 'user_id' not in session:
        flash('Login to submit a project')
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        tutorial = request.form['tutorial']
        image_file = request.files['project_image']
        if image_file:
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
        else:
            filepath = None
        project = Project(
            title=title,
            description=description,
            tutorial_link=tutorial,
            submitter_id=session['user_id'],
            image_path=filepath
        )
        db.session.add(project)
        db.session.commit()
        flash('Project submitted!')
        return redirect(url_for('index'))
    return render_template('submit.html')

@app.route('/vote/<int:id>')
def vote(id):
    if 'user_id' not in session:
        flash('Login to vote!')
        return redirect(url_for('login'))
    project = Project.query.get_or_404(id)
    project.votes += 1
    db.session.commit()
    flash('Vote counted!')
    return redirect(url_for('index'))

@app.route('/premium')
def premium():
    return render_template('premium.html')

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    db.create_all()
    app.run(debug=True)