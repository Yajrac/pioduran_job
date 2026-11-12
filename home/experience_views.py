from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from applicant.models import Applicant, WorkExperience
from .experience_forms import WorkExperienceForm


@login_required(login_url="login-user")
def experience(request, pk=None):
    applicant = get_object_or_404(Applicant, user=request.user)
    instance = get_object_or_404(WorkExperience, pk=pk, applicant=applicant) if pk else None
    form = WorkExperienceForm(request.POST if request.method == "POST" else None, instance=instance)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.applicant = applicant
        item.save()
        messages.success(request, "Work experience saved.")
        return redirect("applicant-profile")
    return render(request, "pages/work_experience.html", {"experience_form": form, "experience": instance})


@login_required(login_url="login-user")
@require_POST
def delete_experience(request, pk):
    item = get_object_or_404(WorkExperience, pk=pk, applicant__user=request.user)
    item.delete()
    messages.success(request, "Work experience deleted.")
    return redirect("applicant-profile")
