from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone
from employer.models import JobApplication, JobPost
from employer.hiring_analytics import hiring_analytics

IN_PROGRESS = ('pending', 'reviewing', 'shortlisted', 'accepted', 'offered')


def _in_range(field, start, end):
    """Q filter for a datetime field falling on local dates start..end (either may be None)."""
    q = Q()
    if start:
        q &= Q(**{f'{field}__date__gte': start})
    if end:
        q &= Q(**{f'{field}__date__lte': end})
    return q


def build_employer_report(employer, start=None, end=None):
    """Counts of job posts, applications, rejections and hires for one employer.

    Job posts are counted by date posted, applications and rejections by
    application date (a rejection has no date of its own), hires by hiring date.
    """
    applied = Q(applications__isnull=False) & _in_range('applications__applied_at', start, end)
    hired = Q(applications__status='hired') & _in_range('applications__hired_at', start, end)
    jobs = (
        JobPost.objects.filter(employer=employer)
        .annotate(
            n_applications=Count('applications', filter=applied, distinct=True),
            n_in_progress=Count('applications', filter=applied & Q(applications__status__in=IN_PROGRESS), distinct=True),
            n_rejected=Count('applications', filter=applied & Q(applications__status='rejected'), distinct=True),
            n_hired=Count('applications', filter=hired, distinct=True),
        )
        .order_by('-created_at')
    )
    posted = set(JobPost.objects.filter(Q(employer=employer) & _in_range('created_at', start, end)).values_list('pk', flat=True))
    rows = [job for job in jobs if job.pk in posted or job.n_applications or job.n_hired]
    return {
        'rows': rows,
        'totals': {
            'job_posts': len(posted),
            'applications': sum(job.n_applications for job in rows),
            'in_progress': sum(job.n_in_progress for job in rows),
            'rejected': sum(job.n_rejected for job in rows),
            'hired': sum(job.n_hired for job in rows),
        },
    }


@login_required(login_url='login-user')
def employer_reports(request):
    if request.user.role != 'employer':
        return HttpResponseForbidden()
    employer = request.user.employer
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    date_error = ''
    start = end = None
    try:
        start = datetime.strptime(date_from, '%Y-%m-%d').date() if date_from else None
        end = datetime.strptime(date_to, '%Y-%m-%d').date() if date_to else None
        if start and end and start > end:
            raise ValueError()
    except ValueError:
        date_error = 'Enter valid dates with Date From no later than Date To.'
        start = end = None

    report = build_employer_report(employer, start, end)
    hires = list(
        JobApplication.objects.filter(Q(job__employer=employer, status='hired') & _in_range('hired_at', start, end))
        .select_related('job__employer', 'applicant')
    )
    if date_error:
        report = {'rows': [], 'totals': dict.fromkeys(['job_posts', 'applications', 'in_progress', 'rejected', 'hired'], 0)}
        hires = []
    hiring_stats = hiring_analytics(hires)

    if request.GET.get('export') == 'pdf' and not date_error:
        from core.report_pdf import download_employer_report
        return download_employer_report({
            'employer': employer, 'report': report, 'hiring_stats': hiring_stats,
            'date_from': date_from, 'date_to': date_to,
            'report_date': timezone.localtime().strftime('%b %d, %Y %I:%M %p'),
        })

    return render(request, 'pages/employer_reports.html', {
        'employer': employer, 'report': report, 'hiring_stats': hiring_stats,
        'date_from': date_from, 'date_to': date_to, 'date_error': date_error,
    })
