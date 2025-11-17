from django.shortcuts import render
from django.db import transaction
from .models import CuocThi, CapThiDau, ThiSinhCapThiDau, BattleVote, GiamKhao
import unicodedata
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
import json


def _normalize(s: str) -> str:
    """
    Chuẩn hoá chuỗi để so khớp: bỏ dấu, lowercase, bỏ khoảng trắng thừa.
    'Chung Kết' -> 'chungket', 'CK' -> 'ck'
    """
    if not s:
        return ""
    # tách dấu rồi bỏ ký tự dấu
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower().strip().replace(" ", "")
    return s


def _find_chung_ket_competition():
    """
    Tìm cuộc thi 'Chung Kết' theo nhiều biến thể tên:
    - Có/không dấu: 'Chung Kết', 'Chung ket', 'chung ket', ...
    - Viết hoa/thường: 'CHUNG KET', ...
    - Viết tắt: 'CK', 'ck'
    Ưu tiên lọc Python-level để đảm bảo bỏ dấu/so khớp chắc chắn.
    """
    targets = {"chungket", "ck"}
    candidates = CuocThi.objects.all().order_by("-id")  # mới nhất trước
    for ct in candidates:
        if _normalize(ct.tenCuocThi) in targets:
            return ct
    return None


def _serialize_thisinh(qs):
    """
    Chuyển queryset ThiSinh thành list dict tối giản cho UI.
    """
    data = []
    for ts in qs:
        data.append({
            "maNV": ts.maNV,
            "hoTen": ts.hoTen,
            "chiNhanh": ts.chiNhanh or "",
            "nhom": ts.nhom or "",
            "donVi": ts.donVi or "",
            "email": ts.email or "",
        })
    return data


def _get_ck_thi_sinh():
    """
    Lấy danh sách thí sinh thuộc cuộc thi 'Chung Kết' (theo các biến thể tên).
    Nếu không thấy, trả về (None, []).
    """
    ct = _find_chung_ket_competition()
    if not ct:
        return None, []
    # ManyToMany: CuocThi ←→ ThiSinh thông qua through=ThiSinhCuocThi
    thi_sinh_qs = ct.thiSinhs.all().order_by("hoTen", "maNV")
    return ct, _serialize_thisinh(thi_sinh_qs)


def battle_view(request):
    # Trang index (trình chiếu): chỉ render, sau này JS có thể đọc cặp đấu từ API pairing_state
    return render(request, "battle/index.html")


def manage_battle_view(request):
    ct, thi_sinh = _get_ck_thi_sinh()

    used_ids = []
    if ct:
        used_ids = list(
            ThiSinhCapThiDau.objects.filter(pair__cuocThi=ct)
            .values_list("thiSinh__maNV", flat=True)
        )

    ctx = {
        "ck": ct,
        "contestants_json": json.dumps(thi_sinh, ensure_ascii=False),
        "used_ids_json": json.dumps(used_ids, ensure_ascii=False),
    }
    return render(request, "battle/manage.html", ctx)

# ===== API: đọc trạng thái cặp đấu hiện tại từ DB =====

def pairing_state(request):
    
    ct = _find_chung_ket_competition()
    if not ct:
        return JsonResponse({"pairs": []})

    pairs_qs = (
        CapThiDau.objects
        .filter(cuocThi=ct, active=True)
        .order_by("thuTuThiDau", "id")
        .prefetch_related("members__thiSinh")
    )

    result = []
    for pair in pairs_qs:
        left_members = []
        right_members = []

        for m in pair.members.all():
            item = {
                "maNV": m.thiSinh.maNV,
                "hoTen": m.thiSinh.hoTen,
                # ưu tiên image_url trên ThiSinhCapThiDau, nếu trống thì lấy từ thiSinh.hinhAnh (nếu có)
                "image_url": m.display_image_url,
            }
            if m.side == "L":
                left_members.append((m.slot or 0, item))
            else:
                right_members.append((m.slot or 0, item))

        # sort theo slot để sau này NvsN vẫn đúng thứ tự
        left_members = [item for _, item in sorted(left_members, key=lambda t: (t[0],))]
        right_members = [item for _, item in sorted(right_members, key=lambda t: (t[0],))]

        result.append({
            "id": pair.id,
            "order": pair.thuTuThiDau,
            "maCapDau": pair.maCapDau,
            "tenCapDau": pair.tenCapDau or "",
            "left": left_members,
            "right": right_members,
        })

    return JsonResponse({"pairs": result})



# ===== API: lưu cấu hình cặp đấu vào DB =====

@csrf_exempt
def save_pairing(request):
    """
    Nhận POST JSON: {"left": ["ma1",...], "right": ["ma2",...]}
    - Validate cân bằng, >0.
    - Validate thí sinh tồn tại và thuộc cuộc thi CK.
    - Không xoá cặp đấu cũ nữa, mà cộng dồn:
        + Tìm thuTuThiDau lớn nhất hiện tại, cặp mới nối tiếp phía sau.
        + Không cho 1 thí sinh xuất hiện trong 2 cặp khác nhau.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Method not allowed")

    # --- Parse JSON ---
    try:
        body = json.loads(request.body.decode("utf-8"))
        left = body.get("left", [])
        right = body.get("right", [])
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    if not isinstance(left, list) or not isinstance(right, list):
        return HttpResponseBadRequest("left/right must be array")

    if len(left) == 0 or len(right) == 0 or len(left) != len(right):
        return HttpResponseBadRequest("Hai bên phải có cùng số lượng (>0)")

    # --- Tìm cuộc thi Chung kết / CK ---
    ct = _find_chung_ket_competition()
    if not ct:
        return HttpResponseBadRequest("Không tìm thấy cuộc thi Chung Kết/CK")

    # --- Kiểm tra thí sinh có tồn tại và thuộc cuộc thi CK không ---
    all_ids = list(dict.fromkeys(left + right))  # unique + giữ thứ tự
    thi_sinh_qs = ct.thiSinhs.filter(maNV__in=all_ids)
    thi_sinh_map = {ts.maNV: ts for ts in thi_sinh_qs}

    missing = [ma for ma in all_ids if ma not in thi_sinh_map]
    if missing:
        return HttpResponseBadRequest(
            "Các mã nhân viên không hợp lệ hoặc không thuộc cuộc thi CK: "
            + ", ".join(missing)
        )

    # --- Không cho dùng lại thí sinh đã nằm trong cặp đấu khác ---
    used_ids = set(
        ThiSinhCapThiDau.objects
        .filter(pair__cuocThi=ct)
        .values_list("thiSinh__maNV", flat=True)
    )
    conflicts = [ma for ma in all_ids if ma in used_ids]
    if conflicts:
        return HttpResponseBadRequest(
            "Các mã nhân viên đã nằm trong một cặp đấu khác: "
            + ", ".join(conflicts)
        )

    # --- Lưu DB trong 1 transaction ---
    from django.db.models import Max

    with transaction.atomic():
        # Tìm thứ tự hiện tại lớn nhất, cặp mới nối tiếp
        max_order = (
            CapThiDau.objects
            .filter(cuocThi=ct)
            .aggregate(m=Max("thuTuThiDau"))
            .get("m") or 0
        )

        # Tạo cặp đấu 1vs1 theo thứ tự index
        for idx, (ma_left, ma_right) in enumerate(zip(left, right), start=1):
            pair = CapThiDau.objects.create(
                cuocThi=ct,
                thuTuThiDau=max_order + idx,
            )

            # Bên trái
            ThiSinhCapThiDau.objects.create(
                pair=pair,
                thiSinh=thi_sinh_map[ma_left],
                side="L",
                slot=1,
            )

            # Bên phải
            ThiSinhCapThiDau.objects.create(
                pair=pair,
                thiSinh=thi_sinh_map[ma_right],
                side="R",
                slot=1,
            )

    payload = {
        "left": left,
        "right": right,
        "by": getattr(request.user, "username", "admin")
        if request.user.is_authenticated else "admin",
    }
    return JsonResponse({"ok": True, "data": payload})

def _get_current_judge(user):
    """
    Tìm giám khảo tương ứng với tài khoản đang đăng nhập.
    Ưu tiên:
      1) maNV ~ username (không phân biệt hoa/thường, bỏ khoảng trắng dư)
      2) email ~ email (không phân biệt hoa/thường, bỏ khoảng trắng dư)
    Trả về instance GiamKhao hoặc None.
    """
    if not getattr(user, "is_authenticated", False):
        return None

    username = (getattr(user, "username", "") or "").strip()
    email = (getattr(user, "email", "") or "").strip()

    qs = GiamKhao.objects.all()

    # 1) Map theo maNV = username (không phân biệt hoa/thường)
    if username:
        jk = qs.filter(maNV__iexact=username).first()
        if jk:
            return jk

    # 2) Map theo email
    if email:
        jk = qs.filter(email__iexact=email).first()
        if jk:
            return jk

    return None


@csrf_exempt
def submit_vote(request):
    """
    API lưu vote vào BattleVote theo tài khoản GIÁM KHẢO đang đăng nhập.
    Body JSON: {
      "pair_id": 123,
      "maNV": "NV001",
      "side": "L" hoặc "R",
      "stars": 1..5,
      "note": "ghi chú"
    }
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Method not allowed")

    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "Bạn chưa đăng nhập."}, status=401)

    # Parse JSON
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    pair_id = body.get("pair_id")
    maNV = body.get("maNV")
    side = body.get("side")
    stars = body.get("stars")
    note = (body.get("note") or "").strip()

    # Validate cơ bản
    if not pair_id or not maNV or side not in ("L", "R"):
        return HttpResponseBadRequest("Thiếu pair_id / maNV / side")

    try:
        stars = int(stars)
    except Exception:
        return HttpResponseBadRequest("stars phải là số nguyên")

    if stars < 1 or stars > 5:
        return HttpResponseBadRequest("stars phải từ 1 đến 5")

    # Tìm giám khảo tương ứng với tài khoản đang đăng nhập
    # Ưu tiên map theo maNV = username, nếu không thấy thì fallback theo email
    judge = _get_current_judge(request.user)

    if not judge:
        return JsonResponse(
            {"ok": False, "error": "Không tìm thấy thông tin giám khảo cho tài khoản hiện tại."},
            status=403
        )

    # Tìm entry (ThiSinhCapThiDau) theo pair + thí sinh + side
    try:
        entry = ThiSinhCapThiDau.objects.select_related("thiSinh", "pair").get(
            pair_id=pair_id,
            thiSinh__maNV=maNV,
            side=side,
        )
    except ThiSinhCapThiDau.DoesNotExist:
        return JsonResponse(
            {"ok": False, "error": "Không tìm thấy thí sinh trong cặp đấu tương ứng."},
            status=404
        )

    vote, created = BattleVote.objects.update_or_create(
        giamKhao=judge,
        entry=entry,
        defaults={
            "stars": stars,
            "note": note,
        },
    )

    # Tính lại tổng và trung bình sau khi vote
    total_votes = entry.total_votes
    avg_stars = entry.avg_stars

    return JsonResponse({
        "ok": True,
        "created": created,
        "stars": vote.stars,
        "note": vote.note,
        "total_votes": total_votes,
        "avg_stars": avg_stars,
        "entry": {
            "pair_id": entry.pair_id,
            "maNV": entry.thiSinh.maNV,
            "side": entry.side,
        },
        "giamKhao": {
            "maNV": judge.maNV,
            "hoTen": judge.hoTen,
        }
    })

