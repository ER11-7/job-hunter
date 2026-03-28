from __future__ import annotations

from pathlib import Path

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from models.entities import Job
from services.matching_engine import extract_profile_context
from utils.config import EXPORTS_DIR


def _resume_lines(job: Job, profile_text: str) -> list[str]:
    profile = extract_profile_context(profile_text)
    relevant_lines = [line.strip() for line in profile_text.splitlines() if line.strip()]
    summary = (
        f"{profile['name']} is a {', '.join(profile['domains'][:2])} professional "
        f"with strengths in {', '.join(profile['skills'][:5])}, tailored for {job.title} at {job.company}."
    )
    lines = [profile["name"], "", "Summary", summary, "", "Skills", ", ".join(profile["skills"])]
    lines.extend(["", "Experience"])
    for line in relevant_lines[:12]:
        lines.append(line)
    return lines


def generate_resume(job: Job, profile_text: str) -> dict[str, str]:
    profile = extract_profile_context(profile_text)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"uploaded_profile_{job.id}"
    pdf_path = EXPORTS_DIR / f"{stem}.pdf"
    docx_path = EXPORTS_DIR / f"{stem}.docx"
    lines = _resume_lines(job, profile_text)

    pdf = canvas.Canvas(str(pdf_path), pagesize=A4)
    y = 800
    for line in lines:
        pdf.drawString(50, y, line[:110])
        y -= 18
        if y < 60:
            pdf.showPage()
            y = 800
    pdf.save()

    document = Document()
    for line in lines:
        document.add_paragraph(line)
    document.save(docx_path)

    return {"pdf": str(pdf_path), "docx": str(docx_path)}
