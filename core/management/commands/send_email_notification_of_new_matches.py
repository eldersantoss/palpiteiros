from django.core.management.base import BaseCommand, CommandError

from core.models import GuessPool, Palpiteiro
from core.notifiers import NewMatchesEmailNotifier


class Command(BaseCommand):
    help = "Send a email message notification informing all guessers that new matches is available to guesses."

    def handle(self, *args, **options):
        guessers = Palpiteiro.get_who_should_be_notified_by_email()

        if guessers.exists():
            notifier = NewMatchesEmailNotifier(guessers)
            if notifier.prepare_and_send_notifications():
                GuessPool.toggle_flag_value("new_matches")
                self.stdout.write("Email notifications of new matches have been sent.")

            else:
                self.stdout.write("No pools with new matches to notificate.")

        else:
            self.stdout.write("No guessers to notificate.")
