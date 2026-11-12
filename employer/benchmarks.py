"""Recommendation 9.4: match candidate profiles with performance benchmarks.

A benchmark is the profile of people who *passed probation* in a job
category: their average skills-test and interview scores (recorded by
employers), their average match score when they applied, the skills most of
them had, and how many had work experience.

Each applicant is compared with the benchmark of the job's category and
gets Above / Near / Below, with the reasons shown. It is decision support
only and needs at least MIN_PASSED passed employees in the category.
"""
import re
from collections import Counter, defaultdict

from home.skill_extraction import skill_in_text
from .job_categories import CATEGORY_LABELS
from .job_demand import _snapshot_score
from .models import ApplicantAssessment

MIN_PASSED = 3          # passed employees needed before a benchmark is shown
COMMON_SKILL_SHARE = 50  # % of passed employees who must share a skill
SCORE_TOLERANCE = 0.5    # skills/interview scores are 0-5
MATCH_TOLERANCE = 10     # match score is 0-100

STATUS_POINTS = {"above": 1.0, "near": 0.5, "below": 0.0}
OVERALL_LABELS = {"above": "Above benchmark", "near": "Near benchmark", "below": "Below benchmark"}


def _avg(values):
    return round(sum(values) / len(values), 1) if values else None


def _skills(text):
    return [s.strip() for s in re.split(r"[,;\n|]+", text or "") if s.strip()]


def build_benchmarks():
    """Benchmarks for every category with recorded probation results."""
    groups = defaultdict(lambda: {"passed": [], "failed": 0})
    records = (ApplicantAssessment.objects
               .filter(application__status="hired", outcome__in=["passed", "failed"])
               .select_related("application__job"))
    for assessment in records:
        group = groups[assessment.application.job.category]
        if assessment.outcome == "passed":
            group["passed"].append(assessment)
        else:
            group["failed"] += 1

    benchmarks = {}
    for category, group in groups.items():
        passed = group["passed"]
        skill_counts, skill_names, with_experience = Counter(), {}, 0
        for assessment in passed:
            snapshot = assessment.application.application_snapshot or {}
            for skill in {s.casefold(): s for s in _skills(snapshot.get("skills", ""))}.values():
                skill_counts[skill.casefold()] += 1
                skill_names.setdefault(skill.casefold(), skill)
            with_experience += bool(snapshot.get("experience"))
        total = len(passed)
        common = [(skill_names[key], round(count / total * 100)) for key, count in skill_counts.most_common()
                  if total and count / total * 100 >= COMMON_SKILL_SHARE][:6]
        finished = total + group["failed"]
        benchmarks[category] = {
            "category": category,
            "label": CATEGORY_LABELS.get(category, "Other"),
            "passed": total,
            "failed": group["failed"],
            "pass_rate": round(total / finished * 100, 1) if finished else None,
            "skills_average": _avg([a.skills_score for a in passed if a.skills_score is not None]),
            "interview_average": _avg([a.interview_score for a in passed if a.interview_score is not None]),
            "match_average": _avg([s for s in (_snapshot_score(a.application) for a in passed) if s is not None]),
            "common_skills": common,
            "experience_share": round(with_experience / total * 100) if total else None,
            "ready": total >= MIN_PASSED,
        }
    return benchmarks


def benchmark_table(benchmarks):
    """Rows for the report, most passed employees first."""
    return sorted(benchmarks.values(), key=lambda row: (-row["passed"], row["label"]))


def _score_status(value, average, tolerance):
    if value >= average + tolerance:
        return "above"
    if value >= average - tolerance:
        return "near"
    return "below"


def compare(application, benchmarks, match_score, confirmed_skills, experiences):
    """Compare one application with its category benchmark (or None)."""
    benchmark = benchmarks.get(application.job.category)
    if not benchmark or not benchmark["ready"]:
        return None
    checks = []

    if match_score is not None and benchmark["match_average"] is not None:
        checks.append({"name": "Skill match", "status": _score_status(match_score, benchmark["match_average"], MATCH_TOLERANCE),
                       "detail": f"{match_score:g}/100 vs. {benchmark['match_average']:g} average"})

    if benchmark["common_skills"]:
        names = [name for name, _ in benchmark["common_skills"]]
        has = [name for name in names if any(skill_in_text(name, own) or skill_in_text(own, name) for own in confirmed_skills)]
        share = len(has) / len(names)
        status = "above" if share >= 0.67 else "near" if share >= 0.34 else "below"
        checks.append({"name": "Common skills of passers", "status": status,
                       "detail": f"has {len(has)} of {len(names)}: {', '.join(names)}"})

    if benchmark["experience_share"] is not None and benchmark["experience_share"] >= 50:
        has_experience = bool(experiences)
        checks.append({"name": "Work experience", "status": "above" if has_experience else "below",
                       "detail": f"{'has' if has_experience else 'no'} experience; {benchmark['experience_share']}% of passers had experience"})

    assessment = getattr(application, "assessment", None)
    for field, label, average in [("skills_score", "Skills test", benchmark["skills_average"]),
                                  ("interview_score", "Interview", benchmark["interview_average"])]:
        value = getattr(assessment, field, None) if assessment else None
        if value is not None and average is not None:
            checks.append({"name": label, "status": _score_status(value, average, SCORE_TOLERANCE),
                           "detail": f"{value}/5 vs. {average:g} average"})

    if not checks:
        return None
    points = sum(STATUS_POINTS[check["status"]] for check in checks) / len(checks)
    overall = "above" if points >= 0.75 else "near" if points >= 0.4 else "below"
    return {"overall": overall, "label": OVERALL_LABELS[overall], "checks": checks,
            "basis": f"{benchmark['passed']} employees who passed probation in {benchmark['label']}"}
