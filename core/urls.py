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
        "boloes/<slug:pool_slug>/",
        views.PoolHome.as_view(),
        name="pool_home",
    ),
    path(
        "palpites/",
        views.guesses,
        name="guesses",
    ),
    path(
        "classificacao/",
        views.ranking,
        name="ranking",
    ),
    path(
        "boloes/<slug:pool_slug>/rodadas/",
        views.RoundsListView.as_view(),
        name="round_list",
    ),
    path(
        "boloes/<slug:pool_slug>/rodadas/<slug:round_slug>/",
        views.RoundDetailView.as_view(),
        name="round_details",
    ),
    path(
        "manual_administracao/",
        views.ManualAdminView.as_view(),
        name="manual_administracao",
    ),
    path(
        "OneSignalSDKWorker.js",
        views.one_signal_worker,
        name="one_signal_worker",
    ),
]
