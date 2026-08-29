
"""Django command entry point for the authoritative registry service."""
import os
import sys


def main():
    # Select the project settings before Django dispatches a management command.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "watheeq.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
