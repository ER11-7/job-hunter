from __future__ import annotations

from io import BytesIO

import requests
from docx import Document

from utils.config import ANTHROPIC_API_KEY


def generate_cover_letter(profile_text: str, job: dict) -> str:
    if not ANTHROPIC_API_KEY:
        return (
            f"Dear Hiring Team,\n\n"
            f"I am excited to apply for the {job['title']} role at {job['company']}. "
            f"My background aligns strongly with the experience described in my profile and the role requirements.\n\n"
            f"I would welcome the opportunity to contribute to {job['company']} and discuss how my experience can support the team.\n\n"
            f"Sincerely,\n{profile_text.splitlines()[0] if profile_text.splitlines() else 'Candidate'}"
        )

    prompt = (
        "You are a professional cover letter writer.\n"
        f"Candidate profile: {profile_text}\n"
        f"Job title: {job['title']}\n"
        f"Company: {job['company']}\n"
        f"Job description: {job['description']}\n"
        "Write a concise, compelling cover letter tailored to this specific role. 3 paragraphs max."
    )
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 700,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    parts = payload.get("content", [])
    return "".join(part.get("text", "") for part in parts if part.get("type") == "text").strip()


def cover_letter_docx_bytes(content: str) -> bytes:
    document = Document()
    for paragraph in content.split("\n\n"):
        document.add_paragraph(paragraph.strip())
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()
