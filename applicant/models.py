from django.db import models
from user.models import User
from django.utils import timezone
from .certificate_storage import certificate_storage, certificate_path


class WorkExperience(models.Model):
    applicant = models.ForeignKey("Applicant", on_delete=models.CASCADE, related_name="work_experiences")
    job_title = models.CharField(max_length=150)
    company = models.CharField(max_length=150)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True, max_length=3000)

    class Meta:
        ordering = ["-start_date", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__isnull=True) | models.Q(end_date__gte=models.F("start_date")), name="experience_dates_in_order"),
            models.CheckConstraint(condition=models.Q(is_current=False) | models.Q(end_date__isnull=True), name="current_experience_no_end"),
        ]

    def __str__(self):
        return f"{self.job_title} at {self.company}"


class ApplicantCertificate(models.Model):
    applicant = models.ForeignKey("Applicant", on_delete=models.CASCADE, related_name="certificates")
    title = models.CharField(max_length=150)
    file = models.FileField(storage=certificate_storage, upload_to=certificate_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title

class Applicant(models.Model):
    profile_photo = models.ImageField(upload_to="applicant_photos/", blank=True)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="applicant_profile"
    )

    first_name = models.CharField(max_length=266)
    last_name = models.CharField(max_length=266)
    middle_name = models.CharField(max_length=266)

    email = models.EmailField(unique=True)

    phone_number = models.CharField(max_length=11)

    skills = models.TextField(
        blank=True,
        null=True,
        help_text="Enter skills separated by commas. Example: Python, Django, React, SQL"
    )

    resume = models.FileField(upload_to="resume/")
    cover_letter = models.FileField(upload_to="cover/")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class ApplicantRegistrationOTP(models.Model):

    username = models.CharField(max_length=150)

    email = models.EmailField()

    phone_number = models.CharField(max_length=11)

    first_name = models.CharField(max_length=266)
    last_name = models.CharField(max_length=266)
    middle_name = models.CharField(max_length=266)

    password = models.CharField(max_length=255)

    resume = models.FileField(
        upload_to="resume/",
        blank=True,
        null=True
    )

    cover_letter = models.FileField(
        upload_to="cover/",
        blank=True,
        null=True
    )

    skills = models.TextField(
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
