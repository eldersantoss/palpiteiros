from django.core.management.base import BaseCommand

from core.models import Guesser, GuessPool
from core.notifiers import UpdatedMatchesEmailNotifier


class Command(BaseCommand):
    help = "Send a email message notification informing all guessers that matches of your involved pools have been updated."

    def handle(self, *args, **options):
        guessers = Guesser.get_who_should_be_notified_by_email()

        if guessers.exists():
            notifier = UpdatedMatchesEmailNotifier(guessers)
            if notifier.prepare_and_send_notifications():
                GuessPool.toggle_flag_value("updated_matches")
                self.stdout.write(
                    "Email notifications of updated matches have been sent."
                )

            else:
                self.stdout.write("No pools with updated matches to notificate.")

        else:
            self.stdout.write("No guessers to notificate.")
