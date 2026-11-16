from django.db import models

class LoginAttemptWindow(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    attempts = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField()
    locked_until = models.DateTimeField(null=True, blank=True)


class PasswordResetCode(models.Model):
    """A 6-digit SMS code for 'Forgot password'. Only the hash is stored.

    `user` is set when the person typed a username/email (only that account
    may be reset). It is empty when they typed a mobile number: after the
    code is confirmed, any applicant/employer account on that number may be
    chosen, since the person proved they hold the phone.
    """
    phone = models.CharField(max_length=11, db_index=True)
    user = models.ForeignKey("user.User", null=True, blank=True, on_delete=models.CASCADE)
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
