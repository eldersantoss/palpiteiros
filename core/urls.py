from django.urls import path

from . import views


app_name = "core"

urlpatterns = [
    path(
        "",
        views.IndexView.as_view(),
        name="index",
    ),
    path(
        "palpitar/",
        views.palpitar,
        name="palpitar",
    ),
    path(
        "palpitar/sucesso",
        views.PalpitarSucessoView.as_view(),
        name="palpitar_sucesso",
    ),
    path(
        "palpitar/encerrado",
        views.PalpitesEncerradosView.as_view(),
        name="palpites_encerrados",
    ),
    path(
        "palpitar/palpiteiro_nao_encontrado",
        views.PalpiteiroNaoEncontradoView.as_view(),
        name="palpiteiro_nao_encontrado",
    ),
    path(
        "classificacao/",
        views.classificacao,
        name="classificacao",
    ),
    path(
        "rodadas/",
        views.RodadasListView.as_view(),
        name="lista_rodadas",
    ),
    path(
        "rodada/<int:id_rodada>/",
        views.detalhes_rodada,
        name="detalhes_rodada",
    ),
]
