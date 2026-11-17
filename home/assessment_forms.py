from django import forms
from django.utils import timezone
from employer.models import ApplicantAssessment


class AssessmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ['skills_score', 'interview_score']:
            self.fields[name].widget.attrs.update({'step':1, 'inputmode':'numeric'})
            self.fields[name].error_messages.update({
                'min_value':'Score cannot be negative.',
                'max_value':'Score must not exceed 5.',
                'invalid':'Enter a whole number from 0 to 5.',
            })
    skills_score = forms.IntegerField(min_value=0, max_value=5, required=False, label='Skills test score (0–5)')
    interview_score = forms.IntegerField(min_value=0, max_value=5, required=False, label='Interview score (0–5)')

    class Meta:
        model = ApplicantAssessment
        fields = ['skills_score', 'interview_score', 'assessment_notes']
        widgets = {'assessment_notes':forms.Textarea(attrs={'rows':4})}


class OutcomeForm(forms.ModelForm):
    class Meta:
        model = ApplicantAssessment
        fields = ['outcome', 'started_on', 'evaluated_on', 'outcome_notes']
        widgets = {'started_on':forms.DateInput(attrs={'type':'date'}, format='%Y-%m-%d'),
                   'evaluated_on':forms.DateInput(attrs={'type':'date'}, format='%Y-%m-%d'),
                   'outcome_notes':forms.Textarea(attrs={'rows':4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        application = getattr(self.instance, 'application', None)
        hired_at = getattr(application, 'hired_at', None)
        self.hired_on = timezone.localtime(hired_at).date() if hired_at else None
        today = timezone.localdate().isoformat()
        start_min = self.hired_on.isoformat() if self.hired_on else ''
        self.fields['started_on'].widget.attrs.update({'max': today, 'min': start_min})
        self.fields['evaluated_on'].widget.attrs.update({
            'max': today,
            'min': (self.instance.started_on.isoformat() if self.instance.started_on else start_min),
        })

    def clean(self):
        data = super().clean()
        outcome, start, evaluated = data.get('outcome'), data.get('started_on'), data.get('evaluated_on')
        today = timezone.localdate()
        if start and self.hired_on and start < self.hired_on:
            self.add_error('started_on', f"The start date cannot be earlier than the hire date ({self.hired_on:%b %d, %Y}).")
        if outcome in {'started','passed','failed'} and not start:
            self.add_error('started_on', 'Enter the actual work start date.')
        if outcome in {'passed','failed'} and not evaluated:
            self.add_error('evaluated_on', 'Enter the probation evaluation date.')
        for field in ['started_on','evaluated_on']:
            value = data.get(field)
            if value and value > today:
                self.add_error(field, 'Date cannot be in the future.')
        if start and evaluated and evaluated < start:
            self.add_error('evaluated_on', 'Evaluation date cannot be before the work start date.')
        if outcome in {'passed','failed'} and not data.get('outcome_notes', '').strip():
            self.add_error('outcome_notes', 'Explain the probation evaluation using job-related evidence.')
        if outcome == 'not_evaluated':
            data['started_on'] = data['evaluated_on'] = None
        elif outcome == 'started':
            data['evaluated_on'] = None
        return data
