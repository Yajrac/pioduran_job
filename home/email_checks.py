"""Extra email checks for registration (beyond the address format).

* email_domain_error(): the domain must exist and be able to receive mail
  (an MX record, or an address record as the mail standard allows).
  123@hagvd.gov is rejected. If DNS cannot be reached (no internet, timeout),
  the address is allowed rather than blocking a real person.
* suggest_email(): "Did you mean ...?" for common typos of popular domains,
  e.g. 1233@gmaiil.com -> 1233@gmail.com. Typo domains are often registered
  by other people and DO receive mail, so a DNS check cannot catch them.
"""
import difflib

from django.conf import settings

POPULAR_DOMAINS = [
    "gmail.com", "yahoo.com", "yahoo.com.ph", "outlook.com", "hotmail.com",
    "icloud.com", "ymail.com", "live.com",
]
# Real providers that look like a popular domain; never "correct" these.
KNOWN_DOMAINS = set(POPULAR_DOMAINS) | {
    "mail.com", "email.com", "me.com", "msn.com", "aol.com", "gmx.com", "zoho.com",
    "proton.me", "protonmail.com", "yandex.com", "outlook.ph", "hotmail.ph",
}
DNS_TIMEOUT = 3


def _domain(email):
    return (email or "").strip().rpartition("@")[2].strip().strip(".").lower()


_answers = {}  # domain -> True/False; only definite DNS answers are remembered


def _lookup(domain):
    """True / False when DNS gave a definite answer, None when it could not answer."""
    try:
        import dns.exception
        import dns.resolver
    except ImportError:
        return None
    resolver = dns.resolver.Resolver()
    resolver.lifetime = DNS_TIMEOUT
    for record in ("MX", "A", "AAAA"):
        try:
            resolver.resolve(domain, record)
            return True
        except dns.resolver.NXDOMAIN:
            return False
        except dns.resolver.NoAnswer:
            continue
        except dns.exception.DNSException:  # timeout / no network
            return None
    return False


def domain_accepts_mail(domain):
    """Does the domain exist and accept mail? Unknown (DNS down) counts as yes,
    but is NOT remembered, so the next check asks DNS again."""
    if domain in _answers:
        return _answers[domain]
    answer = _lookup(domain)
    if answer is None:
        return True
    if len(_answers) > 2000:
        _answers.clear()
    _answers[domain] = answer
    return answer


domain_accepts_mail.cache_clear = _answers.clear  # used by the tests


def email_domain_error(email):
    """'' when fine, otherwise a message for the form."""
    if not getattr(settings, "EMAIL_DOMAIN_CHECK", True):
        return ""
    domain = _domain(email)
    if not domain or "." not in domain:
        return ""  # the format check reports this
    if domain_accepts_mail(domain):
        return ""
    return "This email domain does not exist or cannot receive email. Please check the spelling."


def suggest_email(email):
    """A corrected address for an obvious typo of a popular domain, else None."""
    email = (email or "").strip()
    local, at, domain = email.rpartition("@")
    domain = domain.lower()
    if not (local and at and domain) or domain in KNOWN_DOMAINS:
        return None
    match = difflib.get_close_matches(domain, POPULAR_DOMAINS, n=1, cutoff=0.8)
    return f"{local}@{match[0]}" if match else None
