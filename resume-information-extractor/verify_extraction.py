from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

samples = [
    ("Resume 1 - Software Dev PDF", "sample_resumes/resume_1.pdf", "application/pdf"),
    ("Resume 2 - Student DOCX", "sample_resumes/resume_2.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ("Resume 3 - ML Engineer PDF", "sample_resumes/resume_3.pdf", "application/pdf"),
]

for label, path, mime in samples:
    filename = path.split("/")[-1]
    with open(path, "rb") as f:
        resp = client.post("/api/v1/resume/extract", files={"file": (filename, f, mime)})
    d = resp.json()
    print(f"=== {label} (HTTP {resp.status_code}) ===")
    print(f"  name:     {d['name']}")
    print(f"  email:    {d['email']}")
    print(f"  phone:    {d['phone']}")
    print(f"  linkedin: {d['linkedin']}")
    print(f"  github:   {d['github']}")
    print(f"  skills({len(d['skills'])}): {d['skills'][:6]}")
    print(f"  education: {d['education']}")
    exp = [(e['job_title'], e['company'], e['duration']) for e in d['experience']]
    print(f"  experience: {exp}")
    print()
