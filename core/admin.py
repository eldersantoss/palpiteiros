from django.contrib import admin

from . import models

admin.site.site_header = "Administração Palpiteiros"
admin.site.site_title = "Administração Palpiteiros"
admin.site.index_title = "Selecione entidade para modificar"


@admin.register(models.Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("__str__", "code")
    search_fields = ("name", "code")


@admin.register(models.Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ("name", "season")
    search_fields = ("name", "season")
    filter_horizontal = ["teams"]


@admin.register(models.Guesser)
class GuesserAdmin(admin.ModelAdmin):
    list_display = ("__str__", "user")
    search_fields = [
        "user__username",
        "user__first_name",
        "user__last_name",
    ]


@admin.register(models.Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "competition",
        "date_time",
        "status",
        "open_to_guesses",
        "home_goals",
        "away_goals",
    )
    list_filter = ["competition", "status"]


@admin.register(models.Guess)
class GuessesAdmin(admin.ModelAdmin):
    list_display = ("__str__", "guesser")
    list_filter = ["guesser"]


@admin.register(models.GuessPool)
class GuessPoolAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "number_of_teams",
        "number_of_guessers",
        "number_of_matches",
        "private",
        "new_matches",
        "updated_matches",
        "created",
        "modified",
    )
    list_editable = ("private", "new_matches", "updated_matches")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["teams", "guessers", "guesses"]
