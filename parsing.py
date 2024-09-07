import difflib
import os
from flask import Flask, render_template, request, redirect, url_for
from PyPDF2 import PdfReader
import re
import requests
from flask_mysqldb import MySQL 
from flask_appp import *
from datetime import datetime
from werkzeug.utils import secure_filename
import nltk
from nltk.tokenize import word_tokenize
from calendar import monthrange
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import fitz  # PyMuPDF
import json
#app = Flask(__name__)
app.secret_key = 'secret'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Yash2611'
app.config['MYSQL_DB'] = 'flask_app'
UPLOAD_FOLDER = 'static/resumes'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mysql = MySQL(app)

class Job:
    def __init__(self, job_id, title, description, req_skills, location, salary):
        self.job_id = job_id,
        self.title = title,
        self.description = description,
        self.req_skills = req_skills
        self.location = location, 
        self.salary = salary

@app.route('/abc/<int:job_id>')
def abc(job_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT job_description FROM jobss WHERE id = %s", (job_id,))
    job_description_json = cur.fetchone()[0]
    cur.close()
    
    if job_description_json:
        # Parse JSON data
        job_description = json.loads(job_description_json)
        return render_template('uploadpdf.html', job_id=job_id, job_description=job_description)
    else:
        return "Job not found"

def extract_text_from_pdf(pdf_path):
    document = fitz.open(pdf_path)
    text = ""
    for page_num in range(len(document)):
        page = document.load_page(page_num)
        text += page.get_text() + "\n"
    return text


prompt_template1 = """

This above is resume content, Extract the below information and store in json format, give me that:
1. Name (find out intelligently)
2. email (if not keep it null)
3. MobileNO (if not mentioned keep null)
4. Education (extract information from relevant section):
this key will contain array of objects, that will have keys: collegename, degree, marks(if cgpa is mentioned as marks (means marks showing below 10), multiply by 10 and store in marks, if percentage is there, keep as it is), starting period(year), ending period(year), (if any of info not in resume keep values null, if only  year is there store as ending period.)
5. Projects(this key is also array of objects):
 each object will contain name, tools_technologies, skills (if not mentioned find out from description of project intelligently), durationInMonths(if starting and ending month and year is mentioned then fill duration in months otherwise null (intiger))
6. Experience (this key is also array of objects): (Note: if experience not found, show keys but values null but startingPeriod and endingPeriod: [null, null], tools_technolgies and skills_learnt: [])(position, companyName, startingPeriod (value: array: month, year format), endingPeriod(value: array: month, year format) (if not mentioned keep them null, if only year, month mentioned, fill it in endingPeriod, if only year mentioned keep both null, duration mentioned only in years keep months null), tools_technologies(find out intelligently from the description), skills_learnt(also find them intelligently from description).
7. Skills:(values will be array of all skills) from skills section, extract skills, if sub section is there in skills, leave that, all skills should be fill in array collectively, also intelligently find skills from whole resume add it in this array)

Create json like above requirement, no more keys now, keys names should be exactly same. I will use this json for further development of ATS score generation.
"""

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    print("chk file ")
    if file.filename == '':
        return redirect(request.url)
    
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Extract text from the uploaded PDF
        text = extract_text_from_pdf(file_path)
        
        # Prepare the prompt for the ChatGPT API

        
        proper_prompt = text + prompt_template1
        print(proper_prompt)
        # ChatGPT API request  
        url = "https://chatgpt-42.p.rapidapi.com/chatgpt"
        headers = {
            "x-rapidapi-key": "2ee53df76emsh74af97f1bc88d0bp10986ajsn128f0ec6727b",
            "x-rapidapi-host": "chatgpt-42.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": proper_prompt
                }
            ],
            "web_access": False
        }
        
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        result_text = data.get("result", "")
        print(result_text)
        # Extract JSON part from result text
        json_pattern = r"({.*})"
        match = re.search(json_pattern, result_text, re.DOTALL)

        if match:
            json_data = match.group(1)
            try:
                parsed_json = json.loads(json_data)
            except json.JSONDecodeError:
                parsed_json = {}

            # Save JSON to a file named after the session's  username
            json_filename = f"{session['username']}.json"
            json_filepath = os.path.join(app.config['UPLOAD_FOLDER'], json_filename)
            
            with open(json_filepath, 'w') as file:
                json.dump(parsed_json, file, indent=4)
            
            print('json is',parsed_json)
            # Now you can use `parsed_json` to display or process the extracted information
            return render_template('result.html', resume_data=parsed_json)
        else:
            return "No JSON part found in the response."

    return redirect(url_for('index'))

 
@app.route('/display', methods=['POST'])
def display():
    # Get the submitted form data
    resume_data = request.form.to_dict(flat=False)  # Retrieves all form data as a dictionary of lists

    # Render the display template with resume data
    return render_template('display.html', resume_data=resume_data)


 



    


@app.route('/create_job', methods=['POST', 'GET'])
def create_job():
    if request.method == 'POST':
        title = request.form['title']
        company = request.form['company']
        location = request.form['location']
        
        # Get responsibilities, skills, experience, and education as JSON strings
        responsibilities = request.form.getlist('responsibilities[]')
        skills = request.form.getlist('skills[]')
        experience_required = request.form['experience_required']
        education_required = request.form['education_required']
        employment_type = request.form['employment_type']
        salary = request.form['salary']
        
        # Create the job description dictionary
        job_description = {
            "title": title,
            "company": company,
            "location": location,
            "responsibilities": responsibilities,
            "skills": skills,
            "experience_required": experience_required,
            "education_required": education_required,
            "employment_type": employment_type,
            "salary": salary
        }
        
        # Convert the job description dictionary to a JSON string
        job_description_json = json.dumps(job_description)
        
        # Insert the job into the database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO jobss (job_description) VALUES (%s)", (job_description_json,))
        mysql.connection.commit()
        job_id = cur.lastrowid
        cur.close()
        return redirect(url_for('created_job', job_id=job_id))
    
    return render_template('create_job.html')

@app.route('/created_job/<int:job_id>')
def created_job(job_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT job_description FROM jobss WHERE id = %s", (job_id,))
    result = cur.fetchone()
    cur.close()
    
    if result:
        # Extract the JSON from the result
        job_description = json.loads(result[0])
        return render_template('created_job.html', job=job_description)
    else:
        return "No job found"

@app.route('/jobs')
def jobs():
    if is_logged_in():
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, job_description FROM jobss")
        jobs = cur.fetchall()
        cur.close()
        
        # Parse JSON data
        jobs = [{
            'job_id': job[0],
            'description': json.loads(job[1])
        } for job in jobs]
        
        return render_template('jobs.html', jobs=jobs)
    else:
        return redirect(url_for('login'))



@app.route('/display_resumes')
def display_resumes():
    cur = mysql.connection.cursor()
    cur.execute("SELECT job_id, filename FROM applications")
    job_resumes = cur.fetchall()
    cur.close()
    return render_template('display_resumes.html', job_resumes=job_resumes)

@app.route('/job_titles')
def job_titles():
  if 'is_admin' in session and session['is_admin']:
    cur = mysql.connection.cursor()
    cur.execute("SELECT DISTINCT title FROM applications")
    titles = [row[0] for row in cur.fetchall()]
    cur.close()
    return render_template('job_titles.html', titles=titles)
  else:
      return redirect(url_for('login'))

@app.route('/job_applications/<string:title>')
def job_applications(title):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM applications WHERE title = %s ORDER BY final_score DESC", (title,))
    applications = cur.fetchall()
    cur.close()
    return render_template('job_applications.html', title=title, applications=applications)




if __name__ == '__main__':
    app.run(debug=True)
