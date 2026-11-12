import re
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from applicant.models import Applicant
from .resume_validation import extract_resume_text
from .skill_extraction import detect_skills


class SkillReviewForm(forms.Form):
    skills = forms.CharField(required=False, max_length=1500, widget=forms.Textarea(attrs={'rows':3, 'id':'skills'}), label='Your current skills')
    suggested = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, label='Select skills to add')

    def __init__(self, *args, suggestions=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['suggested'].choices = [(skill, skill) for skill in suggestions]

    def clean(self):
        data = super().clean()
        skills = [re.sub(r'\s+', ' ', skill).strip() for skill in re.split(r'[,;\n|]+', data.get('skills', '')) if skill.strip()]
        skills += data.get('suggested', [])
        unique = {}
        for skill in skills:
            unique.setdefault(skill.casefold(), skill)
        if not unique:
            raise forms.ValidationError('Add at least one skill before saving.')
        if len(unique) > 20 or any(len(skill) > 60 or not any(c.isalpha() for c in skill) for skill in unique.values()):
            raise forms.ValidationError('Use up to 20 skills, each containing a letter and at most 60 characters.')
        data['confirmed_skills'] = ', '.join(unique.values())
        return data


@login_required(login_url='login-user')
def review_resume_skills(request):
    applicant = get_object_or_404(Applicant, user=request.user)
    warning = ''
    detected = []
    if applicant.resume:
        try:
            with applicant.resume.open('rb') as upload:
                text = extract_resume_text(upload)
            detected = detect_skills(text)
            if not text.strip():
                warning = 'Resume text could not be read. You can enter your skills manually.'
        except Exception:
            warning = 'Resume text could not be read. You can enter your skills manually.'
    else:
        warning = 'Upload a resume through Edit Profile to detect skills, or enter them manually.'
    existing = {skill.strip().casefold() for skill in re.split(r'[,;\n|]+', applicant.skills or '')}
    suggestions = [skill for skill in detected if skill.casefold() not in existing]
    form = SkillReviewForm(request.POST if request.method == 'POST' else None, suggestions=suggestions, initial={'skills':applicant.skills or ''})
    if request.method == 'POST' and form.is_valid():
        applicant.skills = form.cleaned_data['confirmed_skills']
        applicant.save(update_fields=['skills'])
        messages.success(request, 'Confirmed skills saved. Your job recommendations now use these skills.')
        return redirect('applicant-profile')
    return render(request, 'pages/review_skills.html', {'skill_form':form, 'suggestions':suggestions, 'warning':warning})
