from core.models import CompetitionGroup
from django.db.models.signals import m2m_changed
from django.dispatch import receiver


@receiver(m2m_changed, sender=CompetitionGroup.teams.through)
def competition_group_teams_changed(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        instance.recalculate_standings()
