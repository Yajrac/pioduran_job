"""Data and geometry for the PESO dashboard charts (server-rendered SVG/CSS).

Colours were checked with the dataviz palette validator:
* trend: applications #2563eb + hires #eb6834 - all checks pass;
* status bars use the fixed status palette in an order where neighbours stay
  apart for colour-blind readers; every part also has a text label, count and
  share next to it, so colour never carries meaning alone.
"""
import math
from datetime import date

from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

from employer.models import Employer, JobApplication, JobPost

GOOD, WARNING, CRITICAL, SERIOUS = "#0ca30c", "#fab219", "#d03b3b", "#ec835a"
APPLICATIONS, HIRES = "#2563eb", "#eb6834"

# SVG canvas for the trend chart (scales with viewBox)
W, H = 640, 240
LEFT, RIGHT, TOP, BOTTOM = 40, 16, 16, 34
MONTHS = 6


def _parts(items):
    """[(label, count, colour)] -> parts with share %; zero parts are kept for the list."""
    total = sum(count for _, count, _ in items)
    return {
        "total": total,
        "parts": [{"label": label, "count": count, "color": color,
                   "share": round(count / total * 100) if total else 0} for label, count, color in items],
    }


def employer_status():
    employers = Employer.objects.all()
    return _parts([
        ("Active", employers.filter(approval_status="approved", is_active=True).count(), GOOD),
        ("Pending approval", employers.filter(approval_status="pending").count(), WARNING),
        ("Suspended", employers.filter(approval_status="approved", is_active=False).count(), CRITICAL),
        ("Rejected", employers.filter(approval_status="rejected").count(), SERIOUS),
    ])


def job_status():
    jobs = JobPost.objects.all()
    return _parts([
        ("Approved", jobs.filter(status="approved").count(), GOOD),
        ("Pending review", jobs.filter(status="pending").count(), WARNING),
        ("Rejected", jobs.filter(status="rejected").count(), CRITICAL),
    ])


def _month_starts(count):
    today = timezone.localdate()
    year, month = today.year, today.month
    months = []
    for _ in range(count):
        months.append(date(year, month, 1))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(months))


def _nice_max(value):
    """Round the axis top up to 1/2/5 x 10^n with 4 ticks."""
    if value <= 0:
        return 4
    step = value / 4
    magnitude = 10 ** math.floor(math.log10(step))
    for factor in (1, 2, 5, 10):
        if step <= factor * magnitude:
            return max(4, int(factor * magnitude * 4))
    return int(value)


def monthly_trend():
    months = _month_starts(MONTHS)
    start = months[0]
    tz = timezone.get_current_timezone()

    def by_month(queryset, field):
        rows = (queryset.filter(**{f"{field}__date__gte": start})
                .annotate(month=TruncMonth(field, tzinfo=tz)).values("month").annotate(n=Count("pk")))
        return {row["month"].date() if hasattr(row["month"], "date") else row["month"]: row["n"] for row in rows}

    applied = by_month(JobApplication.objects.all(), "applied_at")
    hired = by_month(JobApplication.objects.filter(status="hired", hired_at__isnull=False), "hired_at")

    top = _nice_max(max([applied.get(m, 0) for m in months] + [hired.get(m, 0) for m in months] + [0]))
    plot_w, plot_h = W - LEFT - RIGHT, H - TOP - BOTTOM
    band = plot_w / len(months)
    bar_w = min(24, band * 0.42)
    baseline = TOP + plot_h

    def y(value):
        return baseline - value / top * plot_h

    points, line = [], []
    for index, month in enumerate(months):
        center = LEFT + band * index + band / 2
        apps, hires = applied.get(month, 0), hired.get(month, 0)
        bar_h = baseline - y(apps)
        points.append({
            "label": month.strftime("%b"), "full_label": month.strftime("%B %Y"),
            "applications": apps, "hires": hires,
            "cx": round(center, 1), "band_x": round(LEFT + band * index, 1), "band_w": round(band, 1),
            "bar_x": round(center - bar_w / 2, 1), "bar_w": round(bar_w, 1),
            "bar_y": round(y(apps), 1), "bar_h": round(bar_h, 1),
            # rounded data-end, square at the baseline (r = 4, only when tall enough)
            "bar_path": _column_path(center - bar_w / 2, bar_w, y(apps), baseline) if apps else "",
            "hire_y": round(y(hires), 1),
        })
        line.append(f"{round(center, 1)},{round(y(hires), 1)}")

    ticks = [{"value": top * i // 4, "y": round(y(top * i / 4), 1)} for i in range(5)]
    last = points[-1]
    return {
        "width": W, "height": H, "left": LEFT, "right": W - RIGHT, "baseline": baseline,
        "label_y": baseline + 22, "points": points, "ticks": ticks, "line": " ".join(line),
        "total_applications": sum(p["applications"] for p in points),
        "total_hires": sum(p["hires"] for p in points),
        "last": last, "colors": {"applications": APPLICATIONS, "hires": HIRES},
    }


def _column_path(x, width, top_y, baseline):
    height = baseline - top_y
    r = min(4, width / 2, height)
    x2 = x + width
    return (f"M{x:.1f},{baseline:.1f} V{top_y + r:.1f} Q{x:.1f},{top_y:.1f} {x + r:.1f},{top_y:.1f} "
            f"H{x2 - r:.1f} Q{x2:.1f},{top_y:.1f} {x2:.1f},{top_y + r:.1f} V{baseline:.1f} Z")


def dashboard_charts():
    from employer.job_demand import demand_ranking
    ranking = demand_ranking()
    total = sum(row["applications"] for row in ranking)
    for row in ranking:
        row["share"] = round(row["applications"] / total * 100) if total else 0
    return {
        "trend": monthly_trend(),
        "employer_status": employer_status(),
        "job_status": job_status(),
        "top_categories": ranking[:5],
        "category_total": total,
    }
