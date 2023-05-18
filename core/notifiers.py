from typing import Iterable, Literal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

from core.models import Guesser

from .models import Guesser, GuessPool


class EmailNotifier:
    html_structure = """
    <div style='display:flex; justify-content:center; width:100%; margin: 50px 0'>
        <img src='https://palpiteiros-v2.up.railway.app/static/core/img/palpiteiros.png' alt='Logo Palpiteiros' width='100'>
    </div>
    <p style='text-align: center'>
        {}
    </p>
    <p style='text-align: center'>
        {}
    <p>
    <p style='margin: 50px 0; text-align: center'>
        <a href='https://palpiteiros-v2.up.railway.app/' style='text-decoration:none; color: #9acd32; font-weight: bold'>Acessar Palpiteiros</a>
    <p>
    """

    def __init__(
        self,
        notification_type: Literal["new_matches", "updated_matches"],
        guessers: Iterable[Guesser],
    ) -> None:
        if notification_type not in ["new_matches", "updated_matches"]:
            raise ValueError("msg_type value must be 'created' or 'updated'")
        self.notification_type = notification_type
        self.guessers = guessers
        self.email_msgs: list[EmailMultiAlternatives] = []

    def prepare_and_send_notifications(self):
        self.prepare_notifications()
        if self.have_notifications_to_send():
            self.send_notifications()
            return True
        return False

    def prepare_notifications(self) -> str:
        for guesser in self.guessers:
            notifiable_pools = self._get_notifiable_pools(guesser)
            if notifiable_pools.exists():
                email_msg = self._assemble_email(guesser, notifiable_pools)
                self.email_msgs.append(email_msg)

    def have_notifications_to_send(self) -> bool:
        return bool(len(self.email_msgs))

    def send_notifications(self):
        with get_connection() as conn:
            conn.send_messages(self.email_msgs)

    def _get_notifiable_pools(self, guesser: Guesser):
        return (
            guesser.get_involved_pools_with_new_matches()
            if self.notification_type == "new_matches"
            else guesser.get_involved_pools_with_updated_matches()
        )

    def _assemble_email(
        self,
        guesser: Guesser,
        notifiable_pools: Iterable[GuessPool],
    ) -> EmailMultiAlternatives:
        guesser_name = guesser.user.first_name
        text_content, html_content = (
            self._get_plural_content(guesser_name, notifiable_pools)
            if notifiable_pools.count() > 1
            else self._get_singular_content(guesser_name, notifiable_pools)
        )
        recipients = [guesser.user.email]
        email = EmailMultiAlternatives(
            self.subject,
            text_content,
            f"Palpiteiros <{settings.DEFAULT_FROM_EMAIL}>",
            to=recipients,
        )
        email.attach_alternative(html_content, "text/html")
        return email

    def _get_plural_content(
        self,
        guesser_name: str,
        notifiable_pools: Iterable[GuessPool],
    ):
        notifiable_pool_names = [str(np) for np in notifiable_pools]
        pool_names = (
            ", ".join(notifiable_pool_names[:-1]) + f" e {notifiable_pool_names[-1]}"
        )
        text_content = self.text_template_plural.format(
            guesser_name,
            pool_names,
        )

        notifiable_pool_names_strong = [
            f"<strong>{str(pn)}</strong>" for pn in notifiable_pools
        ]
        pool_names_strong = (
            ", ".join(notifiable_pool_names_strong[:-1])
            + f" e {notifiable_pool_names_strong[-1]}"
        )
        html_content = self.html_template_plural.format(
            guesser_name,
            pool_names_strong,
        )
        return text_content, html_content

    def _get_singular_content(
        self,
        guesser_name: str,
        notifiable_pools: Iterable[GuessPool],
    ):
        pool_name = str(notifiable_pools.first())
        text_content = self.text_template_singular.format(
            guesser_name,
            pool_name,
        )

        pool_name_strong = f"<strong>{str(notifiable_pools.first())}</strong>"
        html_content = self.html_template_singular.format(
            guesser_name,
            pool_name_strong,
        )
        return text_content, html_content


class NewMatchesEmailNotifier(EmailNotifier):
    subject = "Novas Partidas Disponíveis"

    text_template_singular = "Olá, {}\nNovas partidas disponíveis no bolão {}. Acesse o app agora mesmo e deixe seus palpites!"
    text_template_plural = "Olá, {}\nNovas partidas disponíveis nos bolões {}. Acesse o app agora mesmo e deixe seus palpites!"

    html_template_singular = EmailNotifier.html_structure.format(
        "Olá, {} 😎",
        "Novas partidas disponíveis no bolão {}. Acesse o app agora mesmo e deixe seus palpites! 🍀⚽",
    )
    html_template_plural = EmailNotifier.html_structure.format(
        "Olá, {} 😎",
        "Novas partidas disponíveis nos bolões {}. Acesse o app agora mesmo e deixe seus palpites! 🍀⚽",
    )

    def __init__(self, guessers: Iterable[Guesser]) -> None:
        super().__init__("new_matches", guessers)


class UpdatedMatchesEmailNotifier(EmailNotifier):
    subject = "Bolões Atualizados"

    text_template_singular = "Olá, {}\nO bolão {} foi atualizado. Acesse o app agora mesmo e confira seus resultados!"
    text_template_plural = "Olá, {}\nOs bolões {} foram atualizados. Acesse o app agora mesmo e confira seus resultados!"

    html_template_singular = EmailNotifier.html_structure.format(
        "Olá, {} 😎",
        "O bolão {} foi atualizado. Acesse o app agora mesmo e confira seus resultados! 📊🏆",
    )
    html_template_plural = EmailNotifier.html_structure.format(
        "Olá, {} 😎",
        "Os bolões {} foram atualizados. Acesse o app agora mesmo e confira seus resultados! 📊🏆",
    )

    def __init__(self, guessers: Iterable[Guesser]) -> None:
        super().__init__("updated_matches", guessers)
