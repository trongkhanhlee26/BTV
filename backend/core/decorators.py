from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse

def judge_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        # yêu cầu cả pk và email trong session
        if not request.session.get("judge_pk") or not request.session.get("judge_email"):
            login_url = reverse("login")
            return redirect(f"{login_url}?next={request.path}")
        return view_func(request, *args, **kwargs)
    return _wrapped
