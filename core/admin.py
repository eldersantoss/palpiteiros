from django.contrib import admin

from . import models

admin.site.site_header = "Administração Palpiteiros"
admin.site.site_title = "Administração Palpiteiros"
admin.site.index_title = "Selecione entidade para modificar"


@admin.register(models.Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ("__str__", "abreviacao")
    search_fields = ("nome", "abreviacao")


@admin.register(models.Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ("name", "season")
    search_fields = ("name", "season")
    filter_horizontal = ["teams"]


@admin.register(models.Palpiteiro)
class PalpiteiroAdmin(admin.ModelAdmin):
    list_display = ("__str__", "usuario")
    search_fields = [
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
    ]


@admin.register(models.Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "competition",
        "data_hora",
        "status",
        "open_to_guesses",
        "gols_mandante",
        "gols_visitante",
    )
    list_filter = ["competition"]


@admin.register(models.Palpite)
class PalpitesAdmin(admin.ModelAdmin):
    list_display = ("__str__", "palpiteiro")
    list_filter = ["palpiteiro"]


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
