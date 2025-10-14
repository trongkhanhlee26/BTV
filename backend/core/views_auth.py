from django.shortcuts import render, redirect
from django.urls import reverse
from core.models import GiamKhao

def login_view(request):
    error = None
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        next_url = request.POST.get("next") or "/"
        judge = GiamKhao.objects.filter(email__iexact=email).first()
        if judge:
            # lưu khóa chính (maNV) vào session
            request.session["judge_pk"] = judge.pk
            request.session["judge_email"] = judge.email or email
            return redirect(next_url)
        error = "Email không nằm trong danh sách Giám khảo."

    return render(request, "auth/login.html", {
        "next": request.GET.get("next") or "/",
        "error": error,
    })

def logout_view(request):
    request.session.pop("judge_pk", None)
    request.session.pop("judge_email", None)
    return redirect(reverse("login"))
