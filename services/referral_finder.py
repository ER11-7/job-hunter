from __future__ import annotations

from models.entities import ReferralContact


CONTACTS = {
    "default": [
        ("Aisha Mehta", "Senior Recruiter"),
        ("Rohan Khanna", "ESG Team Lead"),
        ("Neha Sharma", "Hiring Manager"),
    ]
}


def find_referral_contacts(company: str) -> list[ReferralContact]:
    contacts = CONTACTS.get(company.lower(), CONTACTS["default"])
    normalized = company.lower().replace(" ", "-")
    return [
        ReferralContact(
            name=name,
            role=role,
            company=company,
            linkedin_url=f"https://www.linkedin.com/in/{normalized}-{name.lower().replace(' ', '-')}",
        )
        for name, role in contacts
    ]


def build_referral_message(contact_name: str, role: str, company: str) -> str:
    return (
        f"Hi {contact_name}, I came across the {role} opportunity at {company}. "
        "My background spans ESG, climate, and energy analytics, and I would value a quick conversation "
        "or any guidance on the team."
    )
