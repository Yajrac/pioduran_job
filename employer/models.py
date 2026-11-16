from django.db import models
from user.models import User
from applicant.models import Applicant
from django.utils import timezone
from .job_categories import CATEGORY_CHOICES


class Employer(models.Model):
    APPROVAL_CHOICES = [('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected')]
    approval_status = models.CharField(max_length=12, choices=APPROVAL_CHOICES, default='approved')
    approval_remarks = models.TextField(blank=True, max_length=2000)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    employer = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    business_permit_no = models.CharField(max_length=255, unique=True)
    contact_no = models.CharField(max_length=11, unique=True)
    description = models.TextField()
    company_logo = models.ImageField(upload_to="company_logo")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

class EmployerRegistrationOTP(models.Model):
    username = models.CharField(max_length=150)
    email = models.EmailField()
    password = models.CharField(max_length=255)

    company_name = models.CharField(max_length=255)
    business_permit_no = models.CharField(max_length=255)
    contact_no = models.CharField(max_length=11)

    description = models.TextField(
        blank=True,
        null=True
    )

    company_logo = models.ImageField(
        upload_to="company_logo",
        blank=True,
        null=True
    )

    otp_code = models.CharField(max_length=6)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    expires_at = models.DateTimeField()

    is_verified = models.BooleanField(
        default=False
    )

    def is_expired(self):
        return timezone.now() > self.expires_at



class JobPostQuerySet(models.QuerySet):
    def public(self):
        """Jobs the public may see and apply to: the post is approved AND its
        employer is approved and not suspended. Suspending an employer hides
        their jobs; activating them again brings the jobs back."""
        return self.filter(status="approved", employer__approval_status="approved", employer__is_active=True)


class JobPost(models.Model):
    objects = JobPostQuerySet.as_manager()

    STATUS_CHOICES = (
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    JOB_TYPE = (
        ("full_time", "Full Time"),
        ("part_time", "Part Time"),
        ("contract", "Contract"),
        ("internship", "Internship"),
        ("temporary", "Temporary"),
    )

    employer = models.ForeignKey(
        Employer,
        on_delete=models.CASCADE,
        related_name="jobs"
    )

    title = models.CharField(max_length=255)
    description = models.TextField()

    qualifications = models.TextField()
    required_skills = models.TextField(blank=True, default='')
    experience_required = models.BooleanField(default=False)
    responsibilities = models.TextField(blank=True)

    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    location = models.CharField(max_length=255)

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="other",
        db_index=True,
    )

    job_type = models.CharField(
        max_length=20,
        choices=JOB_TYPE,
        default="full_time"
    )

    vacancies = models.PositiveIntegerField(default=1)

    deadline = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    admin_remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    @property
    def salary_display(self):
        if self.salary is None:
            return "Salary not specified"

        return f"₱{self.salary:,.2f}"

    @property
    def is_public(self):
        return (self.status == "approved" and self.employer.approval_status == "approved"
                and self.employer.is_active)

    def __str__(self):
        return f"{self.title} ({self.status})"
    
class JobApplication(models.Model):
    application_snapshot = models.JSONField(null=True, blank=True, editable=False)

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("reviewing", "Reviewing"),
        ("shortlisted", "Shortlisted"),
        ("accepted", "Accepted"),
        ("offered", "Offered"),
        ("hired", "Hired"),
        ("withdrawn", "Withdrawn"),
        ("declined", "Declined"),
        ("rejected", "Rejected"),
    )

    job = models.ForeignKey(
        JobPost,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    message = models.TextField(blank=True)

    # Application-specific documents
    resume = models.FileField(
        upload_to="job_applications/resumes/",
        blank=True,
        null=True
    )

    cover_letter = models.FileField(
        upload_to="job_applications/cover_letters/",
        blank=True,
        null=True
    )

    applied_at = models.DateTimeField(auto_now_add=True)
    hired_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    class Meta:
        unique_together = ("job", "applicant")

    def __str__(self):
        return f"{self.applicant} - {self.job.title}"

    def save(self, *args, **kwargs):
        if self._state.adding and self.application_snapshot is None:
            self.application_snapshot = {
                'skills': self.applicant.skills or '',
                'experience': list(self.applicant.work_experiences.values('job_title', 'company', 'description')),
                'job_title': self.job.title, 'required_skills': self.job.required_skills,
                'experience_required': self.job.experience_required,
                'qualifications': self.job.qualifications,
            }
        return super().save(*args, **kwargs)


class ApplicantAssessment(models.Model):
    OUTCOMES = [('not_evaluated', 'Not Yet Evaluated'), ('started', 'Started Work'), ('passed', 'Passed Probation'), ('failed', 'Did Not Pass Probation')]
    application = models.OneToOneField(JobApplication, on_delete=models.CASCADE, related_name='assessment')
    skills_score = models.PositiveSmallIntegerField(null=True, blank=True)
    interview_score = models.PositiveSmallIntegerField(null=True, blank=True)
    assessment_notes = models.TextField(blank=True, max_length=3000)
    outcome = models.CharField(max_length=20, choices=OUTCOMES, default='not_evaluated')
    started_on = models.DateField(null=True, blank=True)
    evaluated_on = models.DateField(null=True, blank=True)
    outcome_notes = models.TextField(blank=True, max_length=3000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(skills_score__isnull=True) | models.Q(skills_score__lte=5), name='assessment_skills_max_five'),
            models.CheckConstraint(condition=models.Q(interview_score__isnull=True) | models.Q(interview_score__lte=5), name='assessment_interview_max_five'),
        ]
