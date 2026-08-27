from app.services.education_extractor import extract_education

text = """
EDUCATION
B.Tech in Computer Science & Engineering (2023 – Present)
Vel Tech Rangarajan Dr. Sagunthala R&D Institute of Science and Technology | CGPA: 9.2

Intermediate (2021 – 2023)
Narayana Junior College | CGPA: 9.6

10th ICSE (2021)
St. Ann’s School, ICSE | CGPA: 7.8
"""

result = extract_education(text)
for r in result:
    print(r)
