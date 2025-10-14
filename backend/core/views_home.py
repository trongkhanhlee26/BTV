from django.shortcuts import render, redirect
from core.decorators import judge_required

def home_view(request):
    # Trang chủ nền bk3.jpg + navbar
    return render(request, "home/index.html")

@judge_required
def manage_view(request):
    # Tạm thời dẫn người quản trị vào trang admin
    return redirect("/admin/")
