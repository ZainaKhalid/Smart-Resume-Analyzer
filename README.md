# 📄 Smart Resume Analyzer

> An AI-powered web application that analyzes resumes, extracts skills & experience, and suggests the best-matching jobs.  
> Built with **Flask (Python)**, **HTML/CSS/JS**, and **SQLite**.  

---

## 🚀 Features

✅ Upload a PDF resume & extract text using NLP.  
✅ Skill & experience level detection with basic NLP and keyword analysis.  
✅ AI-powered job matching based on resume skills & job requirements.  
✅ Admin Dashboard:  
  🔹 Add, edit, and view jobs.  
  🔹 View stats of jobs & resumes processed.  
✅ User Authentication: signup, login, logout.  
✅ Session-based admin authentication with secure password hashing.  
✅ Clean, animated frontend with responsive design.

---

📊 Technologies Used
Backend: Python, Flask, SQLite

Frontend: HTML5, CSS3, JavaScript

NLP: spaCy, regex-based extraction

Authentication: Flask sessions, password hashing

Database: SQLite3

---

⚙️ API Endpoints

| Method | Endpoint                | Description                  |
| ------ | ----------------------- | ---------------------------- |
| GET    | `/api/health`           | Health check                 |
| POST   | `/api/upload-resume`    | Upload & analyze resume      |
| GET    | `/api/job-matches/<id>` | Get job matches for a resume |
| POST   | `/api/signup`           | Admin signup                 |
| POST   | `/api/login`            | Admin login                  |
| POST   | `/api/logout`           | Admin logout                 |
| GET    | `/api/jobs`             | List all jobs                |
| POST   | `/api/jobs`             | Add new job (admin only)     |
| GET    | `/api/stats`            | Get platform stats           |
| GET    | `/api/check-admin`      | Check if admin is logged in  |


---

## 📂 Project Structure
├── flask_backend.py # Main Flask backend

├── smart_resume_analyzer.html # Frontend UI

├── resume_analyzer.db # SQLite database

├── uploads/ # Folder for uploaded resumes (temporary)

├── README.md # Project documentation

└── Requirements.txt # Python dependencies

---

2️⃣ Install dependencies
Make sure Python 3.8+ is installed.
(Optional: create a virtual environment.)

	pip install -r requirements.txt
Or manually install the key packages:

	pip install flask flask-cors werkzeug spacy pypdf2
	python -m spacy download en_core_web_sm

---

3️⃣ Run the Flask backend:

	python flask_backend.py
By default, it runs on:

	http://127.0.0.1:5000/

---

4️⃣ Open the Frontend
Visit:

	http://127.0.0.1:5000/
You can also directly open the smart_resume_analyzer.html file in the browser.
However, for authentication & admin dashboard, you must use the Flask server so cookies work properly.

---

🔒 Admin Login
First, sign up as a new admin via the admin page (/admin) in the UI.

Then, log in with the created credentials.

You can now access the dashboard to add/manage jobs & see stats.

---

📈 Improvements & Future Work
Integrate advanced NLP (e.g., transformer models) for more accurate skill extraction.

Add email notifications for users when a job match is found.

Improve job recommendation scoring with ML-based ranking.

Deploy on cloud (Heroku, AWS, etc.) with production-ready server (gunicorn, etc.).

---

📽️ Demo Video
🔗 [![Watch the demo](https://img.youtube.com/vi/XTUkD7jVzLc/0.jpg)](https://www.youtube.com/watch?v=XTUkD7jVzLc)

---

📄 License
MIT License © 2025 Zainab Khalid


