from django.shortcuts import render, redirect, get_object_or_404
from user.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from employer.models import Employer, JobPost, JobApplication
from django.views.decorators.http import require_POST
from applicant.models import Applicant
from django.db.models import Count
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from datetime import datetime
from home.login_limits import limited_login
from functools import wraps
from django.http import HttpResponseForbidden


def is_peso_admin(user):
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)


def admin_required(view):
    """Login required, then PESO admin role required."""
    @login_required(login_url="peso-login")
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not is_peso_admin(request.user):
            return HttpResponseForbidden('PESO administrator access is required.')
        return view(request, *args, **kwargs)
    return wrapped


def keep_alive(request):
    return JsonResponse({
        "status": "ok",
        "service": "Django API",
        "timestamp": timezone.now().isoformat(),
    })

@limited_login
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            # Allow only admin users
            if is_peso_admin(user):
                login(request, user)
                request._public_login_success = True
                if request.headers.get('Accept') == 'application/json':
                    from django.urls import reverse
                    return JsonResponse({'redirect': reverse('peso-dashboard')})
                return redirect("peso-dashboard") 
            else:
                error = 'Invalid username or password.'
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({'error': error, 'clear_fields': ['username', 'password']}, status=400)
                return render(request, 'login.html', {'login_notice': error})
        else:
            exists = User.objects.filter(username=username).exists()
            field = 'password' if exists else 'username'
            error = 'Wrong password.' if exists else 'Username not found.'
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({'field': field, 'error': error}, status=400)
            return render(request, 'login.html', {'login_error_field': field, 'login_error': error})

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect('peso-login')

@admin_required
def peso_dashboard(request):
    from django.db.models import Avg, F
    hiring_summary = JobApplication.objects.filter(
        status='hired', hired_at__gte=F('applied_at'),
    ).aggregate(average=Avg(F('hired_at') - F('applied_at')), measured_count=Count('pk'))
    duration = hiring_summary['average']
    active = Employer.objects.filter(is_active=True).count()
    suspended = Employer.objects.filter(is_active=False).count()
    job_statuses = [('Approved', JobPost.objects.filter(status='approved').count()),
                    ('Pending', JobPost.objects.filter(status='pending').count()),
                    ('Rejected', JobPost.objects.filter(status='rejected').count())]
    maximum = max([count for _, count in job_statuses] + [1])

    context = {
        'average_time_to_hire': round(duration.total_seconds() / 86400, 1) if duration is not None else None,
        'measured_hires': hiring_summary['measured_count'],
        'analytics_active': active,
        'analytics_suspended': suspended,
        'analytics_employers_total': active + suspended,
        'analytics_active_percent': round(active / (active + suspended) * 100, 2) if active + suspended else 0,
        'analytics_job_statuses': [(label, count, round(count / maximum * 100)) for label, count in job_statuses],
        "total_employers": Employer.objects.count(),
        "total_jobs": JobPost.objects.count(),
        "rejected_jobs": job_statuses[2][1],
        "active_applicants": Applicant.objects.count(),
        "open_jobs": JobPost.objects.filter(status="approved").count(),
        "pending_reviews": JobPost.objects.filter(status="pending").count(),

        "recent_employers": Employer.objects.order_by("-created_at")[:3],
        "recent_applicants": Applicant.objects.order_by("-user__date_joined")[:3],
        "recent_jobs": JobPost.objects.select_related("employer").order_by("-created_at")[:4],
    }
    from .dashboard_charts import dashboard_charts
    context["charts"] = dashboard_charts()

    return render(request, "pages/dashboard.html", context)

@admin_required
def employer_list(request):
    employer = Employer.objects.order_by('-created_at', '-pk')
    return render(request, 'pages/employers.html', {"employer": employer})

@admin_required
def employer_detail(request, id):
    employer = get_object_or_404(Employer, id=id)

    return render(request, "pages/employer_detail.html", {
        "employer": employer
    })

@admin_required
@require_POST
def suspend_employer(request, id):
    employer = get_object_or_404(Employer, id=id)

    # =========================================================
    # GET EMAIL FROM RELATED USER ACCOUNT
    # =========================================================

    employer_email = employer.employer.email

    # =========================================================
    # TOGGLE EMPLOYER STATUS
    # =========================================================

    if employer.approval_status != 'approved':
        messages.error(request, 'Review this employer registration before activating the account.')
        return redirect('employer_detail', id=id)
    employer.is_active = not employer.is_active
    employer.save()

    # =========================================================
    # EMPLOYER ACTIVATED
    # =========================================================

    if employer.is_active:

        subject = "Your Employer Account Has Been Activated"

        message = f"""
Hello {employer.company_name},

Good news!

Your employer account has been successfully activated.

You can now log in to your employer account and continue using the PESO system.

Company:
{employer.company_name}

Your account is now active and you may access the employer features available to your account.

Thank you.

PESO Pio Duran
Public Employment Service Office
"""

        if employer_email:

            try:

                send_mail(
                    subject,
                    message,
                    None,
                    [employer_email],
                    fail_silently=False,
                )

                messages.success(
                    request,
                    f"{employer.company_name} has been activated and an activation email has been sent."
                )

            except Exception as e:

                messages.warning(
                    request,
                    f"{employer.company_name} has been activated, but the activation email could not be sent."
                )

        else:

            messages.success(
                request,
                f"{employer.company_name} has been activated."
            )

    # =========================================================
    # EMPLOYER SUSPENDED
    # =========================================================

    else:

        subject = "Your Employer Account Has Been Suspended"

        message = f"""
Hello {employer.company_name},

This is to inform you that your employer account has been suspended.

Company:
{employer.company_name}

Your account is currently inactive and you will not be able to access the employer features of the PESO system while your account is suspended.

If you believe this suspension was made in error or you need assistance, please contact the PESO Pio Duran office.

Thank you.

PESO Pio Duran
Public Employment Service Office
"""

        if employer_email:

            try:

                send_mail(
                    subject,
                    message,
                    None,
                    [employer_email],
                    fail_silently=False,
                )

                messages.warning(
                    request,
                    f"{employer.company_name} has been suspended and a suspension email has been sent."
                )

            except Exception as e:

                messages.warning(
                    request,
                    f"{employer.company_name} has been suspended, but the suspension email could not be sent."
                )

        else:

            messages.warning(
                request,
                f"{employer.company_name} has been suspended."
            )

    return redirect("employer-list")

@admin_required
@require_POST
def delete_employer(request, id):
    employer = get_object_or_404(Employer, id=id)

    company_name = employer.company_name

    # Delete the associated user (this also deletes the Employer
    # because of the OneToOneField with on_delete=models.CASCADE)
    employer.employer.delete()

    messages.success(request, f"{company_name} has been deleted.")

    return redirect("employer-list")

@admin_required
def job_list(request):
    jobs = JobPost.objects.select_related('employer').order_by('-created_at', '-pk')
    return render(request, "pages/job_post.html", {"jobs":jobs})

@admin_required
def view_job(request, id):
    job = get_object_or_404(JobPost, id=id)

    return render(request, "pages/view_job.html", {
        "job": job
    })

@admin_required
def approve_job(request, id):

    job = get_object_or_404(JobPost, id=id)

    # =========================================================
    # ALLOW ONLY ADMINS
    # =========================================================

    if not request.user.is_superuser and request.user.role != "admin":

        messages.error(
            request,
            "You are not authorized to approve job posts."
        )

        return redirect("job-post-list")


    # =========================================================
    # APPROVE JOB
    # =========================================================

    if request.method == "POST" and request.POST.get("decision") == "reject":
        remarks = request.POST.get("remarks", "").strip()
        if not remarks or len(remarks) > 2000:
            messages.error(request, "Give a reason for rejecting this job post (up to 2000 characters).")
            return redirect("approved-job", id=job.id)
        job.status = "rejected"
        job.approved_at = None
        job.admin_remarks = remarks
        job.save(update_fields=["status", "approved_at", "admin_remarks", "updated_at"])
        employer_email = job.employer.employer.email
        if employer_email:
            try:
                send_mail(
                    "Your Job Post Was Not Approved",
                    f"Hello {job.employer.company_name},\n\n"
                    f"Your job post \"{job.title}\" was not approved by PESO Pio Duran.\n\n"
                    f"Remarks:\n{remarks}\n\n"
                    "You may edit the job post and it will be reviewed again.\n\n"
                    "PESO Pio Duran\nPublic Employment Service Office",
                    settings.DEFAULT_FROM_EMAIL,
                    [employer_email],
                    fail_silently=False,
                )
            except Exception:
                messages.warning(request, "The rejection email could not be sent.")
        messages.success(request, f"Job post '{job.title}' has been rejected.")
        return redirect("job-post-list")

    if request.method == "POST":

        job.status = "approved"
        job.approved_at = timezone.now()
        job.admin_remarks = ""
        job.save()


        # =====================================================
        # GET EMPLOYER EMAIL
        # =====================================================

        employer_email = job.employer.employer.email


        # =====================================================
        # SEND APPROVAL EMAIL
        # =====================================================

        if employer_email:

            subject = "Your Job Post Has Been Approved"

            message = f"""
Hello {job.employer.company_name},

Good news!

Your job posting has been approved by the PESO Pio Duran administrator.

JOB DETAILS
----------------------------------------

Job Title:
{job.title}

Job Type:
{job.get_job_type_display()}

Location:
{job.location}

Vacancies:
{job.vacancies}

Salary:
{job.salary_display}

Application Deadline:
{job.deadline.strftime("%B %d, %Y")}

----------------------------------------

Your job post is now approved and published on the PESO system.

Applicants can now view your job posting and submit applications.

Please log in to your employer account to monitor your job posting and applications.

Thank you for using the PESO Pio Duran Job Portal.

PESO Pio Duran
Public Employment Service Office
"""


            try:

                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [employer_email],
                    fail_silently=False,
                )

                messages.success(
                    request,
                    f"Job post '{job.title}' has been approved and published. "
                    f"An approval email has been sent to the employer."
                )

            except Exception:

                messages.warning(
                    request,
                    f"Job post '{job.title}' has been approved and published, "
                    f"but the approval email could not be sent."
                )

        else:

            messages.success(
                request,
                f"Job post '{job.title}' has been approved and published."
            )


        return redirect("job-post-list")


    # =========================================================
    # APPROVAL CONFIRMATION PAGE
    # =========================================================

    return render(
        request,
        "components/approved_job.html",
        {
            "job": job
        }
    )

@admin_required
@require_POST
def delete_job(request, id):

    # =========================================================
    # ADMIN ACCESS ONLY
    # =========================================================

    if not request.user.is_superuser and request.user.role != "admin":

        messages.error(
            request,
            "You are not authorized to delete job posts."
        )

        return redirect("job-post-list")


    # =========================================================
    # GET JOB
    # =========================================================

    job = get_object_or_404(
        JobPost.objects.select_related("employer"),
        id=id
    )


    # =========================================================
    # SAVE INFORMATION BEFORE DELETE
    # =========================================================

    title = job.title

    company = (
        job.employer.company_name
        if job.employer
        else "Unknown Company"
    )


    # =========================================================
    # DELETE
    # =========================================================

    job.delete()


    # =========================================================
    # SUCCESS MESSAGE
    # =========================================================

    messages.success(
        request,
        f'"{title}" from {company} has been deleted successfully.'
    )


    return redirect("job-post-list")

@admin_required
def applicant_list(request):
    applicants = Applicant.objects.select_related("user").all()

    return render(request, "pages/applicant_list.html", {
        "applicants": applicants
    })

def get_date_field(model, candidates):
    """
    Return the first valid date/datetime field path
    available on a model, including supported related fields.
    """
    for path in candidates:
        current_model = model
        valid = True

        for part in path.split("__"):
            try:
                field = current_model._meta.get_field(part)
            except Exception:
                valid = False
                break

            if field.is_relation and field.related_model:
                current_model = field.related_model
            elif part != path.split("__")[-1]:
                valid = False
                break

        if valid:
            return path

    return None


def filter_by_date(queryset, date_field, date_from, date_to):
    """
    Apply an inclusive date range to a queryset.
    The end date includes the entire selected day.
    """
    if not date_field:
        return queryset.none()

    filters = {}

    if date_from:
        filters[f"{date_field}__date__gte"] = date_from

    if date_to:
        filters[f"{date_field}__date__lte"] = date_to

    if filters:
        queryset = queryset.filter(**filters)

    return queryset


@admin_required
def reports(request):
    if request.user.role != 'admin' and not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('PESO administrator access is required.')
    if request.GET.get('section') == 'assessments':
        from employer.models import ApplicantAssessment
        from django.db.models import Avg
        assessments = ApplicantAssessment.objects.all()
        hired = JobApplication.objects.filter(status='hired')
        counts = {value: assessments.filter(application__status='hired', outcome=value).count() for value in ['started', 'passed', 'failed']}
        counts['not_evaluated'] = hired.count() - sum(counts.values())
        summary = assessments.aggregate(skills_average=Avg('skills_score'), interview_average=Avg('interview_score'))
        summary.update(counts)
        summary['assessed_count'] = assessments.exclude(skills_score__isnull=True, interview_score__isnull=True).count()
        from employer.benchmarks import build_benchmarks, benchmark_table, MIN_PASSED
        from .dashboard_charts import _parts, GOOD, WARNING, CRITICAL, APPLICATIONS
        outcomes = _parts([
            ('Passed probation', summary['passed'], GOOD),
            ('Started work', summary['started'], APPLICATIONS),
            ('Not yet evaluated', summary['not_evaluated'], WARNING),
            ('Did not pass', summary['failed'], CRITICAL),
        ])
        benchmarks = benchmark_table(build_benchmarks())
        for row in benchmarks:
            row['progress'] = min(100, round(row['passed'] / MIN_PASSED * 100))
            row['needed'] = max(0, MIN_PASSED - row['passed'])
        return render(request, 'pages/reports.html', {'report_section':'assessments','assessment_summary':summary,
            'hired_total': hired.count(), 'outcomes': outcomes,
            'benchmarks': benchmarks, 'benchmark_min': MIN_PASSED,
            'benchmarks_active': sum(row['ready'] for row in benchmarks)})
    if request.GET.get('section') == 'demand':
        return demand_report(request)
    section = request.GET.get("section", request.GET.get("export", "employers"))
    if section not in {"employers", "applicants", "jobs", "hired"}:
        section = "employers"
    context = {"report_section": section,"report_date": timezone.localtime().strftime("%b %d, %Y %I:%M %p")}
    sources = [
        ("employers", Employer.objects.order_by("-created_at"), "created_at"),
        ("applicants", Applicant.objects.select_related("user").order_by("-user__date_joined"), "user__date_joined"),
        ("jobs", JobPost.objects.select_related("employer").order_by("-created_at"), "created_at"),
        ("hired", JobApplication.objects.filter(status='hired').select_related('applicant', 'job__employer').order_by('-hired_at', '-pk'), 'hired_at'),
    ]
    for key, records, field in sources:
        if key != section:
            continue
        start = request.GET.get(key + "_from", "").strip()
        end = request.GET.get(key + "_to", "").strip()
        context[key + "_from"] = start
        context[key + "_to"] = end
        context[key + "_generated"] = bool(start or end or request.GET.get("generate") == key)
        try:
            date_from = datetime.strptime(start, "%Y-%m-%d").date() if start else None
            date_to = datetime.strptime(end, "%Y-%m-%d").date() if end else None
            if date_from and date_to and date_from > date_to:
                raise ValueError("Invalid range")
            records = filter_by_date(records, field, date_from, date_to)
        except ValueError:
            context[key + "_error"] = "Enter valid dates with Date From no later than Date To."
            records = records.none()
        context[key] = records
        if key == 'hired':
            from employer.hiring_analytics import hiring_analytics
            context[key] = list(records)
            context['hiring_stats'] = hiring_analytics(context[key])
            from .hiring_report import date_presets, hiring_kpis, breakdown_bars
            context['hired_presets'] = date_presets(start, end)
            context['hired_kpis'] = hiring_kpis(context[key])
            context['hired_breakdown'] = breakdown_bars(context['hiring_stats'])
    export = request.GET.get("export")
    if export == section and not context.get(export + "_error"):
        from .report_pdf import download_report
        return download_report(export, context)
    return render(request, "pages/reports.html", context)



def demand_report(request):
    """Recommendation 9.2: job categories ranked by number of applications."""
    from employer.job_demand import demand_ranking, top_jobs, MIN_SAMPLE, TREND_DAYS
    start = request.GET.get("demand_from", "").strip()
    end = request.GET.get("demand_to", "").strip()
    context = {"report_section": "demand", "demand_from": start, "demand_to": end,
               "report_date": timezone.localtime().strftime("%b %d, %Y %I:%M %p"),
               "min_sample": MIN_SAMPLE, "trend_days": TREND_DAYS}
    try:
        date_from = datetime.strptime(start, "%Y-%m-%d").date() if start else None
        date_to = datetime.strptime(end, "%Y-%m-%d").date() if end else None
        if date_from and date_to and date_from > date_to:
            raise ValueError("Invalid range")
    except ValueError:
        context["demand_error"] = "Enter valid dates with Date From no later than Date To."
        context["demand"], context["top_jobs"] = [], []
        return render(request, "pages/reports.html", context)
    context["demand"] = demand_ranking(date_from, date_to)
    context["top_jobs"] = top_jobs(date_from, date_to)
    if request.GET.get("export") == "demand":
        from .report_pdf import download_demand_report
        return download_demand_report(context)
    return render(request, "pages/reports.html", context)


@admin_required
def delete_selected_applicants(request):

    if request.method != "POST":
        return redirect("applicant-list")

    applicant_ids = request.POST.getlist("applicant_ids")

    if not applicant_ids:
        messages.error(
            request,
            "Please select at least one applicant."
        )
        return redirect("applicant-list")

    try:
        with transaction.atomic():

            applicants = Applicant.objects.filter(
                id__in=applicant_ids
            ).select_related("user")

            deleted_count = applicants.count()

            users_to_delete = []

            for applicant in applicants:
                if applicant.user:
                    users_to_delete.append(applicant.user)

            # Delete applicant profiles
            applicants.delete()

            # Delete their associated user accounts
            for user in users_to_delete:
                user.delete()

        messages.success(
            request,
            f"{deleted_count} applicant(s) deleted successfully."
        )

    except Exception as e:

        messages.error(
            request,
            f"Unable to delete applicants: {str(e)}"
        )

    return redirect("applicant-list")


@admin_required
def admin_settings(request):
    """PESO admin account settings: profile details and password change."""
    from django import forms
    from django.contrib.auth import update_session_auth_hash
    from home.password_views import AccountPasswordForm

    class ProfileForm(forms.ModelForm):
        class Meta:
            model = User
            fields = ["first_name", "last_name", "email"]
            labels = {"first_name": "First name", "last_name": "Last name", "email": "Email address"}

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields["email"].required = True
            for field in self.fields.values():
                field.widget.attrs.update({"class": "st-input"})

        def clean_email(self):
            email = self.cleaned_data["email"].strip()
            if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("This email address is already used by another account.")
            return email

    section = request.POST.get("form") if request.method == "POST" else None
    profile_form = ProfileForm(request.POST if section == "profile" else None, instance=request.user)
    password_form = AccountPasswordForm(request.user, request.POST if section == "password" else None)
    for field in password_form.fields.values():
        field.widget.attrs.update({"class": "st-input"})
        field.widget.attrs.pop("autofocus", None)  # don't jump past the profile card

    if section == "profile" and profile_form.is_valid():
        profile_form.save()
        messages.success(request, "Account details updated.")
        return redirect("admin-settings")
    if section == "password" and password_form.is_valid():
        user = password_form.save()
        update_session_auth_hash(request, user)  # stay signed in after the change
        messages.success(request, "Password changed successfully.")
        return redirect("admin-settings")

    return render(request, "pages/admin_settings.html", {
        "profile_form": profile_form, "password_form": password_form, "open_section": section,
    })
