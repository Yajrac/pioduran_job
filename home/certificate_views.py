from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from applicant.models import Applicant, ApplicantCertificate
from employer.models import JobApplication
from .certificate_forms import CertificateForm

from .document_viewer import render_document


@login_required(login_url="login-user")
def certificates(request):
    applicant = get_object_or_404(Applicant, user=request.user)
    form = CertificateForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        if applicant.certificates.count() >= 20:
            form.add_error(None, "You can upload up to 20 certificates. Remove an old certificate first.")
        else:
            certificate = form.save(commit=False)
            certificate.applicant = applicant
            certificate.save()
            messages.success(request, "Certificate uploaded successfully.")
            return redirect("applicant-certificates")
    return render(request, "pages/certificates.html", {"certificate_form": form, "certificates": applicant.certificates.all()})


@login_required(login_url="login-user")
def certificate_file(request, pk):
    certificate = get_object_or_404(ApplicantCertificate.objects.select_related("applicant"), pk=pk)
    owner = certificate.applicant.user_id == request.user.pk
    employer = request.user.role == "employer" and JobApplication.objects.filter(
        applicant=certificate.applicant, job__employer__employer=request.user,
    ).exists()
    if not owner and not employer:
        raise Http404()
    applicant = certificate.applicant
    name = " ".join(filter(None, [applicant.first_name, applicant.last_name]))
    return render_document(request, certificate.file, certificate.title, name,
                           reupload_url=reverse("applicant-certificates") if owner else None)


@login_required(login_url="login-user")
@require_POST
def delete_certificate(request, pk):
    certificate = get_object_or_404(ApplicantCertificate, pk=pk, applicant__user=request.user)
    certificate.file.delete(save=False)
    certificate.delete()
    messages.success(request, "Certificate deleted.")
    return redirect("applicant-certificates")
