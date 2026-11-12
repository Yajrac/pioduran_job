from django.db import models

class LoginAttemptWindow(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    attempts = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField()
    locked_until = models.DateTimeField(null=True, blank=True)
