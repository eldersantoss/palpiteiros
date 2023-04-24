from django.contrib import admin

from . import models

admin.site.site_header = "Administração Palpiteiros"
admin.site.site_title = "Administração Palpiteiros"
admin.site.index_title = "Selecione entidade para modificar"


@admin.register(models.Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ("__str__", "abreviacao")
    search_fields = ("nome", "abreviacao")


@admin.register(models.Palpiteiro)
class PalpiteiroAdmin(admin.ModelAdmin):
    list_display = ("__str__", "usuario", "guessed_on_last_round")
    search_fields = [
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
    ]


@admin.register(models.Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "data_hora",
        "open_to_guesses",
        "gols_mandante",
        "gols_visitante",
    )
    list_filter = ["rodada"]
    list_editable = [
        "gols_mandante",
        "gols_visitante",
    ]
    filter_horizontal = ["rodada"]


@admin.register(models.Rodada)
class RodadaAdmin(admin.ModelAdmin):
    fields = ["pool", "active"]
    list_display = (
        "__str__",
        "pool",
        "created",
        "modified",
        "number_of_matches",
        "active",
    )
    list_filter = ["pool"]


@admin.register(models.Palpite)
class PalpitesAdmin(admin.ModelAdmin):
    list_display = ("__str__", "palpiteiro")
    list_filter = [
        "palpiteiro",
        "partida__rodada",
    ]


@admin.register(models.GuessPool)
class GuessPoolAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "number_of_teams",
        "number_of_guessers",
        "number_of_rounds",
        "number_of_matches",
        "private",
        "created",
        "modified",
    )
    list_editable = ("private",)
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["teams", "guessers", "guesses"]
