from django.contrib import admin

from .models import Equipe, Rodada, Partida, Palpiteiro, Palpite


class EquipeAdmin(admin.ModelAdmin):
    list_display = ("__str__", "abreviacao")
    search_fields = ("nome", "abreviacao")


class PalpiteiroAdmin(admin.ModelAdmin):
    list_display = ("__str__", "usuario", "obter_pontuacao_geral")
    search_fields = [
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
    ]


class PartidaAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "rodada",
        "data_hora",
        "aberta_para_palpites",
    )
    list_filter = ["rodada"]


class PartidaInline(admin.TabularInline):
    model = Partida
    extra = 0
    ordering = ["data_hora"]


class RodadaAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "numero_partidas",
        "abertura",
        "fechamento",
        "aberta_para_palpites",
    )
    inlines = [PartidaInline]


class PalpitesAdmin(admin.ModelAdmin):
    list_display = ("__str__", "palpiteiro")
    list_filter = [
        "palpiteiro",
        "partida__rodada",
    ]


admin.site.register(Equipe, EquipeAdmin)
admin.site.register(Palpiteiro, PalpiteiroAdmin)
admin.site.register(Partida, PartidaAdmin)
admin.site.register(Rodada, RodadaAdmin)
admin.site.register(Palpite, PalpitesAdmin)

admin.site.site_header = "Administração Palpiteiros"
admin.site.site_title = "Administração Palpiteiros"
admin.site.index_title = "Selecione entidade para modificar"
