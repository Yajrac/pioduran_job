from django import forms
from employer.models import Employer
from user.models import User


class CompanyProfileForm(forms.ModelForm):
    email = forms.EmailField(label='Company Email', max_length=254)

    class Meta:
        model = Employer
        fields = ['company_name', 'contact_no', 'description', 'company_logo']
        labels = {'contact_no': 'Mobile Number', 'description': 'Company Description', 'company_logo': 'Company Logo'}
        widgets = {
            'contact_no': forms.TextInput(attrs={'inputmode': 'numeric', 'maxlength': 11, 'pattern': '09[0-9]{9}'}),
            'description': forms.Textarea(attrs={'rows': 5}),
            'company_logo': forms.FileInput(attrs={'accept': 'image/png,image/jpeg,image/webp'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company_logo'].required = False
        if self.instance.pk:
            self.initial['email'] = self.instance.employer.email
        for name, field in self.fields.items():
            field.widget.attrs['aria-describedby'] = f'id_{name}_errors'

    def clean_company_name(self):
        value = self.cleaned_data['company_name'].strip()
        if Employer.objects.filter(company_name__iexact=value).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Company name is already registered.')
        return value

    def clean_contact_no(self):
        import re
        value = self.cleaned_data['contact_no'].strip()
        if not re.fullmatch(r'09[0-9]{9}', value):
            raise forms.ValidationError('Enter an 11-digit mobile number starting with 09.')
        if Employer.objects.filter(contact_no=value).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Mobile number is already registered.')
        return value

    def clean_email(self):
        value = self.cleaned_data['email'].strip()
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.employer_id).exists():
            raise forms.ValidationError('Email address is already registered.')
        return value

    def clean_company_logo(self):
        logo = self.cleaned_data.get('company_logo')
        if 'company_logo' in self.files and logo:
            if logo.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Logo must not exceed 5 MB.')
            if getattr(logo, 'image', None) and logo.image.format not in ['PNG', 'JPEG', 'WEBP']:
                raise forms.ValidationError('Upload a PNG, JPEG, or WebP image.')
        return logo
