from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone
from employer.models import JobApplication
from employer.hiring_analytics import hiring_analytics


@login_required(login_url='login-user')
def employer_reports(request):
    if request.user.role != 'employer':
        return HttpResponseForbidden()
    employer = request.user.employer
    hires = list(JobApplication.objects.filter(job__employer=employer, status='hired').select_related('job__employer'))
    hire_from = request.GET.get('hired_from', '').strip()
    hire_to = request.GET.get('hired_to', '').strip()
    hiring_error = ''
    try:
        start = datetime.strptime(hire_from, '%Y-%m-%d').date() if hire_from else None
        end = datetime.strptime(hire_to, '%Y-%m-%d').date() if hire_to else None
        if start and end and start > end:
            raise ValueError()
        if start or end:
            hires = [item for item in hires if item.hired_at and (not start or timezone.localtime(item.hired_at).date() >= start) and (not end or timezone.localtime(item.hired_at).date() <= end)]
    except ValueError:
        hiring_error = 'Enter valid dates with Date From no later than Date To.'
        hires = []
    hiring_stats = hiring_analytics(hires)
    if request.GET.get('export') == 'time-to-hire' and not hiring_error:
        from core.report_pdf import download_report
        return download_report('hired', {'hired':hires, 'hired_from':hire_from, 'hired_to':hire_to,
            'report_date':timezone.localtime().strftime('%b %d, %Y %I:%M %p'), 'hiring_stats':hiring_stats})

    return render(request, 'pages/employer_reports.html', {
        'employer': employer, 'hiring_stats': hiring_stats,
        'hired_from': hire_from, 'hired_to': hire_to, 'hiring_error': hiring_error,
    })