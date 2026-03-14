from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import sympy
from sympy import sympify

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

@app.route('/visualizer')
def visualizer():
    return render_template('visualizer.html')

@app.route('/math_solver')
def math_solver():
    return render_template('math_solver.html')

@app.route('/solve_math', methods=['POST'])
def solve_math():
    from sympy import sympify, simplify, solve, diff, integrate, limit, series, evalf
    expression = request.form['expression']
    operation = request.form.get('operation', 'simplify')
    
    try:
        expr = sympify(expression)
        if operation == 'simplify':
            result = simplify(expr)
        elif operation == 'solve':
            result = solve(expr)
        elif operation == 'differentiate':
            result = diff(expr)
        elif operation == 'integrate':
            result = integrate(expr)
        elif operation == 'limit':
            result = limit(expr, sympify('x'), 0)
        elif operation == 'series':
            result = series(expr, n=6)
        else:
            result = expr.evalf()
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/plot_function', methods=['POST'])
def plot_function():
    import matplotlib.pyplot as plt
    import io
    import base64
    
    expression = request.form['expression']
    x_min = float(request.form.get('x_min', -10))
    x_max = float(request.form.get('x_max', 10))
    
    try:
        from sympy import symbols, lambdify
        x = symbols('x')
        expr = sympify(expression)
        f = lambdify(x, expr, 'numpy')
        
        import numpy as np
        x_vals = np.linspace(x_min, x_max, 1000)
        y_vals = f(x_vals)
        
        plt.figure(figsize=(8, 6))
        plt.plot(x_vals, y_vals)
        plt.title(f'Plot of {expression}')
        plt.xlabel('x')
        plt.ylabel('y')
        plt.grid(True)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        return f'<img src="data:image/png;base64,{image_base64}" alt="Function Plot">'
    except Exception as e:
        return f"Error plotting: {str(e)}"

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    db.create_all()
    app.run(debug=True)