from django import forms
from django.utils import timezone
from applicant.models import WorkExperience


class WorkExperienceForm(forms.ModelForm):
    class Meta:
        model = WorkExperience
        fields = ["job_title", "company", "start_date", "end_date", "is_current", "description"]
        labels = {"is_current": "I currently work here", "description": "Responsibilities and skills used"}
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Describe your work and the skills you used."}),
        }

    def clean(self):
        data = super().clean()
        start, end = data.get("start_date"), data.get("end_date")
        today = timezone.localdate()
        if start and start > today:
            self.add_error("start_date", "Start date cannot be in the future.")
        if data.get("is_current"):
            data["end_date"] = None
            self.instance.end_date = None
        elif not end:
            self.add_error("end_date", "Enter an end date or select 'I currently work here'.")
        elif start and end < start:
            self.add_error("end_date", "End date must be on or after the start date.")
        elif end > today:
            self.add_error("end_date", "End date cannot be in the future.")
        return data
