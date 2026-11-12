from collections import defaultdict


def hiring_analytics(applications):
    """Elapsed days; missing or reversed timestamps are excluded, never zero-filled."""
    values = []
    groups = defaultdict(list)
    for application in applications:
        application.time_to_hire_days = None
        if application.status != 'hired' or not application.hired_at or not application.applied_at:
            continue
        days = (application.hired_at - application.applied_at).total_seconds() / 86400
        if days < 0:
            continue
        application.time_to_hire_days = round(days, 1)
        values.append(days)
        groups[(application.job.employer_id, application.job_id, application.job.employer.company_name, application.job.title)].append(days)
    breakdown = [{'employer':key[2], 'job':key[3], 'count':len(days), 'average_days':round(sum(days) / len(days), 1)} for key, days in groups.items()]
    breakdown.sort(key=lambda item: (item['employer'].casefold(), item['job'].casefold()))
    return {'average_days':round(sum(values) / len(values), 1) if values else None,
            'measured_count':len(values), 'excluded_count':sum(item.status == 'hired' for item in applications) - len(values),
            'breakdown':breakdown}
