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
        "boloes/buscar/",
        views.GuessPoolListView.as_view(),
        name="pool_list",
    ),
    path(
        "boloes/criar-bolao/",
        views.CreatePoolView.as_view(),
        name="create_pool",
    ),
    path(
        "boloes/<uuid:uuid>/",
        views.GuessPoolSignInView.as_view(),
        name="signin_pool",
    ),
    path(
        "boloes/<slug:pool_slug>/sair/<uuid:uuid>/",
        views.GuessPoolSignOutView.as_view(),
        name="signout_pool",
    ),
    path(
        "boloes/<slug:pool_slug>/",
        views.PoolHomeView.as_view(),
        name="pool_home",
    ),
    path(
        "boloes/<slug:pool_slug>/gerenciar/",
        views.ManagePoolView.as_view(),
        name="pool_management",
    ),
    path(
        "boloes/<slug:pool_slug>/palpites/",
        views.GuessesView.as_view(),
        name="guesses",
    ),
    path(
        "boloes/<slug:pool_slug>/classificacao/",
        views.RankingView.as_view(),
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
        "OneSignalSDKWorker.js",
        views.one_signal_worker,
        name="one_signal_worker",
    ),
]
