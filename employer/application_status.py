from django.db import transaction
from django.db.models import F
from .models import JobPost, JobApplication
from django.utils import timezone


def change_application_status(application_id, employer_id, new_status):
    """Update status and available slots together; repeated status is a no-op."""
    allowed = {'pending', 'reviewing', 'shortlisted', 'offered', 'accepted', 'rejected'}
    if new_status not in allowed:
        raise ValueError('Invalid application status.')
    with transaction.atomic():
        application = JobApplication.objects.select_for_update().get(
            pk=application_id, job__employer_id=employer_id,
        )
        if application.status == new_status:
            return False
        if application.status in {'withdrawn', 'declined', 'hired'}:
            raise ValueError('This application is closed and cannot be changed.')
        reserved_statuses = {'offered', 'accepted', 'hired'}
        if new_status in reserved_statuses and application.status not in reserved_statuses:
            reserved = JobPost.objects.filter(pk=application.job_id, vacancies__gt=0).update(vacancies=F('vacancies') - 1)
            if not reserved:
                raise ValueError('No remaining slots. This applicant cannot be accepted.')
        elif application.status in reserved_statuses and new_status not in reserved_statuses:
            JobPost.objects.filter(pk=application.job_id).update(vacancies=F('vacancies') + 1)
        application.status = new_status
        application.save(update_fields=['status'])
        return True


def applicant_application_action(application_id, user_id, action):
    with transaction.atomic():
        application = JobApplication.objects.select_for_update().get(pk=application_id, applicant__user_id=user_id)
        if action == 'withdraw' and application.status in {'pending', 'reviewing', 'shortlisted'}:
            application.status = 'withdrawn'
        elif action in {'accept', 'decline'} and application.status == 'offered':
            application.status = 'hired' if action == 'accept' else 'declined'
            if action == 'accept':
                application.hired_at = timezone.now()
            else:
                JobPost.objects.filter(pk=application.job_id).update(vacancies=F('vacancies') + 1)
        else:
            raise ValueError('This action is no longer available. Refresh your applications.')
        application.save(update_fields=['status', 'hired_at'])
        return application
