import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from core.models import Competition, CompetitionGroup, Team

OPERATIONS = {}


def operation(name):
    def decorator(func):
        OPERATIONS[name] = func
        return func

    return decorator


@operation("rename_old_national_teams")
def rename_old_national_teams(command: BaseCommand, dry_run: bool = False) -> None:
    OLD_SUFFIX = " (old)"
    COMPETITION_IDS = [38, 46, 41, 47]

    teams = (
        Team.objects.filter(
            competitions__id__in=COMPETITION_IDS,
        )
        .exclude(name__endswith=OLD_SUFFIX)
        .distinct()
    )

    count = teams.count()
    if not count:
        command.stdout.write("No teams to rename.")
        return

    for team in teams:
        command.stdout.write(f"  {team.name} → {team.name}{OLD_SUFFIX}")
        team.name = f"{team.name}{OLD_SUFFIX}"

    if dry_run:
        command.stdout.write(f"Dry run: {count} team(s) would be renamed.")
        return

    Team.objects.bulk_update(teams, ["name"])
    command.stdout.write(f"Renamed {count} team(s).")


@operation("create_and_populate_groups")
def create_and_populate_groups(command: BaseCommand, dry_run: bool = False, file: Path | None = None) -> None:
    WORLD_CUP_COMPETITION_SFI_ID = "5085a3cde16c822b"

    if file is None:
        command.stderr.write("A path to the groups JSON file is required. Aborting.")
        return

    try:
        competition = Competition.objects.get(sfi_id=WORLD_CUP_COMPETITION_SFI_ID)
    except Competition.DoesNotExist:
        command.stderr.write(f"Competition with sfi_id={WORLD_CUP_COMPETITION_SFI_ID} not found. Aborting.")
        return

    with file.open(encoding="utf-8") as f:
        groups_data = json.load(f)

    groups_created = groups_updated = teams_created = teams_renamed = teams_assigned = 0

    for group_data in groups_data:
        group_name = group_data["name"]
        teams_data = group_data["teams"]

        command.stdout.write(f"  Processing {group_name}...")

        teams = []
        for team_data in teams_data:
            team, created = Team.objects.get_or_create(
                sfi_id=team_data["id"],
                defaults={"name": team_data["name"]},
            )
            if created:
                command.stdout.write(f"    NEW TEAM: {team_data['name']} (sfi_id={team_data['id']})")
                teams_created += 1
            elif team.name != team_data["name"]:
                command.stdout.write(f"    RENAME: {team.name} → {team_data['name']}")
                if not dry_run:
                    team.name = team_data["name"]
                    team.save(update_fields=["name"])
                teams_renamed += 1
            teams.append(team)

        if dry_run:
            action = "would create" if not competition.groups.filter(name=group_name).exists() else "would update"
            command.stdout.write(f"    Dry run: {action} {group_name} with {len(teams)} team(s).")
            continue

        group, created = CompetitionGroup.objects.get_or_create(
            competition=competition,
            name=group_name,
        )

        group.teams.set(teams)
        competition.teams.add(*teams)

        if created:
            groups_created += 1
        else:
            groups_updated += 1

        teams_assigned += len(teams)

    if dry_run:
        command.stdout.write("Dry run complete.")
        return

    command.stdout.write(
        f"Done: {groups_created} group(s) created, {groups_updated} group(s) updated, "
        f"{teams_created} team(s) registered, {teams_renamed} team(s) renamed, "
        f"{teams_assigned} team(s) assigned to groups."
    )


class Command(BaseCommand):
    help = "Prepare the database for the World Cup."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "operation",
            choices=list(OPERATIONS.keys()),
            help="Operation to perform.",
        )
        parser.add_argument(
            "file",
            type=Path,
            nargs="?",
            default=None,
            help="Path to the input file required by some operations (e.g. create_and_populate_groups).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Simulate the operation without persisting changes to the database.",
        )

    def handle(self, *args, **options) -> None:
        OPERATIONS[options["operation"]](self, dry_run=options["dry_run"], file=options["file"])
