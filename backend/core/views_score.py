
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction
from django.db.models import Avg, Q
from core.decorators import judge_required
from .models import CuocThi, VongThi, BaiThi, ThiSinh, GiamKhao, PhieuChamDiem
import json
def _pick_competition(preferred_id: int | None):
    """
    Chọn cuộc thi dùng cho chấm điểm:
    1) Nếu preferred_id được truyền và tồn tại → dùng.
    2) Nếu có cuộc thi đang bật và có ít nhất 1 bài → dùng.
    3) Nếu không, lấy cuộc thi gần nhất có ít nhất 1 bài.
    4) Nếu vẫn không có → None.
    """
    qs = CuocThi.objects.all().order_by("-trangThai", "-id")
    if preferred_id:
        ct = qs.filter(id=preferred_id).first()
        if ct:
            return ct
    active = qs.filter(trangThai=True).first()
    if active and BaiThi.objects.filter(vongThi__cuocThi=active).exists():
        return active
    fallback = qs.filter(vong_thi__bai_thi__isnull=False).distinct().first()
    return fallback
def _session_judge(request):
    """Lấy giám khảo từ session (ưu tiên)."""
    jid = request.session.get("judge_id")
    if jid:
        return GiamKhao.objects.filter(id=jid).first()
    return None

def _current_judge(request):
    """
    Xác định giám khảo hiện tại:
   - Nếu có trong session → dùng.
   - Nếu không tìm thấy → None (để view chặn truy cập)
    """
    user = getattr(request, "user", None)
    if user and getattr(user, "email", None):
        gk = GiamKhao.objects.filter(email__iexact=user.email).first()
        if gk:
            return gk
    return GiamKhao.objects.first()
    gk = _session_judge(request)
    return gk

def _active_competition():
    """
    Lấy 'Cuộc thi đang bật' ưu tiên trangThai=True; nếu không có, trả None.
    """
    return CuocThi.objects.filter(trangThai=True).order_by("-id").first()

# after
def _load_form_data(selected_ts, ct, request):
    """
    Trả về (structure, total_max) để render form chấm điểm.
    structure: [{vong, bai_list:[{id, code, ten, max, type, current}]}]
    total_max: int
    """
    if not ct:
        return [], 0

    vongs = list(VongThi.objects.filter(cuocThi=ct).order_by("id"))
    bai_by_vong = []
    total_max = 0

    # điểm hiện có của thí sinh (ưu tiên GK hiện tại)
    score_map = {}
    if selected_ts:
        judge = _current_judge(request)
        qs = PhieuChamDiem.objects.filter(thiSinh=selected_ts, cuocThi=ct)
        score_map_avg = {
            r["baiThi_id"]: float(r["avg"])
            for r in qs.values("baiThi_id").annotate(avg=Avg("diem"))
        }
        score_map_gk = {
            p.baiThi_id: p.diem
            for p in qs
            if judge and p.giamKhao_id == getattr(judge, "pk", None)
        }
        score_map.update(score_map_avg)
        score_map.update(score_map_gk)

    for vt in vongs:
        bais = []
        for bt in BaiThi.objects.filter(vongThi=vt).order_by("id").prefetch_related("time_rules"):
            if _is_time(bt):
                rules = list(bt.time_rules.all()) if hasattr(bt, "time_rules") else []
                this_max = max([r.score for r in rules], default=0)
                b_type = "TIME"
                rules_payload = [{"s": r.start_seconds, "e": r.end_seconds, "score": r.score} for r in rules]
                rules_json = json.dumps(rules_payload, ensure_ascii=False)
            else:
                this_max = bt.cachChamDiem
                b_type = "POINTS"
                rules_json = "[]"

            # ➕ QUAN TRỌNG: cộng vào tổng tối đa
            total_max += this_max

            bais.append({
                "id": bt.id,
                "code": bt.ma,
                "ten": f"{vt.tenVongThi} – {bt.tenBaiThi}",
                "max": this_max,
                "type": b_type,
                "rules": rules_json,
                "current": score_map.get(bt.id, 0.0) if selected_ts else None,
            })
        bai_by_vong.append({"vong": vt, "bai_list": bais})


    # 🔒 luôn trả về tuple
    return bai_by_vong, total_max

# ==== Helpers xác định loại chấm ====
def _score_type(bt) -> str:
    v = getattr(bt, "phuongThucCham", None)
    if v is None:
        return "POINTS"
    s = str(v).strip().upper()
    # chấp nhận cả enum dạng số
    if s in {"TIME", "2"}:
        return "TIME"
    return "POINTS"

def _is_time(bt) -> bool:
    return _score_type(bt) == "TIME"

def _is_points(bt) -> bool:
    return _score_type(bt) == "POINTS"

def _parse_seconds(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    if ":" in s:
        try:
            m, sec = s.split(":")
            return int(m)*60 + int(sec)
        except Exception:
            return None
    try:
        return int(float(s))
    except Exception:
        return None


@ensure_csrf_cookie
@judge_required
@require_http_methods(["GET", "POST"])
def score_view(request):
    # Xử lý AJAX lưu điểm (không reload)
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return HttpResponseBadRequest("Invalid JSON")

        ts_code = (payload.get("thiSinh") or "").strip()
        ct_id   = payload.get("ct_id")  # <-- thêm
        scores  = payload.get("scores") or {}
        done    = payload.get("done")   or {}
        times   = payload.get("times")  or {}

        thi_sinh = ThiSinh.objects.filter(Q(maNV__iexact=ts_code) | Q(hoTen__iexact=ts_code)).first()
        if not thi_sinh:
            return JsonResponse({"ok": False, "message": "Không tìm thấy thí sinh."}, status=400)

        # Ưu tiên ct_id người dùng đang chọn; nếu không có thì rơi về cuộc thi đang bật
        ct = _pick_competition(int(ct_id)) if ct_id else _active_competition()
        if not ct:
            return JsonResponse({"ok": False, "message": "Chưa có cuộc thi hợp lệ."}, status=400)

        judge = _current_judge(request)
        if not judge:
            return JsonResponse({"ok": False, "message": "Bạn chưa đăng nhập giám khảo."}, status=401)

        bai_qs  = BaiThi.objects.filter(vongThi__cuocThi=ct).prefetch_related("time_rules")
        bai_map = {b.id: b for b in bai_qs}
        limit_map = {b.id: b.cachChamDiem for b in bai_qs}

        created = updated = 0
        errors = []
        saved_scores = {}  # {bt_id: điểm_đã_lưu}

        with transaction.atomic():
            # 1) POINTS
            for s_id, raw in scores.items():
                try:
                    btid = int(s_id)
                except ValueError:
                    continue
                bt = bai_map.get(btid)
                if not bt or not _is_points(bt):
                    continue
                try:
                    diem = int(raw)
                except (TypeError, ValueError):
                    errors.append(f"Bài {bt.ma}: điểm không hợp lệ.")
                    continue
                maxp = limit_map.get(btid, 0)
                if diem < 0 or diem > maxp:
                    errors.append(f"Bài {bt.ma}: 0..{maxp}.")
                    continue

                obj, was_created = PhieuChamDiem.objects.update_or_create(
                    thiSinh=thi_sinh, giamKhao=judge, baiThi=bt,
                    defaults=dict(cuocThi=ct, vongThi=bt.vongThi, diem=diem)
                )
                created += int(was_created); updated += int(not was_created)
                saved_scores[btid] = diem

            # 2) TIME
            for bt in bai_qs:
                if not _is_time(bt):
                    continue
                btid = bt.id
                is_done = bool(done.get(str(btid)) or done.get(btid))
                if not is_done:
                    # Không hoàn thành → 0 điểm
                    obj, was_created = PhieuChamDiem.objects.update_or_create(
                        thiSinh=thi_sinh, giamKhao=judge, baiThi=bt,
                        defaults=dict(cuocThi=ct, vongThi=bt.vongThi, diem=0)
                    )
                    created += int(was_created); updated += int(not was_created)
                    saved_scores[btid] = 0
                    continue

                seconds = _parse_seconds(times.get(str(btid)) or times.get(btid))
                if seconds is None or seconds < 0:
                    errors.append(f"Bài {bt.ma}: thời gian không hợp lệ (mm:ss hoặc giây).")
                    # Không lưu khi tick nhưng thời gian sai
                    continue

                # map thời gian → điểm theo rule
                match = None
                for r in bt.time_rules.all():
                    if r.start_seconds <= seconds <= r.end_seconds:
                        match = r; break
                diem = int(getattr(match, "score", 0))

                obj, was_created = PhieuChamDiem.objects.update_or_create(
                    thiSinh=thi_sinh, giamKhao=judge, baiThi=bt,
                    defaults=dict(cuocThi=ct, vongThi=bt.vongThi, diem=diem)
                )
                created += int(was_created); updated += int(not was_created)
                saved_scores[btid] = diem

        return JsonResponse({
            "ok": True,
            "message": f"Đã lưu: mới {created}, cập nhật {updated}, lỗi {len(errors)}.",
            "errors": errors,
            "saved_scores": saved_scores,
            "debug": {
                "count_all": len(bai_qs),
                "count_points": sum(1 for b in bai_qs if _is_points(b)),
                "count_time": sum(1 for b in bai_qs if _is_time(b)),
            }
        })

    # GET: render trang
    query = (request.GET.get("q") or "").strip()
    selected_code = (request.GET.get("ts") or "").strip()
    ct_param = request.GET.get("ct")
    # gợi ý thí sinh theo q
    suggestions = []
    if query:
        suggestions = list(
            ThiSinh.objects.filter(
                Q(maNV__icontains=query) | Q(hoTen__icontains=query)
            ).order_by("maNV").values("maNV", "hoTen", "donVi")[:20]
        )

    selected_ts = None
    if selected_code:
        selected_ts = ThiSinh.objects.filter(Q(maNV__iexact=selected_code) | Q(hoTen__iexact=selected_code)).first()

    ct = _pick_competition(int(ct_param) if ct_param else None)
    structure, total_max = _load_form_data(selected_ts, ct, request)

    return render(request, "score/index.html", {
        "ct": ct,
        "selected_ct_id": ct.id if ct else None,  # NEW
        "structure": structure,
        "total_max": total_max,
        "query": query,
        "suggestions": suggestions,
        "selected_ts": selected_ts,
        "competitions": list(CuocThi.objects.all().order_by("-trangThai", "-id")
                            .values("id","ma","tenCuocThi","trangThai")),
 })
