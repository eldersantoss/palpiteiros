from django.core.management.base import BaseCommand, CommandError

from core.models import Guesser
from core.notifiers import PendingMatchesEmailNotifier


class Command(BaseCommand):
    help = "Send an email message notification informing all guessers that there are pending matches in pools theys are involved with."

    def handle(self, *args, **options):
        guessers = Guesser.get_who_should_be_notified_by_email()

        if guessers.exists():
            notifier = PendingMatchesEmailNotifier(guessers)
            if notifier.prepare_and_send_notifications():
                self.stdout.write(
                    "Email notifications of pending matches have been sent."
                )

            else:
                self.stdout.write("No pools with pending matches to notificate.")

        else:
            self.stdout.write("No guessers to notificate.")
