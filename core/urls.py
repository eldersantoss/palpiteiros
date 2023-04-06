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
        "palpites/",
        views.guesses,
        name="guesses",
    ),
    path(
        "manual_administracao/",
        views.ManualAdminView.as_view(),
        name="manual_administracao",
    ),
    path(
        "classificacao/",
        views.ranking,
        name="ranking",
    ),
    path(
        "rodadas/",
        views.RoundsListView.as_view(),
        name="lista_rodadas",
    ),
    path(
        "rodadas/<slug:slug>/",
        views.round_details,
        name="round_details",
    ),
    path(
        "OneSignalSDKWorker.js",
        views.one_signal_worker,
        name="one_signal_worker",
    ),
]
