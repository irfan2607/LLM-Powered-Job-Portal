from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import google.generativeai as genai
import PyPDF2
import os
import json
from datetime import datetime
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

app = Flask(__name__)
CORS(app)

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

class DatabaseManager:
    def __init__(self, db_path='jobs.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                description TEXT,
                requirements TEXT,
                posted_date DATE,
                skills TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY,
                name TEXT,
                email TEXT,
                resume_text TEXT,
                skills TEXT,
                created_date DATE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY,
                candidate_id INTEGER,
                job_id INTEGER,
                match_score REAL,
                matching_skills TEXT,
                missing_skills TEXT,
                explanation TEXT,
                created_date DATE,
                FOREIGN KEY (candidate_id) REFERENCES candidates (id),
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query, params=()):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.commit()
        conn.close()
        return [dict(row) for row in result]

class LLMSkillsAnalyzer:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-pro')
    
    def extract_skills(self, text):
        prompt = f"""
        Extract technical skills and programming languages from the following text.
        Return only a JSON array of skills, no other text.
        
        Text: {text[:3000]}
        """
        
        try:
            response = self.model.generate_content(prompt)
            skills_text = response.text.strip()
            # Clean response and parse JSON
            skills_text = skills_text.replace('```json', '').replace('```', '').strip()
            return json.loads(skills_text)
        except Exception as e:
            print(f"Error extracting skills: {e}")
            return []
    
    def generate_match_explanation(self, candidate_skills, job_skills, match_score):
        prompt = f"""
        Generate a brief explanation for a job match between candidate and job.
        
        Candidate Skills: {candidate_skills}
        Job Required Skills: {job_skills}
        Match Score: {match_score}
        
        Provide 2-3 sentences explaining the match quality and key strengths.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return "Match analysis based on skills compatibility."

class ResumeProcessor:
    @staticmethod
    def extract_text_from_pdf(pdf_file):
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            raise Exception(f"PDF processing error: {str(e)}")

class MatchingEngine:
    def __init__(self, skills_analyzer):
        self.skills_analyzer = skills_analyzer
        self.vectorizer = TfidfVectorizer()
    
    def calculate_match_score(self, candidate_skills, job_skills):
        if not candidate_skills or not job_skills:
            return 0.0
        
        # Convert skills to strings for vectorization
        candidate_skills_str = ' '.join(candidate_skills)
        job_skills_str = ' '.join(job_skills)
        
        try:
            # Create TF-IDF vectors
            tfidf_matrix = self.vectorizer.fit_transform([candidate_skills_str, job_skills_str])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            return float(similarity[0][0]) * 100
        except:
            # Fallback to Jaccard similarity
            candidate_set = set(candidate_skills)
            job_set = set(job_skills)
            
            if not job_set:
                return 0.0
                
            intersection = candidate_set.intersection(job_set)
            union = candidate_set.union(job_set)
            
            return (len(intersection) / len(union)) * 100

# Initialize services
db_manager = DatabaseManager()
skills_analyzer = LLMSkillsAnalyzer()
resume_processor = ResumeProcessor()
matching_engine = MatchingEngine(skills_analyzer)

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    try:
        search = request.args.get('search', '')
        location = request.args.get('location', '')
        
        query = "SELECT * FROM jobs WHERE 1=1"
        params = []
        
        if search:
            query += " AND (title LIKE ? OR company LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])
        
        if location:
            query += " AND location LIKE ?"
            params.append(f'%{location}%')
        
        query += " ORDER BY posted_date DESC"
        
        jobs = db_manager.execute_query(query, params)
        return jsonify(jobs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/seed', methods=['POST'])
def seed_jobs():
    """Seed jobs from JSONPlaceholder (adapted)"""
    try:
        response = requests.get('https://jsonplaceholder.typicode.com/posts')
        posts = response.json()[:20]  # Get first 20 posts as sample jobs
        
        companies = ['Google', 'Microsoft', 'Amazon', 'Meta', 'Netflix', 'Apple', 'Tesla', 'Uber']
        locations = ['San Francisco, CA', 'New York, NY', 'Austin, TX', 'Seattle, WA', 'Boston, MA']
        
        for i, post in enumerate(posts):
            company = companies[i % len(companies)]
            location = locations[i % len(locations)]
            
            # Extract skills from post body
            skills = skills_analyzer.extract_skills(post['body'])
            
            db_manager.execute_query('''
                INSERT OR REPLACE INTO jobs 
                (id, title, company, location, description, requirements, posted_date, skills)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post['id'],
                post['title'],
                company,
                location,
                post['body'],
                f"Requirements for {post['title']}",
                datetime.now().date(),
                json.dumps(skills)
            ))
        
        return jsonify({'message': f'Seeded {len(posts)} jobs'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-resume', methods=['POST'])
def upload_resume():
    try:
        if 'resume' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['resume']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Extract text from PDF
        resume_text = resume_processor.extract_text_from_pdf(file)
        
        # Extract skills using LLM
        skills = skills_analyzer.extract_skills(resume_text)
        
        # Store candidate data
        candidate_id = db_manager.execute_query(
            'INSERT INTO candidates (name, email, resume_text, skills, created_date) VALUES (?, ?, ?, ?, ?)',
            ('Candidate', 'candidate@example.com', resume_text, json.dumps(skills), datetime.now().date())
        )
        
        return jsonify({
            'candidate_id': candidate_id,
            'resume_text': resume_text[:500] + '...' if len(resume_text) > 500 else resume_text,
            'skills': skills
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations/<int:candidate_id>', methods=['GET'])
def get_recommendations(candidate_id):
    try:
        # Get candidate data
        candidates = db_manager.execute_query(
            'SELECT * FROM candidates WHERE id = ?', 
            (candidate_id,)
        )
        
        if not candidates:
            return jsonify({'error': 'Candidate not found'}), 404
        
        candidate = candidates[0]
        candidate_skills = json.loads(candidate['skills'])
        
        # Get all jobs
        jobs = db_manager.execute_query('SELECT * FROM jobs')
        
        recommendations = []
        for job in jobs:
            job_skills = json.loads(job['skills'])
            
            # Calculate match score
            match_score = matching_engine.calculate_match_score(candidate_skills, job_skills)
            
            # Find matching and missing skills
            matching_skills = list(set(candidate_skills) & set(job_skills))
            missing_skills = list(set(job_skills) - set(candidate_skills))
            
            # Generate explanation
            explanation = skills_analyzer.generate_match_explanation(
                candidate_skills, job_skills, match_score
            )
            
            recommendations.append({
                'job_id': job['id'],
                'job_title': job['title'],
                'company': job['company'],
                'location': job['location'],
                'match_score': round(match_score, 1),
                'matching_skills': matching_skills,
                'missing_skills': missing_skills,
                'explanation': explanation
            })
        
        # Sort by match score descending
        recommendations.sort(key=lambda x: x['match_score'], reverse=True)
        
        return jsonify(recommendations[:10])  # Return top 10 matches
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)