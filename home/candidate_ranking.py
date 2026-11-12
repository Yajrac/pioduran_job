import re
from .skill_extraction import skill_in_text, experience_matches


def parse_required_skills(value):
    skills = {}
    for item in re.split(r'[,;\n|]+', value or ''):
        item = re.sub(r'\s+', ' ', item).strip()
        if item:
            skills.setdefault(item.casefold(), item)
    return list(skills.values())


def ranking_requirements_error(value):
    skills = parse_required_skills(value)
    if len(skills) > 20 or any(len(skill) > 60 or not any(char.isalpha() for char in skill) for skill in skills):
        return 'Enter up to 20 required skills, each containing a letter and at most 60 characters.'
    return ''


def candidate_match(job, confirmed_skills, experiences):
    required = parse_required_skills(job.required_skills)
    if not required:
        return {'score':None, 'matched':[], 'missing':[], 'required':[], 'experience':[], 'skills_points':0, 'experience_points':0}
    matched = [skill for skill in required if any(skill_in_text(skill, confirmed) for confirmed in confirmed_skills)]
    missing = [skill for skill in required if skill not in matched]
    relevant = experience_matches(job, experiences)
    weight = 80 if job.experience_required else 100
    skills_points = len(matched) / len(required) * weight
    experience_points = 20 if job.experience_required and relevant else 0
    return {'score':round(skills_points + experience_points, 1), 'matched':matched, 'missing':missing,
            'required':required, 'experience':relevant, 'skills_points':round(skills_points, 1), 'experience_points':experience_points}
