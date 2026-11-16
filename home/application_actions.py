from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from employer.models import JobApplication
from employer.application_status import applicant_application_action
from .sms import SMS_BRAND, send_sms


def notify_employer(application):
    """Text the employer when the applicant answers their job offer.
    A failed SMS is only logged; the applicant's answer still stands."""
    applicant = application.applicant
    name = f"{applicant.first_name} {applicant.last_name}".strip() or applicant.user.username
    title = application.job.title
    if application.status == 'hired':
        text = f"{SMS_BRAND}: {name} ACCEPTED your job offer for {title}. They are now marked as Hired."
    elif application.status == 'declined':
        text = (f"{SMS_BRAND}: {name} DECLINED your job offer for {title}. "
                "The opening is available again for other applicants.")
    else:
        return
    send_sms(application.job.employer.contact_no, text)


@login_required(login_url='login-user')
@require_POST
def application_action(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, applicant__user=request.user)
    try:
        application = applicant_application_action(application.pk, request.user.pk, request.POST.get('action'))
        labels = {'withdrawn': 'Application withdrawn.', 'declined': 'Job offer declined.', 'hired': 'Job offer accepted. Your status is now Hired.'}
        messages.success(request, labels[application.status])
        notify_employer(JobApplication.objects.select_related('job__employer', 'applicant__user').get(pk=application.pk))
    except ValueError as error:
        messages.error(request, str(error))
    return redirect('my-applications')
