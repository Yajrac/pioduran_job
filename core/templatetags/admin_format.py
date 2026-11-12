from django import template

register = template.Library()


@register.filter
def days_label(value):
    """0.4 -> 'Same day', 1 -> '1 day', 6.5 -> '6.5 days', None -> 'Not available'."""
    if value is None or value == "":
        return "Not available"
    value = float(value)
    if value < 1:
        return "Same day"
    rounded = round(value, 1)
    text = f"{rounded:g}"
    return f"{text} day" if rounded == 1 else f"{text} days"


@register.filter
def initials(applicant):
    first = (getattr(applicant, "first_name", "") or "").strip()[:1]
    last = (getattr(applicant, "last_name", "") or "").strip()[:1]
    return (first + last).upper() or "?"


@register.filter
def posted_ago(value):
    """Short relative date for listings: 'today', '3 days ago', '2 weeks ago'."""
    from django.utils import timezone
    if not value:
        return ""
    days = (timezone.localdate() - timezone.localtime(value).date()).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days} days ago"
    if days < 30:
        weeks = days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    if days < 365:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    years = days // 365
    return f"{years} year{'s' if years > 1 else ''} ago"
