from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from employer.models import JobApplication
from employer.application_status import applicant_application_action


@login_required(login_url='login-user')
@require_POST
def application_action(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, applicant__user=request.user)
    try:
        application = applicant_application_action(application.pk, request.user.pk, request.POST.get('action'))
        labels = {'withdrawn': 'Application withdrawn.', 'declined': 'Job offer declined.', 'hired': 'Job offer accepted. Your status is now Hired.'}
        messages.success(request, labels[application.status])
    except ValueError as error:
        messages.error(request, str(error))
    return redirect('my-applications')
