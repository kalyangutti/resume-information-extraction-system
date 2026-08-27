"""
Script to generate sample resume files (PDF + DOCX) for testing.
Run once from the project root: python create_sample_resumes.py
"""
import json
import io
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(ROOT, "sample_resumes")
OUTPUT_DIR = os.path.join(ROOT, "sample_outputs")
os.makedirs(SAMPLE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# Resume 1 — Software Developer PDF
# ============================================================
RESUME_1_TEXT = """Arjun Sharma
arjun.sharma@email.com | +91 9876543210
linkedin.com/in/arjunsharma | github.com/arjunsharma

SUMMARY
Experienced Software Engineer with 3+ years building scalable backend systems using Python and FastAPI.

SKILLS
Python, FastAPI, Django, PostgreSQL, Redis, Docker, Kubernetes, AWS, Git, REST APIs, CI/CD, SQL, Linux

EXPERIENCE

Software Engineer
Infosys Limited
June 2022 - Present

- Developed microservices architecture using FastAPI and Docker
- Reduced API latency by 40% via Redis caching layer
- Automated deployment pipelines with GitHub Actions

Software Engineer Intern
TCS (Tata Consultancy Services)
January 2022 - May 2022

- Built RESTful APIs for internal HR portal using Django
- Wrote unit tests achieving 85% coverage

EDUCATION

B.Tech in Computer Science
Indian Institute of Technology, Delhi
2018 - 2022

CERTIFICATIONS
AWS Certified Solutions Architect
"""

RESUME_1_JSON = {
    "name": "Arjun Sharma",
    "email": "arjun.sharma@email.com",
    "phone": "+91 9876543210",
    "skills": [
        "Python", "FastAPI", "Django", "PostgreSQL", "Redis",
        "Docker", "Kubernetes", "AWS", "Git", "REST APIs", "CI/CD", "SQL", "Linux"
    ],
    "education": [
        {"degree": "B.Tech in Computer Science", "institution": "Indian Institute of Technology, Delhi"}
    ],
    "experience": [
        {
            "job_title": "Software Engineer",
            "company": "Infosys Limited",
            "duration": "June 2022 - Present"
        },
        {
            "job_title": "Software Engineer Intern",
            "company": "TCS (Tata Consultancy Services)",
            "duration": "January 2022 - May 2022"
        }
    ],
    "linkedin": "https://linkedin.com/in/arjunsharma",
    "github": "https://github.com/arjunsharma"
}

# ============================================================
# Resume 2 — Student/Fresher DOCX
# ============================================================
RESUME_2_TEXT = """Priya Mehta
priya.mehta@gmail.com
+91 8765432109
linkedin.com/in/priyamehta
github.com/priyamehta

OBJECTIVE
Recent B.Sc graduate seeking entry-level Data Science role.

EDUCATION

B.Sc in Data Science
Pune University
2020 - 2023

SKILLS
Python, Machine Learning, Deep Learning, Scikit-learn, TensorFlow, Pandas, NumPy, Matplotlib, SQL, Git, Jupyter Notebook

INTERNSHIPS

Data Science Intern
Analytics India Pvt Ltd
May 2023 - July 2023

- Built classification models for customer churn prediction
- Performed exploratory data analysis on 50k+ records

PROJECTS
- Sentiment Analysis Web App using NLP and Flask
- Image Classification with CNN (TensorFlow + Keras)
"""

RESUME_2_JSON = {
    "name": "Priya Mehta",
    "email": "priya.mehta@gmail.com",
    "phone": "+91 8765432109",
    "skills": [
        "Python", "Machine Learning", "Deep Learning", "Scikit-learn",
        "TensorFlow", "Pandas", "NumPy", "Matplotlib", "SQL", "Git", "Jupyter Notebook"
    ],
    "education": [
        {"degree": "B.Sc in Data Science", "institution": "Pune University"}
    ],
    "experience": [
        {
            "job_title": "Data Science Intern",
            "company": "Analytics India Pvt Ltd",
            "duration": "May 2023 - July 2023"
        }
    ],
    "linkedin": "https://linkedin.com/in/priyamehta",
    "github": "https://github.com/priyamehta"
}

# ============================================================
# Resume 3 — ML/DevOps Developer PDF
# ============================================================
RESUME_3_TEXT = """Ravi Kumar
ravi.kumar@outlook.com | +91 9123456789
https://linkedin.com/in/ravikumar | https://github.com/ravikumar

PROFESSIONAL SUMMARY
Senior ML Engineer with 5 years of experience building production ML pipelines on AWS and GCP.

TECHNICAL SKILLS
Python, PyTorch, TensorFlow, Scikit-learn, MLOps, Apache Kafka, Apache Airflow,
Docker, Kubernetes, AWS SageMaker, Google Cloud Platform, Terraform, Jenkins, Git,
PostgreSQL, MongoDB, Redis, FastAPI, REST APIs, NLP, Computer Vision, BERT

PROFESSIONAL EXPERIENCE

Senior ML Engineer
Google India Pvt Ltd
March 2021 - Present

- Designed and deployed large-scale NLP models using BERT and PyTorch
- Built automated ML pipelines with Apache Airflow and Kubeflow
- Reduced model training time by 60% via distributed training on AWS SageMaker

ML Engineer
Flipkart Internet Pvt Ltd
July 2019 - February 2021

- Built recommendation system serving 10M+ daily users
- Developed real-time fraud detection with Apache Kafka

EDUCATION

M.Tech in Artificial Intelligence
IIT Bombay
2017 - 2019

B.Tech in Electronics
NIT Trichy
2013 - 2017
"""

RESUME_3_JSON = {
    "name": "Ravi Kumar",
    "email": "ravi.kumar@outlook.com",
    "phone": "+91 9123456789",
    "skills": [
        "Python", "PyTorch", "TensorFlow", "Scikit-learn", "MLOps",
        "Apache Kafka", "Apache Airflow", "Docker", "Kubernetes",
        "AWS SageMaker", "Google Cloud Platform", "Terraform", "Jenkins",
        "Git", "PostgreSQL", "MongoDB", "Redis", "FastAPI", "REST APIs",
        "NLP", "Computer Vision", "BERT"
    ],
    "education": [
        {"degree": "M.Tech in Artificial Intelligence", "institution": "IIT Bombay"},
        {"degree": "B.Tech in Electronics", "institution": "NIT Trichy"}
    ],
    "experience": [
        {
            "job_title": "Senior ML Engineer",
            "company": "Google India Pvt Ltd",
            "duration": "March 2021 - Present"
        },
        {
            "job_title": "ML Engineer",
            "company": "Flipkart Internet Pvt Ltd",
            "duration": "July 2019 - February 2021"
        }
    ],
    "linkedin": "https://linkedin.com/in/ravikumar",
    "github": "https://github.com/ravikumar"
}


def create_pdf(text: str, output_path: str) -> None:
    """Create a minimal PDF using PyMuPDF."""
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        doc = fitz.open()
        page = doc.new_page()
        # Write text at top-left with wrapping
        rect = fitz.Rect(50, 50, 550, 800)
        page.insert_textbox(rect, text, fontsize=10, fontname="helv")
        doc.save(output_path)
        doc.close()
        print(f"  Created PDF: {output_path}")
    except Exception as e:
        print(f"  WARNING: Could not create PDF ({e}). Creating text fallback.")
        # Write a text file as fallback (will fail PDF parsing tests gracefully)
        with open(output_path + ".txt", "w", encoding="utf-8") as f:
            f.write(text)


def create_docx(text: str, output_path: str) -> None:
    """Create a DOCX using python-docx."""
    try:
        from docx import Document
        doc = Document()
        for line in text.split("\n"):
            doc.add_paragraph(line)
        doc.save(output_path)
        print(f"  Created DOCX: {output_path}")
    except Exception as e:
        print(f"  WARNING: Could not create DOCX ({e}).")


def main():
    print("Creating sample resumes...")

    # Resume 1 — PDF
    create_pdf(RESUME_1_TEXT, os.path.join(SAMPLE_DIR, "resume_1.pdf"))

    # Resume 2 — DOCX
    create_docx(RESUME_2_TEXT, os.path.join(SAMPLE_DIR, "resume_2.docx"))

    # Resume 3 — PDF
    create_pdf(RESUME_3_TEXT, os.path.join(SAMPLE_DIR, "resume_3.pdf"))

    print("Creating sample outputs...")

    with open(os.path.join(OUTPUT_DIR, "resume_1.json"), "w", encoding="utf-8") as f:
        json.dump(RESUME_1_JSON, f, indent=2)
    print("  Created: sample_outputs/resume_1.json")

    with open(os.path.join(OUTPUT_DIR, "resume_2.json"), "w", encoding="utf-8") as f:
        json.dump(RESUME_2_JSON, f, indent=2)
    print("  Created: sample_outputs/resume_2.json")

    with open(os.path.join(OUTPUT_DIR, "resume_3.json"), "w", encoding="utf-8") as f:
        json.dump(RESUME_3_JSON, f, indent=2)
    print("  Created: sample_outputs/resume_3.json")

    print("\nDone! Sample files created successfully.")


if __name__ == "__main__":
    main()
