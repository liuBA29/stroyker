from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections

UserModel = get_user_model()


class Command(BaseCommand):
    help = 'Change a stroykerbox default admin password.'
    requires_migrations_checks = True
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            'user_email',
            nargs='?',
            help=(
                'User email to change password.'
            ),
        )
        parser.add_argument(
            'new_password',
            nargs='?',
            help=(
                'New password.'
            ),
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            choices=tuple(connections),
            help='Specifies the database to use. Default is "default".',
        )

    def handle(self, *args, **options):
        if not all((options['user_email'], options['new_password'])):
            return 'Required data not provided, process is skiped.'

        try:
            u = UserModel._default_manager.using(options["database"]).get(
                email=options['user_email']
            )
        except UserModel.DoesNotExist:
            return f'user with email {options["user_email"]} does not exist'

            try:
                validate_password(options['new_password'], u)
            except ValidationError as err:
                return "\n".join(err.messages)

        u.set_password(options['new_password'])
        u.save()
        return f'Password changed successfully for user {u}'
