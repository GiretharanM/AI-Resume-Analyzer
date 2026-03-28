from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import spacy
from PyPDF2 import PdfReader
import os

app = Flask(__name__)
app.secret_key = "super_secret_key_for_placements"

# --- DATABASE CONFIGURATION ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Load NLP Model
nlp = spacy.load("en_core_web_sm")

# --- DATA DICTIONARIES ---
MASTER_SKILLS = ["python", "sql", "java", "c++", "html", "css", "javascript", "react", "machine learning", "nlp", "excel", "aws", "docker", "power bi", "pandas", "deep learning"]

JOB_REQUIREMENTS = {
    "Data Analyst": ["python", "sql", "excel", "machine learning", "pandas", "power bi"],
    "Web Developer": ["html", "css", "javascript", "react"],
    "Backend Developer": ["python", "sql", "java", "aws", "docker"],
    "Data Scientist": ["python", "sql", "machine learning", "deep learning", "pandas", "nlp"]
}

COURSE_LINKS = {
    "python": "https://www.coursera.org/learn/python",
    "sql": "https://www.udemy.com/course/the-complete-sql-bootcamp/",
    "machine learning": "https://www.coursera.org/specializations/machine-learning",
    "react": "https://react.dev/learn",
    "javascript": "https://www.freecodecamp.org/learn/",
    "deep learning": "https://www.coursera.org/specializations/deep-learning",
    "aws": "https://aws.amazon.com/training/"
}

CAREER_ROADMAPS = {
    "Data Analyst": ["Excel & Stats", "SQL Basics", "Python/Pandas", "Power BI", "Portfolio Projects"],
    "Web Developer": ["HTML/CSS/Git", "JavaScript", "React.js", "Backend APIs", "Deployments"],
    "Backend Developer": ["Python/Java", "SQL Databases", "REST APIs", "System Design", "Cloud/Docker"],
    "Data Scientist": ["Python & Math", "Advanced SQL", "Machine Learning", "Deep Learning", "End-to-End Projects"]
}

INTERVIEW_QUESTIONS = {
    "Data Analyst": [
        "Explain the difference between WHERE and HAVING in SQL.",
        "How do you handle missing values in a dataset using Pandas?",
        "What is the difference between a LEFT JOIN and an INNER JOIN?"
    ],
    "Web Developer": [
        "What is the Virtual DOM in React and how does it work?",
        "Explain the difference between let, const, and var in JavaScript.",
        "What are React Hooks? Can you name a few?"
    ],
    "Backend Developer": [
        "Explain the principles of RESTful API design.",
        "What is the difference between SQL and NoSQL databases?",
        "How does Docker help in deployment?"
    ],
    "Data Scientist": [
        "Explain the bias-variance tradeoff.",
        "How does a Random Forest algorithm work?",
        "What is the difference between supervised and unsupervised learning?"
    ]
}

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    history = db.relationship('History', backref='user', lazy=True)

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Float, nullable=False)
    matched_skills = db.Column(db.String(500), nullable=False)
    missing_skills = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

with app.app_context():
    db.create_all()

# --- HELPER FUNCTIONS ---
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = "".join([page.extract_text() for page in reader.pages])
    return text.lower()

def extract_skills(text):
    doc = nlp(text)
    skills = set([token.text for token in doc if token.text in MASTER_SKILLS])
    for skill in MASTER_SKILLS:
        if " " in skill and skill in text:
            skills.add(skill)
    return list(skills)

def generate_resume_summary(skills, target_job):
    if not skills:
        return f"Motivated IT student eager to learn and contribute as a {target_job}."
    top_skills = [skill.capitalize() for skill in skills[:3]]
    if len(top_skills) > 1:
        skills_str = ", ".join(top_skills[:-1]) + f", and {top_skills[-1]}"
    else:
        skills_str = top_skills[0]
    return f"Motivated IT student aspiring to excel as a {target_job}. Equipped with a strong foundation in {skills_str}, with a proven ability to solve complex problems and a passion for continuous learning."

def fetch_live_jobs(job_title):
    formatted_job = job_title.replace(" ", "%20")
    naukri_job = job_title.replace(" ", "-").lower()
    return [
        {"platform": "LinkedIn", "title": f"{job_title} Openings", "link": f"https://www.linkedin.com/jobs/search/?keywords={formatted_job}", "color": "#0a66c2"},
        {"platform": "Naukri", "title": f"Latest {job_title} Jobs", "link": f"https://www.naukri.com/{naukri_job}-jobs", "color": "#ff7555"},
        {"platform": "Indeed", "title": f"Active {job_title} Roles", "link": f"https://in.indeed.com/jobs?q={formatted_job}", "color": "#003a9b"}
    ]

# --- ROUTES ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if User.query.filter_by(username=username).first():
            flash("Username already exists!")
            return redirect(url_for("register"))
        new_user = User(username=username, password=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials!")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_history = History.query.filter_by(user_id=session["user_id"]).order_by(History.id.desc()).all()

    if request.method == "POST":
        file = request.files.get("resume")
        jd_text = request.form.get("job_description")

        if file and file.filename.endswith('.pdf'):
            resume_text = extract_text_from_pdf(file)
            user_skills = extract_skills(resume_text)
            
            best_job = "Data Analyst"
            highest_match = 0
            for job, req_skills in JOB_REQUIREMENTS.items():
                match_count = sum(1 for skill in req_skills if skill in user_skills)
                if match_count > highest_match:
                    highest_match = match_count
                    best_job = job

            req_skills = extract_skills(jd_text.lower()) if jd_text else JOB_REQUIREMENTS.get(best_job, [])
            matched = [s for s in req_skills if s in user_skills]
            missing = [s for s in req_skills if s not in user_skills]
            score = round((len(matched) / max(len(req_skills), 1)) * 100, 2)
            
            new_record = History(score=score, matched_skills=", ".join(matched), missing_skills=", ".join(missing), user_id=session["user_id"])
            db.session.add(new_record)
            db.session.commit()

            courses = {s: COURSE_LINKS.get(s, f"https://www.youtube.com/results?search_query={s}+course") for s in missing}
            roadmap = CAREER_ROADMAPS.get(best_job, ["Keep Learning", "Build Projects"])
            questions = INTERVIEW_QUESTIONS.get(best_job, ["Tell me about yourself.", "Describe a challenging project."])
            generated_summary = generate_resume_summary(user_skills, best_job)
            live_jobs = fetch_live_jobs(best_job)

            return render_template("index.html", skills=user_skills, score=score, missing=missing, courses=courses, history=user_history, best_job=best_job, roadmap=roadmap, questions=questions, summary=generated_summary, live_jobs=live_jobs, show_results=True)

    return render_template("index.html", show_results=False, history=user_history)

if __name__ == "__main__":
    app.run(debug=True)