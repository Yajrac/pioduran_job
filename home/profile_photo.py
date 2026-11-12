from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from PIL import Image
from applicant.models import Applicant


class ProfilePhotoForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = ['profile_photo']
        widgets = {'profile_photo': forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'})}

    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        if not photo:
            raise forms.ValidationError('Choose a profile photo.')
        if photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Photo must not exceed 5 MB.')
        try:
            image = Image.open(photo)
            if image.format not in {'JPEG', 'PNG', 'WEBP'}:
                raise ValueError()
            if image.width * image.height > 25000000:
                raise ValueError()
            image.verify()
        except Exception:
            raise forms.ValidationError('Upload a valid JPG, PNG, or WebP image (up to 25 megapixels).')
        finally:
            photo.seek(0)
        return photo


@login_required(login_url='login-user')
def profile_photo(request):
    applicant = get_object_or_404(Applicant, user=request.user)
    form = ProfilePhotoForm(request.POST if request.method == 'POST' else None,
                            request.FILES if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        applicant.profile_photo = form.cleaned_data['profile_photo']
        applicant.save(update_fields=['profile_photo'])
        messages.success(request, 'Profile photo updated.')
        return redirect('applicant-profile')
    return render(request, 'pages/profile_photo.html', {'photo_form': form, 'applicant': applicant})
