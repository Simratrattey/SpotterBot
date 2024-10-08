from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.exceptions import HttpResponseError
from dateutil import parser
from datetime import datetime

app = Flask(__name__)
CORS(app)

def clean_text(text):
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    return text.lower().split()

def calculate_experience_months(start_date, end_date):
    try:
        start = parser.parse(start_date)
        end_date = end_date.strip().lower()
        if end_date in ["current", "present", "till date", "ongoing", "to present", "till"]:
            end = datetime.now()
        else:
            end = parser.parse(end_date)
        months = (end.year - start.year) * 12 + end.month - start.month
        return months
    except Exception as e:
        print(f"Error parsing dates: {start_date} - {end_date}, Error: {e}")
        return 0

def analyze_document(endpoint, key, file_path, model_id="Model12345"):
    document_analysis_client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    total_experience_months = 0
    extracted_skills = []
    extracted_projects = []
    name = ""

    try:
        with open(file_path, "rb") as f:
            poller = document_analysis_client.begin_analyze_document(model_id, document=f)
            result = poller.result()

        print("Document analysis completed.")
        
        for idx, document in enumerate(result.documents):
            print(f"Analyzing document #{idx + 1}")
            for field_name, field in document.fields.items():
                if field_name.lower() == "name":
                    name = field.value
                elif field_name.lower() == "experience":
                    if field.value_type == "list":
                        for item in field.value:
                            if item.value_type == "dictionary":
                                date_field = item.value.get('DATE')
                                if date_field and date_field.value:
                                    print(f"Extracted date field: {date_field.value}")
                                    if " - " in date_field.value or " to " in date_field.value or " TO " in date_field.value or "-" in date_field.value:
                                        dates = re.split(r'\s*-\s*|\s*to\s*', date_field.value, flags=re.IGNORECASE)
                                        if len(dates) == 2:
                                            start_date = dates[0].strip()
                                            end_date = dates[1].strip()
                                            print(f"Parsed start date: {start_date}, end date: {end_date}")
                                            experience_months = calculate_experience_months(start_date, end_date)
                                            print(f"Experience from {start_date} to {end_date}: {experience_months} months")
                                            total_experience_months += experience_months
                elif field_name.lower() == "skills":
                    if field.value_type == "string":
                        cleaned_words = clean_text(field.value.replace("skills", ""))
                        extracted_skills.extend(cleaned_words)
                    elif field.value_type == "list":
                        for item in field.value:
                            if item.value_type == "string":
                                cleaned_words = clean_text(item.value.replace("skills", ""))
                                extracted_skills.extend(cleaned_words)
                elif field_name.lower() == "projects":
                    if field.value:
                        if field.value_type == "string":
                            cleaned_words = clean_text(field.value.replace("projects", ""))
                            extracted_projects.extend(cleaned_words)
                        elif field.value_type == "list":
                            for item in field.value:
                                if item.value and item.value_type == "string":
                                    cleaned_words = clean_text(item.value.replace("projects", ""))
                                    extracted_projects.extend(cleaned_words)

    except HttpResponseError as e:
        print(f"Error analyzing document: {e.message}")

    return name, total_experience_months, extracted_skills, extracted_projects

def compare_experience(extracted_months, required_months):
    difference = extracted_months - required_months
    score = difference  # 1 point added or deducted for each month difference
    return score

def compare_skills(extracted_skills, required_skills, skill_weights):
    extracted_text = ' '.join(extracted_skills)
    matched_skills = []
    total_score = 0

    for skill, weight in zip(required_skills, skill_weights):
        if skill in extracted_text:
            matched_skills.append(skill)
            total_score += weight

    return total_score, matched_skills

def compare_projects(extracted_projects, required_projects):
    extracted_text = ' '.join(extracted_projects)
    matched_projects = []
    total_score = 0
    score_per_project = 10

    for project in required_projects:
        if project in extracted_text:
            matched_projects.append(project)
            total_score += score_per_project

    return total_score, matched_projects

def process_resumes(endpoint, key, resume_directory, required_experience_months, required_skills, skill_weights, required_projects):
    scores = []

    for idx, file_name in enumerate(os.listdir(resume_directory)):
        file_path = os.path.join(resume_directory, file_name)
        if os.path.isfile(file_path) and file_path.lower().endswith(".pdf"):
            print(f"Processing resume {idx + 1}: {file_name}")
            
            name, total_experience_months, extracted_skills, extracted_projects = analyze_document(endpoint, key, file_path)
            
            # Calculate and display experience scores
            print(f"Extracted total months of experience: {total_experience_months}")
            experience_score = compare_experience(total_experience_months, required_experience_months)
            print(f"Experience score: {experience_score}")
            
            # Calculate and display skill scores
            print(f"Extracted skills: {extracted_skills}")
            total_skill_score, matched_skills = compare_skills(extracted_skills, required_skills, skill_weights)
            print(f"Matched skills: {matched_skills}")
            print(f"Total skill score: {total_skill_score:.2f}/100")
            
            # Calculate and display project scores
            print(f"Extracted projects: {extracted_projects}")
            if not extracted_projects:
                print("No projects found.")
                project_score = 0
            else:
                project_score, matched_projects = compare_projects(extracted_projects, required_projects)
                print(f"Matched projects: {matched_projects}")
                print(f"Total project score: {project_score}")

            # Calculate and display final score
            final_score = experience_score + total_skill_score + project_score
            print(f"Final score for resume {idx + 1}: {final_score}\n")

            # Append result for sorting later
            scores.append((name if name else file_name, final_score))

    return scores

@app.route('/upload', methods=['POST'])
def upload():
    required_experience_months = int(request.form['required_experience_months'])
    required_skills = request.form.getlist('required_skills[]')
    skill_weights = list(map(float, request.form.getlist('skill_weights[]')))
    required_projects = request.form.getlist('required_projects[]')
    num_shortlist = int(request.form['num_shortlist'])

    resume_directory = os.path.join(os.path.dirname(__file__), 'testResumes')

    # Clear the directory before uploading new resumes
    if os.path.exists(resume_directory):
        for filename in os.listdir(resume_directory):
            file_path = os.path.join(resume_directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    os.rmdir(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    else:
        os.makedirs(resume_directory)

    # Save new resumes to the directory
    for file in request.files.getlist('files'):
        file_path = os.path.join(resume_directory, file.filename)
        file.save(file_path)

    endpoint = "https://resume9811.cognitiveservices.azure.com/"
    key = "1523cf62ddf44443b363a21405c4882d"

    scores = process_resumes(endpoint, key, resume_directory, required_experience_months, required_skills, skill_weights, required_projects)

    sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)

    shortlisted_resumes = [{'name': name, 'score': score} for name, score in sorted_scores[:num_shortlist]]

    return jsonify(shortlisted_resumes)

if __name__ == "__main__":
    app.run(debug=True)
