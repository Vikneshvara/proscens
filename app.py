from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.template_folder = '.'
app.secret_key = 'THE_BOYS_SECRET_KEY'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///projects.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    is_premium = db.Column(db.Boolean, default=False)
    bio = db.Column(db.Text, default='')
    avatar = db.Column(db.String(200), default='default.png')
    level = db.Column(db.Integer, default=1)
    xp = db.Column(db.Integer, default=0)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    tutorial_link = db.Column(db.String(200))
    category = db.Column(db.String(50), default='General')
    tags = db.Column(db.String(200), default='')
    votes = db.Column(db.Integer, default=0)
    submitter_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    image_path = db.Column(db.String(200))
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

class Friend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending')  # pending, accepted, blocked

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def index():
    projects = Project.query.order_by(Project.votes.desc()).all()
    user_info = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user_info = {
            'username': user.username,
            'level': user.level,
            'xp': user.xp
        }
    # Add submitter info to projects
    for project in projects:
        project.submitter = User.query.get(project.submitter_id)
    return render_template('index.html', projects=projects, user_info=user_info)

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

@app.route('/skills')
def skills():
    return render_template('skills.html')

@app.route('/visualizer')
def visualizer():
    return render_template('visualizer.html')

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

@app.route('/leaderboard')
def leaderboard():
    projects = Project.query.order_by(Project.votes.desc()).limit(10).all()
    return render_template('leaderboard.html', projects=projects)

@app.route('/friends')
def friends():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_friends = Friend.query.filter(
        ((Friend.user_id == session['user_id']) | (Friend.friend_id == session['user_id'])) &
        (Friend.status == 'accepted')
    ).all()
    friend_ids = []
    for f in user_friends:
        if f.user_id == session['user_id']:
            friend_ids.append(f.friend_id)
        else:
            friend_ids.append(f.user_id)
    friends_list = User.query.filter(User.id.in_(friend_ids)).all()
    return render_template('friends.html', friends=friends_list)

@app.route('/add_friend/<int:user_id>')
def add_friend(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if user_id == session['user_id']:
        flash('Cannot add yourself as friend!')
        return redirect(url_for('index'))
    existing = Friend.query.filter(
        ((Friend.user_id == session['user_id']) & (Friend.friend_id == user_id)) |
        ((Friend.user_id == user_id) & (Friend.friend_id == session['user_id']))
    ).first()
    if existing:
        flash('Friend request already exists!')
    else:
        friend = Friend(user_id=session['user_id'], friend_id=user_id)
        db.session.add(friend)
        db.session.commit()
        flash('Friend request sent!')
    return redirect(url_for('index'))

@app.route('/accept_friend/<int:friend_id>')
def accept_friend(friend_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    friend_req = Friend.query.filter_by(user_id=friend_id, friend_id=session['user_id'], status='pending').first()
    if friend_req:
        friend_req.status = 'accepted'
        db.session.commit()
        flash('Friend request accepted!')
    return redirect(url_for('friends'))

@app.route('/chat/<int:user_id>')
def chat(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    friend = User.query.get_or_404(user_id)
    messages = Message.query.filter(
        ((Message.sender_id == session['user_id']) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == session['user_id']))
    ).order_by(Message.timestamp).all()
    return render_template('chat.html', friend=friend, messages=messages)

@app.route('/send_message/<int:user_id>', methods=['POST'])
def send_message(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    content = request.form['message']
    if content.strip():
        message = Message(sender_id=session['user_id'], receiver_id=user_id, content=content)
        db.session.add(message)
        db.session.commit()
    return redirect(url_for('chat', user_id=user_id))

@app.route('/submit_enhanced', methods=['GET','POST'])
def submit_enhanced():
    if 'user_id' not in session:
        flash('Login to submit a project')
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        tutorial = request.form['tutorial']
        category = request.form['category']
        tags = request.form['tags']
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
            category=category,
            tags=tags,
            submitter_id=session['user_id'],
            image_path=filepath
        )
        db.session.add(project)
        db.session.commit()
        # Award XP
        user = User.query.get(session['user_id'])
        user.xp += 50
        db.session.commit()
        flash('Project submitted! +50 XP earned!')
        return redirect(url_for('index'))
    return render_template('submit_enhanced.html')

@app.route('/achievements')
def achievements():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_achievements = Achievement.query.filter_by(user_id=session['user_id']).all()
    return render_template('achievements.html', achievements=user_achievements)

@app.route('/profile/<int:user_id>')
def profile(user_id):
    user = User.query.get_or_404(user_id)
    projects = Project.query.filter_by(submitter_id=user_id).order_by(Project.votes.desc()).all()
    achievements = Achievement.query.filter_by(user_id=user_id).all()
    return render_template('profile.html', user=user, projects=projects, achievements=achievements)

@app.route('/global_chat')
def global_chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    messages = Message.query.filter_by(receiver_id=None).order_by(Message.timestamp.desc()).limit(50).all()
    return render_template('global_chat.html', messages=messages)

@app.route('/send_global_message', methods=['POST'])
def send_global_message():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    content = request.form['message']
    if content.strip():
        message = Message(sender_id=session['user_id'], receiver_id=None, content=content)
        db.session.add(message)
        db.session.commit()
    return redirect(url_for('global_chat'))

@app.route('/math_solver')
def math_solver():
    return render_template('math_solver.html')

@app.route('/solve_math', methods=['POST'])
def solve_math():
    expression = request.form.get('expression', '')
    operation = request.form.get('operation', 'evaluate')
    try:
        from sympy import symbols, sympify, solve, diff, integrate, simplify, Eq, limit, series, Matrix
        x, y, z = symbols('x y z')
        if operation == 'solve':
            eq = sympify(expression)
            result = solve(eq)
        elif operation == 'diff':
            expr = sympify(expression)
            result = diff(expr, x)
        elif operation == 'integrate':
            expr = sympify(expression)
            result = integrate(expr, x)
        elif operation == 'simplify':
            expr = sympify(expression)
            result = simplify(expr)
        elif operation == 'limit':
            # Assume limit as x approaches a value, e.g., limit(x**2, x, 0)
            parts = expression.split(',')
            if len(parts) == 3:
                expr = sympify(parts[0])
                var = sympify(parts[1])
                point = sympify(parts[2])
                result = limit(expr, var, point)
            else:
                result = "Format: expression,variable,point"
        elif operation == 'series':
            expr = sympify(expression)
            result = series(expr, x, 0, 6)
        elif operation == 'matrix':
            # Simple matrix operations, e.g., [[1,2],[3,4]] * [[5,6],[7,8]]
            result = "Matrix operations coming soon"
        else:
            result = sympify(expression)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/plot_function', methods=['POST'])
def plot_function():
    expression = request.form.get('expression', '')
    try:
        from sympy import symbols, sympify, lambdify
        import matplotlib.pyplot as plt
        import numpy as np
        import io
        import base64

        x = symbols('x')
        expr = sympify(expression)
        f = lambdify(x, expr, 'numpy')

        x_vals = np.linspace(-10, 10, 400)
        y_vals = f(x_vals)

        plt.figure(figsize=(8, 6))
        plt.plot(x_vals, y_vals, color='#ff6b6b', linewidth=2)
        plt.title(f'Plot of {expression}', fontsize=16, color='white')
        plt.xlabel('x', color='white')
        plt.ylabel('y', color='white')
        plt.grid(True, alpha=0.3)
        plt.axhline(0, color='white', linewidth=0.5)
        plt.axvline(0, color='white', linewidth=0.5)
        plt.gca().set_facecolor('#000011')
        plt.gca().tick_params(colors='white')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor='#000011')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()

        return f'<img src="data:image/png;base64,{image_base64}" alt="Function Plot" style="max-width:100%; border-radius:10px; box-shadow: 0 0 20px #ff6b6b;">'
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True)