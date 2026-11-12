import re

# Suggestions are reviewable keywords, not verified qualifications.
SKILLS = {
    'Customer Service': ['customer service', 'customer assistance', 'customer support'],
    'Sales': ['sales', 'selling'], 'Cashiering': ['cashiering', 'cashier', 'point of sale', 'pos system'],
    'Inventory Management': ['inventory', 'stock management', 'stock control'],
    'Cooking': ['cooking', 'cook', 'food preparation'], 'Food Safety': ['food safety', 'food handling'],
    'Cleaning': ['cleaning', 'housekeeping', 'sanitation'], 'Driving': ['driving', 'driver'],
    'Delivery': ['delivery', 'deliveries'], 'Communication': ['communication', 'communicate'],
    'Teamwork': ['teamwork', 'team player'], 'Computer Literacy': ['computer literacy', 'computer skills'],
    'Microsoft Excel': ['microsoft excel', 'excel'], 'Microsoft Word': ['microsoft word'],
    'Data Entry': ['data entry'], 'Bookkeeping': ['bookkeeping'], 'Accounting': ['accounting'],
    'Welding': ['welding', 'welder'], 'Electrical Work': ['electrician', 'electrical installation'],
    'Plumbing': ['plumbing', 'plumber'], 'Carpentry': ['carpentry', 'carpenter'],
    'Python': ['python'], 'JavaScript': ['javascript'], 'HTML': ['html'], 'CSS': ['css'],
    'SQL': ['sql'], 'Graphic Design': ['graphic design'], 'Time Management': ['time management'],
}


def contains(text, phrase):
    return bool(re.search(r'(?<!\w)' + re.escape(phrase.casefold()) + r'(?!\w)', text.casefold()))


def detect_skills(text):
    return [label for label, aliases in SKILLS.items() if any(contains(text, alias) for alias in aliases)]


def skill_in_text(skill, text):
    aliases = SKILLS.get(skill, next((values for key, values in SKILLS.items() if key.casefold() == skill.casefold()), [skill]))
    return any(contains(text, alias) for alias in aliases)


def experience_matches(job, experiences):
    job_text = ' '.join([job.title, job.description, job.qualifications, job.responsibilities])
    job_text += ' ' + getattr(job, 'required_skills', '')
    job_skills = set(detect_skills(job_text))
    matches = []
    for item in experiences:
        text = item.job_title + ' ' + item.description
        shared = job_skills.intersection(detect_skills(text))
        same_role = contains(job.title, item.job_title) or contains(item.job_title, job.title)
        if shared or same_role:
            matches.append(f'{item.job_title} at {item.company}')
    return matches
