from django import forms
from employer.models import Employer
from user.models import User
from .registration_validation import clean_company_name, company_name_error, description_error, logo_error, permit_file_error


class CompanyProfileForm(forms.ModelForm):
    email = forms.EmailField(label='Company Email', max_length=254)

    class Meta:
        model = Employer
        fields = ['company_name', 'contact_no', 'description', 'company_logo', 'business_permit_file']
        labels = {'contact_no': 'Mobile Number', 'description': 'Company Description', 'company_logo': 'Company Logo', 'business_permit_file': 'Business Permit'}
        widgets = {
            'contact_no': forms.TextInput(attrs={'inputmode': 'numeric', 'maxlength': 11, 'pattern': '09[0-9]{9}'}),
            'company_logo': forms.FileInput(attrs={'accept': 'image/png,image/jpeg,image/webp'}),
            'company_name': forms.TextInput(attrs={'maxlength': 150}),
            'description': forms.Textarea(attrs={'rows': 5, 'maxlength': 1000}),
            'business_permit_file': forms.FileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company_logo'].required = False
        self.fields['business_permit_file'].required = False
        if self.instance.pk:
            self.initial['email'] = self.instance.employer.email
        for name, field in self.fields.items():
            field.widget.attrs['aria-describedby'] = f'id_{name}_errors'

    def clean_company_name(self):
        value = clean_company_name(self.cleaned_data['company_name'])
        error = company_name_error(value)
        if error:
            raise forms.ValidationError(error)
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

    def clean_description(self):
        value = self.cleaned_data['description'].strip()
        error = description_error(value)
        if error:
            raise forms.ValidationError(error)
        return value

    def clean_company_logo(self):
        logo = self.cleaned_data.get('company_logo')
        if 'company_logo' in self.files and logo:
            error = logo_error(logo)
            if error:
                raise forms.ValidationError(error)
        return logo

    def clean_business_permit_file(self):
        permit = self.cleaned_data.get('business_permit_file')
        if 'business_permit_file' in self.files and permit:
            error = permit_file_error(permit)
            if error:
                raise forms.ValidationError(error)
        return permit
