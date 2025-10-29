
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction
from django.db.models import Avg, Q
from core.decorators import judge_required
from .models import CuocThi, VongThi, BaiThi, ThiSinh, GiamKhao, PhieuChamDiem, ThiSinhCuocThi
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
    user = getattr(request, "user", None)
    if user and getattr(user, "email", None):
        gk = GiamKhao.objects.filter(email__iexact=user.email).first()
        if gk:
            return gk
    gk = _session_judge(request)
    return gk or GiamKhao.objects.first()


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
        
        for bt in (
            BaiThi.objects
            .filter(vongThi=vt)
            .order_by("id")
            .prefetch_related("time_rules", "template_sections__items")
        ):
            if _is_time(bt):
                rules = list(bt.time_rules.all()) if hasattr(bt, "time_rules") else []
                this_max = max([r.score for r in rules], default=0)
                b_type = "TIME"
                rules_payload = [{"s": r.start_seconds, "e": r.end_seconds, "score": r.score} for r in rules]
                rules_json = json.dumps(rules_payload, ensure_ascii=False)
            else:
                # TEMPLATE: tổng điểm = tổng item.max_score
                if _is_template(bt):
                    this_max = sum(
                        i.max_score
                        for s in bt.template_sections.all()
                        for i in s.items.all()
                    )
                    b_type = "TEMPLATE"
                else:  # POINTS
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
    # Nếu model lưu dạng số: 0=POINTS, 1=TEMPLATE, 2=TIME (bạn có thể đổi nếu mapping khác)
    if s in {"TIME", "2"}:
        return "TIME"
    if s in {"TEMPLATE", "1"}:
        return "TEMPLATE"
    return "POINTS"

def _is_template(bt) -> bool:
    return _score_type(bt) == "TEMPLATE"


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

def _resolve_thi_sinh_from_query(q: str):
    if not q:
        return None
    raw = q.strip()
    # Nếu người dùng chọn từ suggestion kiểu "TS001 — Nguyễn Văn A"
    if "—" in raw:
        maybe_code = raw.split("—", 1)[0].strip()
        ts = ThiSinh.objects.filter(maNV__iexact=maybe_code).first()
        if ts:
            return ts
    # Thử mã NV (tách token đầu)
    token = raw.split()[0]
    ts = ThiSinh.objects.filter(maNV__iexact=token).first()
    if ts:
        return ts
    # Cuối cùng thử khớp tên (exact trước)
    ts = ThiSinh.objects.filter(hoTen__iexact=raw).first()
    if ts:
        return ts
    # Cho “tên chứa” để tăng độ linh hoạt (lấy người đầu)
    return ThiSinh.objects.filter(hoTen__icontains=raw).order_by("maNV").first()



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

        bai_qs = (
            BaiThi.objects
            .filter(vongThi__cuocThi=ct)
            .prefetch_related("time_rules", "template_sections__items")
        )
        bai_map = {b.id: b for b in bai_qs}

        def _tpl_max(b):
            return sum(i.max_score for s in b.template_sections.all() for i in s.items.all())

        limit_map = {}
        for b in bai_qs:
            if _is_template(b):
                limit_map[b.id] = _tpl_max(b)
            elif _is_points(b):
                limit_map[b.id] = b.cachChamDiem
            else:  # TIME
                limit_map[b.id] = 0



        created = updated = 0
        errors = []
        saved_scores = {}  # {bt_id: điểm_đã_lưu}

        force = bool(payload.get("force"))
        incoming_ids = set()

        incoming_ids.update(int(k) for k in (scores or {}).keys() if str(k).isdigit())
        incoming_ids.update(int(k) for k in (done or {}).keys()   if str(k).isdigit())
        incoming_ids.update(int(k) for k in (times or {}).keys()  if str(k).isdigit())

        if incoming_ids:
            existed_qs = PhieuChamDiem.objects.filter(
                thiSinh=thi_sinh, baiThi_id__in=list(incoming_ids)
            ).values_list("baiThi__ma", flat=True)
            existed_codes = list(existed_qs)

            if existed_codes and not force:
                return JsonResponse({
                    "ok": False,
                    "code": "already_scored",
                    "message": "Thí sinh này đã được chấm điểm. Bạn có chắc chắn muốn chấm lại không?",
                    "existed_tests": existed_codes,
                }, status=409)


        with transaction.atomic():
            # 1) POINTS
            for s_id, raw in scores.items():
                try:
                    btid = int(s_id)
                except ValueError:
                    continue
                bt = bai_map.get(btid)
                # Cho phép nhập điểm cho cả POINTS và TEMPLATE (điểm tổng)
                if not bt or not (_is_points(bt) or _is_template(bt)):
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
        if errors:
            return JsonResponse({
                "ok": False,
                "message": f"Điểm số không hợp lệ ở {len(errors)} mục.",
                "errors": errors,
                "saved_scores": saved_scores,
            }, status=400)
        else:
            return JsonResponse({
                "ok": True,
                "message": f"Đã lưu điểm số thí sinh.",
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
    vt_param = request.GET.get("vt")
    bt_param = request.GET.get("bt")


    # AJAX gợi ý: chỉ trả JSON {maNV, hoTen}; bắt buộc phải chọn Cuộc thi đang bật
    if request.GET.get("ajax") in ("suggest", "1"):
        query = (request.GET.get("q") or "").strip()
        if not query:
            return JsonResponse([], safe=False)

        ct_id = request.GET.get("ct")
        ct = CuocThi.objects.filter(trangThai=True, id=ct_id).first()
        if not ct:
            # Chưa chọn CT hoặc CT không hợp lệ/không bật -> không gợi ý
            return JsonResponse([], safe=False)

        qs = (
            ThiSinh.objects
            .filter(cuocThi=ct)
            .filter(Q(maNV__icontains=query) | Q(hoTen__icontains=query))
            .order_by("maNV")
            .values("maNV", "hoTen")[:20]
        )
        return JsonResponse(list(qs), safe=False)




    # gợi ý thí sinh (server-render) — lọc theo CT đang bật nếu có ct_param
    suggestions = []
    if query:
        ct_for_suggest = CuocThi.objects.filter(trangThai=True, id=ct_param).first() if ct_param else None
        base_qs = ThiSinh.objects.all()
        if ct_for_suggest:
            base_qs = base_qs.filter(cuocThi=ct_for_suggest)  # ← lọc theo mact ở ThiSinh
        suggestions = list(
            base_qs.filter(
                Q(maNV__icontains=query) | Q(hoTen__icontains=query)
            ).order_by("maNV").values("maNV", "hoTen")[:20]
        )




    selected_ts = None
    if selected_code:
        selected_ts = ThiSinh.objects.filter(
            Q(maNV__iexact=selected_code) | Q(hoTen__iexact=selected_code)
        ).first()
    elif query:
        # Người dùng bấm Tìm với ô textfield "q"
        selected_ts = _resolve_thi_sinh_from_query(query)

    # Chỉ lấy danh sách CT đang bật...
    cuoc_this_active = CuocThi.objects.filter(trangThai=True).order_by("-id")
    ct = cuoc_this_active.filter(id=ct_param).first() if ct_param else None

   # ✅ Nếu thí sinh không thuộc cuộc thi đang chọn → bỏ chọn
    if ct and selected_ts:

        if not ThiSinhCuocThi.objects.filter(thiSinh=selected_ts, cuocThi=ct).exists():
            selected_ts = None
    # === NEW: cung cấp danh sách Vòng thi theo CT, và Bài thi theo Vòng ===
    rounds = []
    tests = []
    selected_vt = None
    selected_bt = None

    if ct:
        rounds = list(VongThi.objects.filter(cuocThi=ct).order_by("id").values("id", "tenVongThi"))
        if vt_param:
            selected_vt = VongThi.objects.filter(cuocThi=ct, id=vt_param).first()
            if selected_vt:
                tests = list(BaiThi.objects.filter(vongThi=selected_vt).order_by("id").values("id", "ma", "tenBaiThi"))
                if bt_param:
                    selected_bt = BaiThi.objects.filter(vongThi=selected_vt, id=bt_param).first()


    structure, total_max = _load_form_data(selected_ts, ct, request)
    # === NEW: lọc structure theo vòng/bài người dùng chọn
    if selected_vt:
        structure = [blk for blk in structure if getattr(blk.get("vong"), "id", None) == selected_vt.id]

    if selected_bt:
        new_structure = []
        for blk in structure:
            filtered = [b for b in blk.get("bai_list", []) if b.get("id") == selected_bt.id]
            if filtered:
                new_structure.append({"vong": blk.get("vong"), "bai_list": filtered})
        structure = new_structure

    # Tính lại tổng tối đa cho đúng phần đang hiển thị
    total_max = sum(b.get("max", 0) for blk in structure for b in blk.get("bai_list", []))

    # --- AJAX: meta cho dropdown động ---
    if request.GET.get("ajax") == "meta":
        ct_id = request.GET.get("ct")
        vt_id = request.GET.get("vt")
        data = {"rounds": [], "tests": []}

        if ct_id:
            ct_obj = CuocThi.objects.filter(trangThai=True, id=ct_id).first()
            if ct_obj:
                data["rounds"] = list(
                    VongThi.objects.filter(cuocThi=ct_obj)
                    .order_by("id")
                    .values("id", "tenVongThi")
                )
                if vt_id:
                    vt_obj = VongThi.objects.filter(cuocThi=ct_obj, id=vt_id).first()
                    if vt_obj:
                        data["tests"] = list(
                            BaiThi.objects.filter(vongThi=vt_obj)
                            .order_by("id")
                            .values("id", "ma", "tenBaiThi")
                        )
        return JsonResponse(data)




    return render(request, "score/index.html", {
        "ct": ct,
        "selected_ct_id": int(ct_param) if ct_param else None,
        "structure": structure,
        "total_max": total_max,
        "query": query,
        "suggestions": suggestions,
        "selected_ts": selected_ts,
        # chỉ hiển thị các cuộc thi đang bật
        "competitions": list(
            CuocThi.objects.filter(trangThai=True).order_by("-id")
            .values("id","ma","tenCuocThi","trangThai")
        ),
        # NEW: dữ liệu cho dropdown phụ thuộc
        "rounds": rounds,
        "tests": tests,
        "selected_vt_id": selected_vt.id if selected_vt else None,
        "selected_bt_id": selected_bt.id if selected_bt else None,
    })


    
@judge_required
@require_http_methods(["GET", "POST"])
def score_template_api(request, btid: int):
    bt = get_object_or_404(BaiThi.objects.prefetch_related("template_sections__items"), pk=btid)
    if str(bt.phuongThucCham).upper() != "TEMPLATE":
        return JsonResponse({"ok": False, "message": "Bài thi này không phải chấm theo mẫu."}, status=400)

    if request.method == "GET":
        try:
            # kiểm tra loại bài là TEMPLATE
            if not _is_template(bt):
                return JsonResponse({"ok": False, "message": "Bài thi này không phải chấm theo mẫu."}, status=400)

            sections = []
            total_max = 0

            # Lấy danh sách section theo 2 cách để tránh lệ thuộc related_name
            try:
                sec_qs = bt.template_sections.all().order_by("stt", "id")
            except Exception:
                try:
                    from .models import BaiThiTemplateSection
                    sec_qs = BaiThiTemplateSection.objects.filter(baiThi=bt).order_by("stt", "id")
                except Exception:
                    return JsonResponse({"ok": False, "message": "Không tìm thấy quan hệ sections cho bài thi này."}, status=500)

            for s in sec_qs:
                # Lấy danh sách item theo 2 cách (an toàn với related_name)
                try:
                    item_qs = s.items.all().order_by("stt", "id")
                except Exception:
                    try:
                        from .models import BaiThiTemplateItem
                        item_qs = BaiThiTemplateItem.objects.filter(section=s).order_by("stt", "id")
                    except Exception:
                        return JsonResponse({"ok": False, "message": f"Không tìm thấy items cho section {getattr(s,'id','?')}."}, status=500)

                items = []
                for i in item_qs:
                    items.append({
                        "id": i.id,
                        "stt": getattr(i, "stt", None),
                        "content": getattr(i, "content", ""),
                        "max": int(getattr(i, "max_score", 0) or 0),
                        "note": getattr(i, "note", "") or "",
                    })
                    total_max += int(getattr(i, "max_score", 0) or 0)

                sections.append({
                    "id": s.id,
                    "stt": getattr(s, "stt", None),
                    "title": getattr(s, "title", ""),
                    "note": getattr(s, "note", "") or "",
                    "items": items,
                })

            return JsonResponse({
                "ok": True,
                "bt": {"id": bt.id, "code": bt.ma, "name": bt.tenBaiThi},
                "total_max": total_max,
                "sections": sections,
            })

        except Exception as e:
            # tránh 500 trả HTML → trả JSON để frontend hiển thị rõ lỗi
            return JsonResponse({"ok": False, "message": f"Server error: {e.__class__.__name__}: {e}"}, status=500)


    # POST: nhận điểm từng item, tính tổng và lưu vào Phiếu chấm (mức tổng)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    ts_code = (payload.get("thiSinh") or "").strip()
    ct_id   = payload.get("ct_id")
    item_scores = payload.get("items") or {}   # {"<item_id>": <điểm số>}

    # 1) Ưu tiên Mã NV
    thi_sinh = ThiSinh.objects.filter(maNV__iexact=ts_code).first()

    # 2) Nếu không có, cho phép gõ tên để lưu
    if not thi_sinh:
        # Ưu tiên trong cuộc thi hiện tại (nếu có)
        by_name_qs = ThiSinh.objects.filter(hoTen__iexact=ts_code)
        if ct_id:
            ct_obj = _pick_competition(int(ct_id))
            if ct_obj:
                by_name_qs = by_name_qs.filter(phieuchamdiem__cuocThi=ct_obj).distinct() or by_name_qs
        thi_sinh = by_name_qs.first()

    if not thi_sinh:
        return JsonResponse({"ok": False, "message": "Không tìm thấy thí sinh theo tên đã nhập."}, status=400)


    # Chỉ chấm vào CT đang bật
    ct = CuocThi.objects.filter(trangThai=True, id=ct_id).first() if ct_id else _active_competition()
    if not ct:
        return JsonResponse({"ok": False, "message": "Chưa có cuộc thi hợp lệ (chỉ chấm vào cuộc thi đang bật)."}, status=400)


    judge = _current_judge(request)
    if not judge:
        return JsonResponse({"ok": False, "message": "Bạn chưa đăng nhập giám khảo."}, status=401)

    # Map max cho từng item
    max_map = {}
    for s in bt.template_sections.all():
        for i in s.items.all():
            max_map[i.id] = int(i.max_score or 0)

    # Chuẩn hóa & kẹp điểm trong khoảng 0..max
    total = 0
    normalized = {}
    for raw_id, raw_val in item_scores.items():
        try:
            iid = int(raw_id)
        except Exception:
            continue
        if iid not in max_map:
            continue
        try:
            val = int(float(raw_val))
        except Exception:
            val = 0
        val = max(0, min(val, max_map[iid]))
        normalized[iid] = val
        total += val

    # Lưu tổng vào Phiếu chấm (chi tiết item nếu cần sẽ bổ sung model riêng sau)
    with transaction.atomic():
        obj, created = PhieuChamDiem.objects.update_or_create(
            thiSinh=thi_sinh, giamKhao=judge, baiThi=bt,
            defaults=dict(cuocThi=ct, vongThi=bt.vongThi, diem=total)
        )

    return JsonResponse({
        "ok": True,
        "saved_total": total,
        "message": f"Đã lưu {total} điểm cho {bt.ma} (TEMPLATE).",
    })