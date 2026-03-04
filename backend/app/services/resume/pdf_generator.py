from pathlib import Path
from typing import Dict, Any
from app.core.config import STORAGE_DIR
from app.core.logging import logger


class ATSDocumentGenerator:
    def generate_html_resume(self, ast: Dict[str, Any]) -> str:
        """Generate clean, ATS-compliant semantic HTML resume."""
        contact = ast.get("contact", {})
        summary = ast.get("summary", "")
        skills = ast.get("skills", {})
        experience = ast.get("experience", [])
        education = ast.get("education", [])
        projects = ast.get("projects", [])
        certifications = ast.get("certifications", [])

        # Contact line
        contact_parts = []
        if contact.get("email"):
            contact_parts.append(contact['email'])
        if contact.get("phone"):
            contact_parts.append(contact['phone'])
        if contact.get("location"):
            contact_parts.append(contact['location'])
        if contact.get("linkedin"):
            contact_parts.append(f"<a href='{contact['linkedin']}'>LinkedIn</a>")
        if contact.get("github"):
            contact_parts.append(f"<a href='{contact['github']}'>GitHub</a>")

        contact_line = " | ".join(contact_parts)

        # Experience HTML
        exp_html = []
        for exp in experience:
            company = exp.get("company", "")
            title = exp.get("title", "")
            dates = f"{exp.get('start_date', '')} - {exp.get('end_date', 'Present')}" if exp.get('start_date') else ""
            bullets = "".join([f"<li>{b}</li>" for b in exp.get("bullet_points", [])])

            exp_html.append(f"""
            <div class="item">
                <div class="item-header">
                    <strong>{title}</strong> — <span>{company}</span>
                    <span class="date">{dates}</span>
                </div>
                <ul>{bullets}</ul>
            </div>
            """)

        # Skills HTML
        skills_html = []
        for cat, s_list in skills.items():
            if s_list:
                skills_html.append(f"<p><strong>{cat}:</strong> {', '.join(s_list)}</p>")

        # Education HTML
        edu_html = []
        for edu in education:
            edu_html.append(f"""
            <div class="item">
                <div class="item-header">
                    <strong>{edu.get('degree')}</strong> in {edu.get('field_of_study', '')}
                    <span class="date">{edu.get('graduation_year', '')}</span>
                </div>
                <p>{edu.get('institution')}</p>
            </div>
            """)

        # Projects HTML
        proj_html = []
        for p in projects:
            p_bullets = "".join([f"<li>{b}</li>" for b in p.get("bullet_points", [])])
            proj_html.append(f"""
            <div class="item">
                <div class="item-header">
                    <strong>{p.get('name')}</strong>
                </div>
                <p>{p.get('description', '')}</p>
                <ul>{p_bullets}</ul>
            </div>
            """)

        # Certifications HTML
        cert_html = "".join([f"<li>{c}</li>" for c in certifications]) if certifications else ""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{contact.get('full_name', 'Resume')}</title>
    <style>
        body {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: 10.5pt;
            line-height: 1.4;
            color: #111827;
            max-width: 800px;
            margin: 20px auto;
            padding: 20px;
        }}
        h1 {{
            font-size: 18pt;
            margin: 0 0 4px 0;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #111827;
        }}
        .contact-info {{
            text-align: center;
            font-size: 9.5pt;
            margin-bottom: 16px;
            color: #4b5563;
        }}
        .contact-info a {{
            color: #2563eb;
            text-decoration: none;
        }}
        h2 {{
            font-size: 12pt;
            text-transform: uppercase;
            border-bottom: 1.5px solid #1f2937;
            padding-bottom: 2px;
            margin: 14px 0 8px 0;
            color: #1f2937;
            letter-spacing: 0.5px;
        }}
        .item {{
            margin-bottom: 10px;
        }}
        .item-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 2px;
        }}
        .date {{
            font-size: 9.5pt;
            color: #4b5563;
        }}
        ul {{
            margin: 4px 0 8px 18px;
            padding: 0;
        }}
        li {{
            margin-bottom: 3px;
        }}
        p {{
            margin: 3px 0;
        }}
    </style>
</head>
<body>
    <h1>{contact.get('full_name', 'Candidate Name')}</h1>
    <div class="contact-info">{contact_line}</div>

    {'<h2>Professional Summary</h2><p>' + summary + '</p>' if summary else ''}

    <h2>Technical Skills</h2>
    {''.join(skills_html)}

    <h2>Professional Experience</h2>
    {''.join(exp_html)}

    {'<h2>Key Projects</h2>' + ''.join(proj_html) if projects else ''}

    <h2>Education</h2>
    {''.join(edu_html)}

    {'<h2>Certifications</h2><ul>' + cert_html + '</ul>' if cert_html else ''}
</body>
</html>"""
        return html

    def save_html_and_pdf(self, ast: Dict[str, Any], output_id: str) -> str:
        """Save HTML and return file path."""
        html_content = self.generate_html_resume(ast)
        file_path = STORAGE_DIR / f"{output_id}_tailored_resume.html"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return str(file_path)


doc_generator = ATSDocumentGenerator()
