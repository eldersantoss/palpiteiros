from django.contrib import admin

from .models import Equipe, Rodada, Partida, Palpiteiro, Palpite


admin.site.site_header = "Administração Palpiteiros"
admin.site.site_title = "Administração Palpiteiros"
admin.site.index_title = "Selecione entidade para modificar"


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ("__str__", "abreviacao")
    search_fields = ("nome", "abreviacao")


@admin.register(Palpiteiro)
class PalpiteiroAdmin(admin.ModelAdmin):
    list_display = ("__str__", "usuario", "obter_pontuacao_geral")
    search_fields = [
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
    ]


@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "rodada",
        "data_hora",
        "aberta_para_palpites",
        "gols_mandante",
        "gols_visitante",
    )
    list_filter = ["rodada"]
    list_editable = [
        "gols_mandante",
        "gols_visitante",
    ]


class PartidaInline(admin.TabularInline):
    model = Partida
    extra = 0
    ordering = ["data_hora"]


@admin.register(Rodada)
class RodadaAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "numero_partidas",
        "abertura",
        "fechamento",
        "aberta_para_palpites",
    )
    inlines = [PartidaInline]


@admin.register(Palpite)
class PalpitesAdmin(admin.ModelAdmin):
    list_display = ("__str__", "palpiteiro")
    list_filter = [
        "palpiteiro",
        "partida__rodada",
    ]
