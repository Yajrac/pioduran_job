from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from employer.models import JobApplication, ApplicantAssessment
from .assessment_forms import AssessmentForm, OutcomeForm


@login_required(login_url='login-user')
def review_applicant(request, pk):
    with transaction.atomic():
        application = get_object_or_404(JobApplication.objects.select_for_update().select_related('job__employer','applicant'), pk=pk, job__employer__employer=request.user)
        assessment = ApplicantAssessment.objects.filter(application=application).first() or ApplicantAssessment(application=application)
        section = request.POST.get('section') if request.method == 'POST' else None
        form = AssessmentForm(request.POST if section == 'assessment' else None, instance=assessment)
        outcome_form = OutcomeForm(request.POST if section == 'outcome' else None, instance=assessment)
        if section == 'assessment' and form.is_valid():
            form.save()
            request.session['applicant_review_saved'] = {'pk':pk, 'message':'Assessment saved successfully.'}
            return redirect('review-applicant', pk=pk)
        if section == 'outcome':
            if application.status != 'hired':
                messages.error(request, 'Employment outcomes are available only for hired applicants.')
            elif outcome_form.is_valid():
                outcome_form.save()
                request.session['applicant_review_saved'] = {'pk':pk, 'message':'Employment outcome saved successfully.'}
                return redirect('review-applicant', pk=pk)
    saved = request.session.pop('applicant_review_saved', None) if request.method == 'GET' else None
    saved_message = saved['message'] if saved and saved.get('pk') == pk else ''
    return render(request, 'pages/review_applicant.html', {'application':application, 'assessment_form':form, 'outcome_form':outcome_form, 'saved_message':saved_message})
