from django.urls import path
from . import views
from . import certificate_views
from .application_actions import application_action
from . import experience_views
from .profile_photo import profile_photo
from .skill_review import review_resume_skills
from .employer_approval import approval_status
from .assessment_views import review_applicant
from .applicant_profile_views import employer_applicant_profile
from .permit_views import business_permit
from .password_views import AccountPasswordChangeView
from .report_views import employer_reports
from . import document_views
from . import password_reset

urlpatterns = [
    path('forgot-password/', password_reset.forgot_password, name='forgot-password'),
    path('forgot-password/verify/', password_reset.verify_code, name='forgot-password-verify'),
    path('forgot-password/resend/', password_reset.resend_code, name='forgot-password-resend'),
    path('forgot-password/account/', password_reset.choose_account, name='forgot-password-account'),
    path('forgot-password/new/', password_reset.new_password, name='forgot-password-new'),
    path('applicant/documents/<str:kind>/', document_views.my_document, name='my-document'),
    path('applications/<int:pk>/documents/<str:kind>/', document_views.application_document, name='application-document'),
    path('employer/reports/', employer_reports, name='employer-reports'),
    path('account/change-password/', AccountPasswordChangeView.as_view(), name='change-password'),
    path('account/password-changed/', AccountPasswordChangeView.as_view(extra_context={'password_changed': True}), name='change-password-done'),
    path('employer/applications/<int:pk>/review/', review_applicant, name='review-applicant'),
    path('employer/applications/<int:pk>/profile/', employer_applicant_profile, name='employer-applicant-profile'),
    path('employers/<int:pk>/business-permit/', business_permit, name='business-permit'),
    path('employer/approval-status/', approval_status, name='employer-approval-status'),
    path('applicant/profile/review-skills/', review_resume_skills, name='review-resume-skills'),
    path('applicant/profile/photo/', profile_photo, name='applicant-profile-photo'),
    path('applicant/experience/add/', experience_views.experience, name='add-work-experience'),
    path('applicant/experience/<int:pk>/edit/', experience_views.experience, name='edit-work-experience'),
    path('applicant/experience/<int:pk>/delete/', experience_views.delete_experience, name='delete-work-experience'),
    path('my-applications/<int:pk>/action/', application_action, name='applicant-application-action'),
    path('applicant/certificates/', certificate_views.certificates, name='applicant-certificates'),
    path('certificates/<int:pk>/file/', certificate_views.certificate_file, name='certificate-file'),
    path('applicant/certificates/<int:pk>/delete/', certificate_views.delete_certificate, name='delete-certificate'),
    path('registration/check-resume/', views.resume_check, name='check-resume'),
    path('registration/check-company/', views.registration_company_check, name='check-registration-company'),
    path('employer/company/', views.employer_company_profile, name='employer-company-profile'),
    path('employer/company/edit/', views.edit_employer_company_profile, name='edit-employer-company-profile'),
    path('registration/check-email/', views.registration_email_check, name='check-registration-email'),
    path('registration/check-username/', views.registration_username_check, name='check-registration-username'),
    path('', views.home_view, name='home'),
    path('employee-registration/', views.employee_registration, name='employee-registration'),
    path('applicant-registration/', views.applicant_registration, name='applicant-registration'),
    path('login/', views.login_user, name='login-user'),
    path('employer-dashboard/', views.employer_dashboard, name='employer-dashboard'),
    path('browse-job/', views.browse_job, name="browse-job"),
    path('job-list/', views.job_list, name="job-list"),
    path('post-job/', views.post_job, name="job-post"),
    path('post-job-update/<int:id>/', views.update_job, name="update-job"),
    path("job/delete/<int:id>/", views.employer_delete_job, name="employer-delete-job"),
    path("jobs/<int:id>/", views.job_details, name="job_details"),
    path("company/<int:id>/", views.company_profile, name="company_profile"),
    path('logut/', views.logout_user, name='logout_user'),
    path("job/<int:id>/apply/", views.apply_job, name="apply-job"),
    path("my-applications/", views.my_applications, name="my-applications"),
    path('applicants-list/', views.applicants, name='applicants'),
    path("application/<int:id>/status/", views.update_applicant_status, name="update-applicant-status"),
    path(
    "employee/registration/verify/",
    views.verify_employer_registration,
    name="verify-employer-registration"
),
path(
    "applicant/registration/verify/",
    views.verify_applicant_registration,
    name="verify-applicant-registration"
),
    path(
        "applicant/profile/",
        views.applicant_profile,
        name="applicant-profile",
    ),

    path(
    "applicant/profile/edit/",
    views.edit_applicant_profile,
    name="edit-applicant-profile",
),

]
