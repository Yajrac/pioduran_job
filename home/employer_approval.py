from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from employer.models import Employer
from django.db import transaction


@login_required(login_url='login-user')
def approval_status(request):
    employer = get_object_or_404(Employer, employer=request.user)
    return render(request, 'pages/employer_approval_status.html', {'employer':employer})


@login_required(login_url='peso-login')
@require_POST
@transaction.atomic
def review_employer(request, pk):
    if request.user.role != 'admin' and not request.user.is_superuser:
        return HttpResponseForbidden('Only PESO administrators can review employers.')
    employer = get_object_or_404(Employer.objects.select_for_update(), pk=pk)
    if employer.approval_status != 'pending':
        messages.info(request, 'Registration review is already complete. Use Suspend/Activate to manage approved accounts.')
        return redirect('employer_detail', id=pk)
    decision = request.POST.get('decision')
    remarks = request.POST.get('remarks', '').strip()
    if decision not in {'approved', 'rejected'} or len(remarks) > 2000:
        messages.error(request, 'Choose a valid decision and use at most 2000 characters for remarks.')
    elif decision == 'rejected' and not remarks:
        messages.error(request, 'Provide a reason for rejecting the employer.')
    else:
        employer.approval_status = decision
        employer.approval_remarks = remarks
        employer.reviewed_at = timezone.now()
        employer.is_active = decision == 'approved'
        employer.save(update_fields=['approval_status','approval_remarks','reviewed_at','is_active'])
        messages.success(request, f'Employer {decision}.')
    return redirect('employer_detail', id=pk)


class EmployerApprovalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view, args, kwargs):
        protected = {'employer-dashboard','job-list','job-post','update-job','employer-delete-job','applicants','update-applicant-status','review-applicant'}
        if request.resolver_match.url_name not in protected:
            return None
        if not request.user.is_authenticated:
            return None
        if request.user.role != 'employer':
            return HttpResponseForbidden('An employer account is required.')
        employer = Employer.objects.filter(employer=request.user).first()
        if not employer or employer.approval_status != 'approved' or not employer.is_active:
            return redirect('employer-approval-status')
