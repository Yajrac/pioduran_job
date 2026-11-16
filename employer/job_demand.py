"""Recommendation 9.2: job demand ranking and likelihood of success.

* Demand ranking: job categories ranked by how many people applied, with
  hires, success rate and a 30-day trend.
* Likelihood of success: for one application, the share of past finished
  applications in the same category (and, when there is enough data, the
  same match-score band) that ended in a hire.

Everything is a plain historical rate, so it works with small data sets and
is easy to explain. It supports decisions; it never shortlists or rejects.
"""
import re
from collections import Counter, defaultdict
from datetime import timedelta
from types import SimpleNamespace

from django.db.models import Count, Q, Sum
from django.utils import timezone

from home.candidate_ranking import candidate_match
from .job_categories import CATEGORY_LABELS
from .models import JobApplication, JobPost

# Applications whose outcome is known. Withdrawn/declined are the applicant's
# own choice, so they say nothing about success and are left out.
FINISHED = ("hired", "rejected")
MIN_SAMPLE = 5      # fewer finished applications than this -> "not enough data"
TREND_DAYS = 30


def _rate(hires, finished):
    return round(hires / finished * 100, 1) if finished else None


def demand_ranking(date_from=None, date_to=None):
    """Job categories ranked by number of applications (most applied first)."""
    applications = JobApplication.objects.all()
    if date_from:
        applications = applications.filter(applied_at__date__gte=date_from)
    if date_to:
        applications = applications.filter(applied_at__date__lte=date_to)

    rows = {
        item["job__category"]: item
        for item in applications.values("job__category").annotate(
            applications=Count("pk"),
            applicants=Count("applicant", distinct=True),
            hires=Count("pk", filter=Q(status="hired")),
            finished=Count("pk", filter=Q(status__in=FINISHED)),
        )
    }

    now = timezone.now()
    recent = Counter(dict(JobApplication.objects.filter(applied_at__gte=now - timedelta(days=TREND_DAYS))
                          .values_list("job__category").annotate(n=Count("pk"))))
    previous = Counter(dict(JobApplication.objects.filter(
        applied_at__gte=now - timedelta(days=TREND_DAYS * 2),
        applied_at__lt=now - timedelta(days=TREND_DAYS),
    ).values_list("job__category").annotate(n=Count("pk"))))

    open_jobs = {
        item["category"]: item
        for item in JobPost.objects.public().filter(deadline__gte=timezone.localdate())
        .values("category").annotate(jobs=Count("pk"), vacancies=Sum("vacancies"))
    }

    ranking = []
    for category, item in rows.items():
        this_period, last_period = recent[category], previous[category]
        if this_period > last_period:
            trend = "up"
        elif this_period < last_period:
            trend = "down"
        else:
            trend = "same"
        ranking.append({
            "category": category,
            "label": CATEGORY_LABELS.get(category, "Other"),
            "applications": item["applications"],
            "applicants": item["applicants"],
            "hires": item["hires"],
            "finished": item["finished"],
            "success_rate": _rate(item["hires"], item["finished"]),
            "recent": this_period,
            "previous": last_period,
            "trend": trend,
            "open_jobs": open_jobs.get(category, {}).get("jobs", 0),
            "open_vacancies": open_jobs.get(category, {}).get("vacancies") or 0,
        })
    ranking.sort(key=lambda row: (-row["applications"], -row["hires"], row["label"]))
    top = ranking[0]["applications"] if ranking else 1
    for rank, row in enumerate(ranking, 1):
        row["rank"] = rank
        row["percent"] = round(row["applications"] / top * 100)
    return ranking


def top_jobs(date_from=None, date_to=None, limit=10):
    """Individual job posts with the most applications."""
    filters = Q()
    if date_from:
        filters &= Q(applications__applied_at__date__gte=date_from)
    if date_to:
        filters &= Q(applications__applied_at__date__lte=date_to)
    jobs = (JobPost.objects.select_related("employer")
            .annotate(application_count=Count("applications", filter=filters))
            .filter(application_count__gt=0)
            .order_by("-application_count", "-created_at")[:limit])
    return list(jobs)


# ---------------------------------------------------------------- likelihood

def match_band(score):
    if score is None:
        return None
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


BAND_LABELS = {"high": "high match (70%+)", "medium": "medium match (40-69%)", "low": "low match (below 40%)"}


def _snapshot_score(application):
    """Match score as it was when the person applied (from the snapshot)."""
    snapshot = application.application_snapshot or {}
    if not snapshot.get("required_skills"):
        return None
    job = SimpleNamespace(
        title=snapshot.get("job_title", ""), description="", responsibilities="",
        qualifications=snapshot.get("qualifications", ""), required_skills=snapshot["required_skills"],
        experience_required=snapshot.get("experience_required", False),
    )
    experiences = [SimpleNamespace(**item) for item in snapshot.get("experience", [])]
    skills = [s.strip() for s in re.split(r"[,;\n|]+", snapshot.get("skills", "")) if s.strip()]
    return candidate_match(job, skills, experiences)["score"]


def success_history():
    """Counts of finished applications by category and by (category, band)."""
    by_category = defaultdict(lambda: [0, 0])          # category -> [hires, finished]
    by_band = defaultdict(lambda: [0, 0])              # (category, band) -> [hires, finished]
    finished = JobApplication.objects.filter(status__in=FINISHED).select_related("job")
    for application in finished:
        hired = int(application.status == "hired")
        category = application.job.category
        by_category[category][0] += hired
        by_category[category][1] += 1
        band = match_band(_snapshot_score(application))
        if band:
            by_band[(category, band)][0] += hired
            by_band[(category, band)][1] += 1
    return {"category": by_category, "band": by_band, "finished_ids": set(finished.values_list("pk", flat=True))}


def likelihood(application, history, match_score=None):
    """Historical chance of being hired for an application, with its basis.

    Returns None when there is not enough history to say anything useful.
    """
    category = application.job.category
    band = match_band(match_score)
    own = application.pk in history["finished_ids"]
    own_hired = int(application.status == "hired")

    def counts(source, key):
        hires, finished = source.get(key, (0, 0))
        if own:  # never let an application predict itself
            hires, finished = hires - own_hired, finished - 1
        return hires, finished

    label = CATEGORY_LABELS.get(category, "Other")
    if band:
        hires, finished = counts(history["band"], (category, band))
        if finished >= MIN_SAMPLE:
            return {"percent": _rate(hires, finished), "sample": finished,
                    "basis": f"{finished} past {label} applicants with {BAND_LABELS[band]}"}
    hires, finished = counts(history["category"], category)
    if finished >= MIN_SAMPLE:
        return {"percent": _rate(hires, finished), "sample": finished,
                "basis": f"{finished} past {label} applicants"}
    return None
