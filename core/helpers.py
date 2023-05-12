from typing import Literal

from django.contrib import messages
from django.http import HttpRequest
from django.shortcuts import redirect


def redirect_with_msg(
    request: HttpRequest,
    msg_type: Literal["debug", "info", "success", "warning", "error"],
    msg: str,
    msg_duration: Literal["short", "mid", "long"] = "mid",
    to="core:index",
    permanent=False,
):
    """
    Append a message to the request object and return an HttpResponseRedirect to
    the appropriate URL for the arguments passed.

    The to argument could be:

        * A model: the model's `get_absolute_url()` function will be called.

        * A view name, possibly with arguments: `urls.reverse()` will be used
          to reverse-resolve the name.

        * A URL, which will be used as-is for the redirect location.

    Issues a temporary redirect by default; pass permanent=True to issue a
    permanent redirect.
    """
    extra_tags = f"temp-msg {msg_duration}-time-msg"
    getattr(messages, msg_type)(request, msg, extra_tags)
    return redirect(to, permanent=permanent)
