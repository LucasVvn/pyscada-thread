#!/usr/bin/env python
"""Point d'entrée Django pour développer et tester le plugin (réglages de tests/)."""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
