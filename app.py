from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.extras import DictCursor
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database connection
def get_db_connection():
    database_url = os.getenv('DATABASE_URL')  # Get the database URL
    if not database_url:  
        raise ValueError("DATABASE_URL is not set in environment variables")  
    return psycopg2.connect(database_url)
    
# Routes
@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT team_name, current_round FROM teams ORDER BY current_round DESC, round4_completion_time, round3_completion_time, round2_completion_time, round1_completion_time LIMIT 10')
    leaderboard = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('index.html', leaderboard=leaderboard)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        team_id = request.form['team_id']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        cur.execute('SELECT * FROM teams WHERE team_id = %s AND team_password = %s', (team_id, password))
        team = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if team:
            session['team_id'] = team_id
            session['current_round'] = team['current_round']
            return redirect(url_for('team_dashboard'))
        
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # For demonstration, using hardcoded admin credentials
        # In production, use proper authentication
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            return redirect(url_for('admin'))
        flash('Invalid admin credentials')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/team/logout')
def team_logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/team/dashboard')
def team_dashboard():
    if 'team_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    # Get team info
    cur.execute('SELECT * FROM teams WHERE team_id = %s', (session['team_id'],))
    team = dict(cur.fetchone())  # Convert to regular dictionary
    team['position'] = None  # Initialize position as None
    
    # If team has completed all rounds, check their position
    if team['current_round'] > 4:
        # Get position based on completion times
        cur.execute('''
            WITH ranked_teams AS (
                SELECT 
                    team_id,
                    ROW_NUMBER() OVER (
                        ORDER BY 
                            current_round DESC,
                            round4_completion_time,
                            round3_completion_time,
                            round2_completion_time,
                            round1_completion_time
                    ) as position
                FROM teams
                WHERE current_round > 4
            )
            SELECT position FROM ranked_teams WHERE team_id = %s
        ''', (session['team_id'],))
        position = cur.fetchone()
        if position:
            team['position'] = position[0]
    
    cur.close()
    conn.close()
    
    return render_template('team_dashboard.html', team=team)

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    if 'team_id' not in session:
        return redirect(url_for('login'))
    
    answer = request.form['answer']
    round_num = int(request.form['round'])
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM teams WHERE team_id = %s', (session['team_id'],))
    team = cur.fetchone()
    
    correct_answer = team[f'r{round_num}']
    
    if answer == correct_answer:
        # Update round completion
        cur.execute('''
            UPDATE teams 
            SET current_round = %s, 
                round{}_completion_time = %s 
            WHERE team_id = %s
        '''.format(round_num), (round_num + 1, datetime.now(), session['team_id']))
        conn.commit()
        
        if round_num == 4:
            flash('🎉 Congratulations! You have completed all rounds! 🎉')
        else:
            flash(f'🎉 Congratulations! You have completed Round {round_num}! Moving to Round {round_num + 1}.')
    else:
        flash('Incorrect answer. Try again.')
    
    cur.close()
    conn.close()
    
    return redirect(url_for('team_dashboard'))

@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM teams ORDER BY current_round DESC, round4_completion_time, round3_completion_time, round2_completion_time, round1_completion_time')
    teams = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('admin.html', teams=teams)

@app.route('/admin/toggle_team', methods=['POST'])
def toggle_team_status():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    team_id = request.form['team_id']
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('UPDATE teams SET is_active = NOT is_active WHERE team_id = %s', (team_id,))
    conn.commit()
    
    cur.close()
    conn.close()
    
    return redirect(url_for('admin'))

@app.route('/admin/upload', methods=['POST'])
def upload_teams():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    if 'file' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('admin'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('admin'))
    
    try:
        df = pd.read_excel(file)
        conn = get_db_connection()
        cur = conn.cursor()
        
        for _, row in df.iterrows():
            cur.execute('''
                INSERT INTO teams (team_name, team_id, team_password, member1, member2, member3, member4, r1, r2, r3, r4)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                row['team_name'], row['team_id'], row['team_password'],
                row['member1'], row['member2'], row['member3'], row['member4'],
                row['r1'], row['r2'], row['r3'], row['r4']
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        flash('Teams uploaded successfully')
    except Exception as e:
        flash(f'Error uploading teams: {str(e)}')
    
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)