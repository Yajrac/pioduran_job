from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from employer.models import JobApplication
from .candidate_ranking import candidate_match, parse_required_skills


@login_required(login_url="login-user")
def employer_applicant_profile(request, pk):
    """The applicant's current profile, for the employer whose job they applied to.

    Looked up through the application, so an employer only ever sees people who
    applied to one of their own jobs; anyone else gets a 404.
    """
    application = get_object_or_404(
        JobApplication.objects.select_related("job__employer", "applicant__user"),
        pk=pk, job__employer__employer=request.user,
    )
    applicant = application.applicant
    skill_tags = parse_required_skills(applicant.skills)
    experiences = list(applicant.work_experiences.order_by("-is_current", "-start_date"))
    match = candidate_match(application.job, skill_tags, experiences)
    return render(request, "pages/employer_applicant_profile.html", {
        "application": application,
        "applicant": applicant,
        "skill_tags": skill_tags,
        "match": match,
        "experiences": experiences,
        "certificates": list(applicant.certificates.all()),
    })
