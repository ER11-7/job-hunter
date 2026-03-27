from __future__ import annotations

from pathlib import Path

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from models.entities import Job, Profile
from utils.config import EXPORTS_DIR


def _resume_lines(job: Job, profile: Profile) -> list[str]:
    relevant_experience = sorted(
        profile.experience,
        key=lambda item: sum(
            1
            for token in profile.keywords
            if token.lower() in f"{job.title} {job.description} {item}".lower()
        ),
        reverse=True,
    )
    summary = (
        f"{profile.name} is a {', '.join(profile.domains[:2])} professional "
        f"with strengths in {', '.join(profile.skills[:5])}, tailored for {job.title} at {job.company}."
    )
    lines = [profile.name, profile.email, "", "Summary", summary, "", "Skills", ", ".join(profile.skills)]
    lines.extend(["", "Experience"])
    for entry in relevant_experience:
        lines.append(f"{entry['title']} | {entry['company']} | {entry['period']}")
        lines.append(entry["impact"])
    return lines


def generate_resume(job: Job, profile: Profile) -> dict[str, str]:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{profile.id}_{job.id}"
    pdf_path = EXPORTS_DIR / f"{stem}.pdf"
    docx_path = EXPORTS_DIR / f"{stem}.docx"
    lines = _resume_lines(job, profile)

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
