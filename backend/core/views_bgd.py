# core/views_bgd.py
from io import BytesIO
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db.models import Q
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from django.utils import timezone
from django.http import QueryDict

from .models import BanGiamDoc, CuocThi
from .views_score import score_view  # tái dùng view chấm hiện có

# --- 1) Trang QR: hiển thị lần lượt từng BGD (1 mã/lần), có nút chuyển & lưu ảnh ---
def bgd_qr_index(request):
    items = list(BanGiamDoc.objects.order_by("maBGD").values("maBGD", "ten", "token"))
    # build URL đích khi quét
    def _go_url(tok):
        return request.build_absolute_uri(reverse("bgd-go", args=[tok]))
    for it in items:
        it["url"] = _go_url(it["token"])
    return render(request, "bgd/qr.html", {"items": items})

# --- 2) Ảnh QR PNG cho 1 token ---
def bgd_qr_png(request, token: str):
    # dùng thư viện qrcode để tạo ảnh (pip install qrcode[pil])
    try:
        import qrcode
    except Exception:
        raise Http404("Thiếu thư viện qrcode. Hãy cài: pip install qrcode[pil]")
    bgd = BanGiamDoc.objects.filter(token=token).only("token").first()
    if not bgd:
        raise Http404("Token không hợp lệ")
    data = request.build_absolute_uri(reverse("bgd-go", args=[bgd.token]))
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(data); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type="image/png")

# --- 3) Khi quét QR: set session & ép cuộc thi "Chung Kết", rồi chuyển qua trang chấm ---
def bgd_go(request, token: str):
    bgd = BanGiamDoc.objects.filter(token=token).first()
    if not bgd:
        raise Http404("Token không hợp lệ")

    # tìm cuộc thi "Chung Kết" (không phân biệt hoa/thường, bỏ dấu)
    # Bạn có thể chỉnh điều kiện này nếu muốn khớp chính xác tuyệt đối.
    chung_ket = CuocThi.objects.filter(tenCuocThi__iexact="Chung Kết").first()
    if not chung_ket:
        # fallback: thử "Chung Ket"
        chung_ket = CuocThi.objects.filter(tenCuocThi__iexact="Chung Ket").first()
    if not chung_ket:
        raise Http404("Chưa tạo cuộc thi 'Chung Kết'")

    # Ghi session để khóa CT khi chấm
    request.session["bgd_token"] = token
    request.session["bgd_ct_id"] = chung_ket.id
    request.session["bgd_ct_name"] = chung_ket.tenCuocThi
    request.session.modified = True

    return redirect("score-bgd")

# --- 4) View chấm cho BGD: khóa vào "Chung Kết", tái dùng score_view ---
def score_bgd_view(request):
    ct_id = request.session.get("bgd_ct_id")
    if not ct_id:
        # chưa đi qua QR -> quay về trang QR
        return redirect("bgd-qr")

    # ép querystring ct=<id> để score_view hiểu (không phá request.GET gốc)
    # (nếu score_view của bạn không nhận "ct", hãy sửa đúng theo tham số nó đang dùng)
    mutable_get = request.GET.copy()
    mutable_get["ct"] = str(ct_id)
    request.GET = mutable_get

    # Optionally: gắn cờ vào request để score_view (nếu bạn muốn khóa thêm)
    # request.bgd_mode = True

    # gọi view gốc
    return score_view(request)
