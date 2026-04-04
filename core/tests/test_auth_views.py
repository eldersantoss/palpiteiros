import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_logout_get_returns_method_not_allowed(client):
    user = get_user_model().objects.create_user(username="logout-get-user", password="safe-password-123")
    client.force_login(user)

    response = client.get(reverse("logout"))

    assert response.status_code == 405


def test_logout_post_logs_user_out(client):
    user = get_user_model().objects.create_user(username="logout-post-user", password="safe-password-123")
    client.force_login(user)

    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert response.url == reverse("core:index")
    assert "_auth_user_id" not in client.session
