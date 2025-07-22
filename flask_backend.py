from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import PyPDF2
import spacy
import re
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3
from contextlib import contextmanager
import json
from collections import Counter
import math
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_from_directory

app = Flask(__name__)
CORS(app, supports_credentials=True)  # 🔥 Allow credentials (cookies)

app.secret_key = '70eb90eab88bd96393294b5ac3ad5b00'  # 🔐 Required for session

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['admin'] = True
            return jsonify({'success': True, 'message': 'Logged in successfully!'})
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        # Check if username already exists
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return jsonify({'error': 'Username already exists'}), 400

        hashed_pw = generate_password_hash(password)
        cursor.execute(
            'INSERT INTO users (username, password) VALUES (?, ?)',
            (username, hashed_pw)
        )
        conn.commit()

    return jsonify({'success': True, 'message': 'User created successfully'})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('admin', None)
    return jsonify({'success': True})

@app.route('/api/check-admin', methods=['GET'])
def check_admin():
    if session.get('admin'):
        return jsonify({'logged_in': True})
    else:
        return jsonify({'logged_in': False})

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'pdf'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load spaCy model (you'll need to install: python -m spacy download en_core_web_sm)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Please install spaCy English model: python -m spacy download en_core_web_sm")
    nlp = None

# Database setup
DATABASE = 'resume_analyzer.db'

def init_db():
    """Initialize the database with required tables"""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
        ''') 

        # Jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                description TEXT NOT NULL,
                skills TEXT NOT NULL,
                experience_level TEXT NOT NULL,
                salary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Resumes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                extracted_text TEXT,
                skills TEXT,
                experience_level TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert sample jobs if table is empty
        cursor.execute('SELECT COUNT(*) FROM jobs')
        if cursor.fetchone()[0] == 0:
            sample_jobs = [
                ('Frontend Developer', 'TechCorp Inc.', 'Looking for a skilled frontend developer with React experience. You will be responsible for building user interfaces and ensuring great user experience.', 
                 'JavaScript,React,CSS,HTML,TypeScript,Redux,Webpack', 'mid', '$70,000 - $90,000'),
                ('Full Stack Engineer', 'StartupXYZ', 'Join our team as a full stack engineer working with modern technologies. You will work on both frontend and backend systems.', 
                 'Node.js,Python,React,MongoDB,AWS,Express,Docker', 'senior', '$80,000 - $120,000'),
                ('Data Scientist', 'DataTech Solutions', 'Seeking a data scientist with machine learning expertise. You will analyze large datasets and build predictive models.', 
                 'Python,Machine Learning,TensorFlow,SQL,Statistics,Pandas,NumPy,Scikit-learn', 'mid', '$90,000 - $130,000'),
                ('UX Designer', 'DesignStudio', 'Creative UX designer needed for innovative product design. You will create user-centered designs and prototypes.', 
                 'Figma,Adobe XD,User Research,Prototyping,CSS,Sketch,InVision', 'entry', '$60,000 - $80,000'),
                ('Backend Developer', 'CloudTech', 'Backend developer with expertise in cloud technologies. You will build scalable APIs and microservices.', 
                 'Python,Django,PostgreSQL,AWS,Docker,Redis,Kubernetes', 'senior', '$85,000 - $110,000'),
                ('DevOps Engineer', 'InfraTech', 'DevOps engineer to manage CI/CD pipelines and cloud infrastructure. You will automate deployment processes.', 
                 'AWS,Docker,Kubernetes,Jenkins,Terraform,Linux,Git,Python', 'senior', '$95,000 - $125,000')
            ]
            
            cursor.executemany('''
                INSERT INTO jobs (title, company, description, skills, experience_level, salary)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', sample_jobs)                   
        conn.commit()

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def extract_skills_from_text(text):
    """Extract skills from resume text using NLP and keyword matching"""
    # Common technical skills database
    technical_skills = {
        'programming': ['Python', 'JavaScript', 'Java', 'C++', 'C#', 'Ruby', 'PHP', 'Go', 'Rust', 'Swift', 'Kotlin', 'TypeScript', 'R', 'Scala', 'Perl'],
        'web_frontend': ['React', 'Angular', 'Vue.js', 'HTML', 'CSS', 'SCSS', 'SASS', 'Bootstrap', 'Tailwind', 'jQuery', 'Webpack', 'Babel'],
        'web_backend': ['Node.js', 'Django', 'Flask', 'Express', 'Spring', 'Laravel', 'Ruby on Rails', 'ASP.NET', 'FastAPI'],
        'databases': ['MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'SQLite', 'Oracle', 'SQL Server', 'Cassandra', 'ElasticSearch'],
        'cloud': ['AWS', 'Azure', 'Google Cloud', 'Docker', 'Kubernetes', 'Jenkins', 'Terraform', 'Ansible'],
        'data_science': ['Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy', 'Matplotlib', 'Seaborn', 'Jupyter'],
        'design': ['Figma', 'Adobe XD', 'Photoshop', 'Illustrator', 'Sketch', 'InVision', 'Prototyping', 'User Research', 'UX Design', 'UI Design'],
        'tools': ['Git', 'GitHub', 'GitLab', 'Jira', 'Confluence', 'Slack', 'Trello', 'Postman', 'VSCode', 'IntelliJ']
    }
    
    all_skills = []
    for category in technical_skills.values():
        all_skills.extend(category)
    
    # Convert text to lowercase for matching
    text_lower = text.lower()
    
    # Find skills mentioned in the text
    found_skills = []
    for skill in all_skills:
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.append(skill)
    
    # Use spaCy for additional entity extraction if available
    if nlp:
        doc = nlp(text)
        # Extract organizations and technologies
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'PRODUCT'] and len(ent.text) > 2:
                # Check if it might be a technology
                if any(tech.lower() in ent.text.lower() for tech in all_skills):
                    found_skills.append(ent.text)
    
    # Remove duplicates and return
    return list(set(found_skills))

def determine_experience_level(text):
    """Determine experience level from resume text"""
    text_lower = text.lower()
    
    # Count experience indicators
    senior_indicators = ['senior', 'lead', 'principal', 'architect', 'manager', 'director', 'head of', 'chief']
    mid_indicators = ['developer', 'engineer', 'analyst', 'consultant', 'specialist']
    entry_indicators = ['junior', 'entry', 'intern', 'trainee', 'graduate', 'recent graduate']
    
    # Count years of experience mentioned
    years_pattern = r'(\d+)\s*\+?\s*years?\s*(of\s*)?(experience|exp)'
    years_matches = re.findall(years_pattern, text_lower)
    
    max_years = 0
    for match in years_matches:
        try:
            years = int(match[0])
            max_years = max(max_years, years)
        except ValueError:
            continue
    
    # Determine level based on years
    if max_years >= 5:
        return 'senior'
    elif max_years >= 2:
        return 'mid'
    elif max_years > 0:
        return 'entry'
    
    # Fallback to keyword matching
    senior_count = sum(1 for indicator in senior_indicators if indicator in text_lower)
    mid_count = sum(1 for indicator in mid_indicators if indicator in text_lower)
    entry_count = sum(1 for indicator in entry_indicators if indicator in text_lower)
    
    if senior_count > 0 or 'year' in text_lower:
        return 'senior'
    elif entry_count > 0:
        return 'entry'
    else:
        return 'mid'

def calculate_job_match_score(resume_skills, job_skills):
    """Calculate matching score between resume and job skills"""
    if not resume_skills or not job_skills:
        return 0
    
    resume_skills_lower = [skill.lower() for skill in resume_skills]
    job_skills_lower = [skill.lower() for skill in job_skills]
    
    # Find matching skills
    matching_skills = []
    for job_skill in job_skills_lower:
        for resume_skill in resume_skills_lower:
            if job_skill == resume_skill or job_skill in resume_skill or resume_skill in job_skill:
                matching_skills.append(job_skill)
                break
    
    # Calculate score
    score = (len(matching_skills) / len(job_skills_lower)) * 100
    return min(round(score, 2), 100)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Resume Analyzer API is running'})

@app.route('/api/upload-resume', methods=['POST'])
def upload_resume():
    """Handle resume upload and analysis"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Extract text from PDF
            extracted_text = extract_text_from_pdf(file_path)
            
            if not extracted_text.strip():
                return jsonify({'error': 'Could not extract text from PDF'}), 400
            
            # Analyze resume
            skills = extract_skills_from_text(extracted_text)
            experience_level = determine_experience_level(extracted_text)
            
            # Save to database
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO resumes (filename, extracted_text, skills, experience_level)
                    VALUES (?, ?, ?, ?)
                ''', (filename, extracted_text, json.dumps(skills), experience_level))
                resume_id = cursor.lastrowid
                conn.commit()
            
            # Clean up uploaded file
            os.remove(file_path)
            
            return jsonify({
                'success': True,
                'resume_id': resume_id,
                'skills': skills,
                'experience_level': experience_level,
                'text_length': len(extracted_text)
            })
        
        return jsonify({'error': 'Invalid file type. Please upload a PDF file.'}), 400
    
    except Exception as e:
        return jsonify({'error': f'Error processing resume: {str(e)}'}), 500

@app.route('/api/job-matches/<int:resume_id>', methods=['GET'])
def get_job_matches(resume_id):
    """Get job matches for a specific resume"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Get resume details
            cursor.execute('SELECT * FROM resumes WHERE id = ?', (resume_id,))
            resume = cursor.fetchone()
            
            if not resume:
                return jsonify({'error': 'Resume not found'}), 404
            
            resume_skills = json.loads(resume['skills'])
            resume_experience = resume['experience_level']
            
            # Get all jobs
            cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC')
            jobs = cursor.fetchall()
            
            # Calculate matches
            job_matches = []
            for job in jobs:
                job_skills = job['skills'].split(',')
                match_score = calculate_job_match_score(resume_skills, job_skills)
                
                # Find matching skills
                matching_skills = []
                resume_skills_lower = [skill.lower() for skill in resume_skills]
                for job_skill in job_skills:
                    if any(job_skill.lower() in resume_skill.lower() or resume_skill.lower() in job_skill.lower() 
                           for resume_skill in resume_skills_lower):
                        matching_skills.append(job_skill.strip())
                
                job_matches.append({
                    'id': job['id'],
                    'title': job['title'],
                    'company': job['company'],
                    'description': job['description'],
                    'skills': job_skills,
                    'experience_level': job['experience_level'],
                    'salary': job['salary'],
                    'match_score': match_score,
                    'matching_skills': matching_skills
                })
            
            # Sort by match score
            job_matches.sort(key=lambda x: x['match_score'], reverse=True)
            
            return jsonify({
                'success': True,
                'matches': job_matches,
                'total_matches': len(job_matches)
            })
    
    except Exception as e:
        return jsonify({'error': f'Error getting job matches: {str(e)}'}), 500

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Get all jobs"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC')
            jobs = cursor.fetchall()
            
            job_list = []
            for job in jobs:
                job_list.append({
                    'id': job['id'],
                    'title': job['title'],
                    'company': job['company'],
                    'description': job['description'],
                    'skills': job['skills'].split(','),
                    'experience_level': job['experience_level'],
                    'salary': job['salary'],
                    'created_at': job['created_at']
                })
            
            return jsonify({
                'success': True,
                'jobs': job_list,
                'total': len(job_list)
            })
    
    except Exception as e:
        return jsonify({'error': f'Error getting jobs: {str(e)}'}), 500

@app.route('/api/jobs', methods=['POST'])
def create_job():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    """Create a new job"""
    try:
        data = request.get_json()
        
        required_fields = ['title', 'company', 'description', 'skills', 'experience_level']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Format skills
        if isinstance(data['skills'], list):
            skills_str = ','.join(data['skills'])
        else:
            skills_str = data['skills']
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO jobs (title, company, description, skills, experience_level, salary)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data['title'],
                data['company'],
                data['description'],
                skills_str,
                data['experience_level'],
                data.get('salary', '')
            ))
            job_id = cursor.lastrowid
            conn.commit()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Job created successfully'
        })
    
    except Exception as e:
        return jsonify({'error': f'Error creating job: {str(e)}'}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get application statistics"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Get total jobs
            cursor.execute('SELECT COUNT(*) FROM jobs')
            total_jobs = cursor.fetchone()[0]
            
            # Get total resumes processed
            cursor.execute('SELECT COUNT(*) FROM resumes')
            total_resumes = cursor.fetchone()[0]
            
            # Calculate success rate (mock calculation)
            success_rate = min(85 + (total_resumes * 2), 95) if total_resumes > 0 else 0
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_jobs': total_jobs,
                    'total_resumes': total_resumes,
                    'success_rate': f"{success_rate}%"
                }
            })
    
    except Exception as e:
        return jsonify({'error': f'Error getting stats: {str(e)}'}), 500

@app.route('/')
def index():
    return send_from_directory('.', 'smart_resume_analyzer.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

