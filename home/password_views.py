import re

from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy


class AccountPasswordForm(PasswordChangeForm):
    def clean_new_password1(self):
        password = self.cleaned_data['new_password1']
        if not (len(password) >= 8 and re.search(r'[A-Z]', password)
                and re.search(r'[a-z]', password) and re.search(r'[0-9]', password)
                and re.search(r'[^A-Za-z0-9]', password)):
            raise ValidationError('Use at least 8 characters with uppercase, lowercase, a number, and a special character.')
        return password


class AccountPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    login_url = reverse_lazy('login-user')
    form_class = AccountPasswordForm
    template_name = 'pages/change_password.html'
    success_url = reverse_lazy('change-password-done')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['account_base'] = ('employer_base.html' if self.request.user.role == 'employer'
                                   else 'home_base.html')
        return context
