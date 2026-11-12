import hashlib
import math
from datetime import timedelta
from functools import wraps

from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .models import LoginAttemptWindow

LIMIT = 5
PERIOD = timedelta(minutes=5)


def limited_login(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        request._login_template = 'login.html' if view.__module__ == 'core.views' else 'pages/login.html'
        if request.method != 'POST':
            return view(request, *args, **kwargs)
        # REMOTE_ADDR is server-provided; do not trust arbitrary forwarded headers.
        identity = request.POST.get('username', '').strip().casefold()
        raw = f"{request.META.get('REMOTE_ADDR', '')}\0{identity}"
        key = hashlib.sha256(raw.encode()).hexdigest()
        now = timezone.now()
        rows = LoginAttemptWindow.objects.filter(pk=key)
        LoginAttemptWindow.objects.get_or_create(key=key, defaults={'started_at': now})
        # Conditional updates reserve an attempt before authentication, including
        # concurrent requests. Rows persist across reloads and worker restarts.
        rows.filter(
            Q(locked_until__lte=now) |
            Q(locked_until__isnull=True, started_at__lte=now - PERIOD)
        ).update(attempts=0, started_at=now, locked_until=None)
        reserved = rows.filter(attempts__lt=LIMIT, locked_until__isnull=True).update(attempts=F('attempts') + 1)
        if not reserved:
            return cooldown_response(request, rows.get(), now)
        rows.filter(attempts__gte=LIMIT, locked_until__isnull=True).update(locked_until=now + PERIOD)
        response = view(request, *args, **kwargs)
        if getattr(request, '_public_login_success', False):
            rows.delete()
        else:
            state = rows.first()
            if state and state.locked_until:
                return cooldown_response(request, state, timezone.now())
            if state and state.attempts >= 3:
                warning = (
                    f'{state.attempts} failed login attempts. '
                    f'{LIMIT - state.attempts} attempt(s) remaining before a 5-minute cooldown.'
                )
                if request.headers.get('Accept') == 'application/json':
                    import json
                    data = json.loads(response.content)
                    data['warning'] = warning
                    response.content = json.dumps(data)
                else:
                    context = {
                        'login_notice': warning,
                        'login_error_field': 'password' if 'Wrong password.' in response.content.decode() else 'username',
                        'login_error': 'Invalid username or password.',
                    }
                    response = render(request, request._login_template, context, status=response.status_code)
        return response
    return wrapped


def cooldown_response(request, state, now):
    until = state.locked_until or (state.started_at + PERIOD)
    seconds = max(1, math.ceil((until - now).total_seconds()))
    message = f'Too many login attempts. Please try again in {math.ceil(seconds / 60)} minute(s).'
    if request.headers.get('Accept') == 'application/json':
        response = JsonResponse({
            'error': message, 'retry_after': seconds,
            'clear_fields': ['username', 'password'],
        }, status=429)
    else:
        response = render(request, getattr(request, '_login_template', 'pages/login.html'), {'login_notice': message}, status=429)
    response['Retry-After'] = str(seconds)
    return response
