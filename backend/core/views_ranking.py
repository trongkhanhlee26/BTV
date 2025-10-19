from django.shortcuts import render
from django.db.models import Avg
from .models import CuocThi, VongThi, BaiThi, ThiSinh, PhieuChamDiem

# Chuẩn hoá loại chấm để không phụ thuộc chữ hoa/thường/enum
def _score_type(bt) -> str:
    v = getattr(bt, "phuongThucCham", None)
    if v is None:
        return "POINTS"
    s = str(v).strip().upper()
    if s in {"TIME", "2"}:
        return "TIME"
    return "POINTS"

def ranking_view(request):
    # 1) Chọn cuộc thi (chỉ lấy cuộc thi đang bật)
    ct_id = request.GET.get("ct")
    cuoc_this = CuocThi.objects.filter(trangThai=True).order_by("-id")  # chỉ ACTIVE

    selected_ct = None
    if ct_id:
        # Nếu ct_id không phải ACTIVE thì bỏ qua
        selected_ct = cuoc_this.filter(id=ct_id).first()
    # fallback: lấy cái ACTIVE đầu tiên
    if not selected_ct:
        selected_ct = cuoc_this.first()


    if not selected_ct:
        return render(request, "ranking/index.html", {
            "cuoc_this": cuoc_this,
            "selected_ct": None,
            "columns": [],
            "rows": [],
            "total_max": 0,
            "title": "Xếp hạng theo Cuộc thi",
        })

    # 2) Lấy tất cả bài trong cuộc thi (prefetch rule để tính Max cho TIME)
    vt_ids = VongThi.objects.filter(cuocThi=selected_ct).values_list("id", flat=True)
    bai_list = list(
        BaiThi.objects
        .filter(vongThi_id__in=vt_ids)
        .select_related("vongThi")
        .prefetch_related("time_rules")
        .order_by("vongThi_id", "id")
    )

    columns = []
    for b in bai_list:
        if _score_type(b) == "TIME":
            rules = list(b.time_rules.all()) if hasattr(b, "time_rules") else []
            b_max = max([r.score for r in rules], default=0)
        else:
            b_max = b.cachChamDiem

        columns.append({
            "id": b.id,
            "code": b.ma,
            "title": f"{b.vongThi.tenVongThi} – {b.tenBaiThi}",
            "max": b_max,
        })

    total_max = sum(c["max"] for c in columns)

    # 3) Lấy điểm trung bình mỗi thí sinh – bài thi
    scores_qs = (
        PhieuChamDiem.objects
        .filter(cuocThi=selected_ct, baiThi_id__in=[b["id"] for b in columns])
        .values("thiSinh__maNV", "baiThi_id")
        .annotate(avg=Avg("diem"))
    )
    score_map = {(r["thiSinh__maNV"], r["baiThi_id"]): float(r["avg"]) for r in scores_qs}

    # 4) Chỉ lấy thí sinh có mact đúng với cuộc thi đã chọn
    ts_qs = (
        ThiSinh.objects
        .filter(cuocThi=selected_ct)   # <-- dựa theo mact ở bảng ThiSinh
        .order_by("maNV")
    )


    rows = []
    for ts in ts_qs:
        row_scores, total = [], 0.0
        for col in columns:
            val = score_map.get((ts.maNV, col["id"]), 0.0)
            row_scores.append(val)
            total += val
        rows.append({
            "maNV": ts.maNV,
            "hoTen": ts.hoTen,
            "donVi": ts.donVi or "",
            "scores": row_scores,
            "total": total,
        })


    # 5) Sắp xếp theo tổng giảm dần
    rows.sort(key=lambda r: (-r["total"], r["maNV"]))

    return render(request, "ranking/index.html", {
        "cuoc_this": cuoc_this,
        "selected_ct": selected_ct,
        "columns": columns,
        "rows": rows,
        "total_max": total_max,
        "title": f"Xếp hạng — {selected_ct.ma} · {selected_ct.tenCuocThi}",
    })