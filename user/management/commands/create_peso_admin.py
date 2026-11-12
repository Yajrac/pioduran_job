from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a PESO administrator account, or reset an existing one's password."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, username, **options):
        User = get_user_model()
        password = getpass("Password: ")
        if password != getpass("Password (again): "):
            raise CommandError("Passwords do not match.")
        user = User.objects.filter(username=username).first() or User(username=username)
        try:
            validate_password(password, user)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages))
        user.role = "admin"
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"PESO admin '{username}' is ready."))
