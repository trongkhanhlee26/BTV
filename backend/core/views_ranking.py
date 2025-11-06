from django.shortcuts import render
from django.db.models import Avg
from .models import CuocThi, VongThi, BaiThi, ThiSinh, PhieuChamDiem
from django.db.models import Q

def _score_type(bt) -> str:
    v = getattr(bt, "phuongThucCham", None)
    if v is None:
        return "POINTS"
    s = str(v).strip().upper()
    if s in {"TIME", "2"}:
        return "TIME"
    return "POINTS"

def ranking_view(request):
    ct_id = request.GET.get("ct")
    cuoc_this = CuocThi.objects.filter(trangThai=True).order_by("-id")

    # Nếu không có cuộc thi active -> trả trang rỗng
    if not cuoc_this.exists():
        return render(request, "ranking/index.html", {
            "cuoc_this": cuoc_this, "selected_ct": None,
            "groups": [], "rows": [], "total_max": 0,
            "title": "Xếp hạng theo Cuộc thi",
        })

    # Có cuộc thi active: ưu tiên ct theo tham số; nếu không thấy thì fallback ct đầu tiên
    selected_ct = cuoc_this.filter(id=ct_id).first() if ct_id else None
    if selected_ct is None:
        selected_ct = cuoc_this.first()

    # 2) Lấy các vòng + bài của cuộc thi
    vongs = list(VongThi.objects.filter(cuocThi=selected_ct).order_by("id"))
    bai_list = (
        BaiThi.objects.filter(vongThi__in=vongs)
        .select_related("vongThi").prefetch_related("time_rules")
        .order_by("vongThi_id", "id")
    )

    # Gom theo vòng
    groups = []
    group_index_by_vong = {}
    running_test_index = 0
    total_max = 0

    for vt in vongs:
        tests = []
        g_max = 0
        for b in [x for x in bai_list if x.vongThi_id == vt.id]:
            if _score_type(b) == "TIME":
                rules = list(getattr(b, "time_rules", []).all()) if hasattr(b, "time_rules") else []
                b_max = max([r.score for r in rules], default=0)
            else:
                b_max = b.cachChamDiem
            tests.append({
                "id": b.id,
                "code": b.ma,
                "title": b.tenBaiThi,
                "max": b_max,
                "col_index": running_test_index,  # vị trí cột (tính từ 0 trong phần bài thi)
            })
            running_test_index += 1
            g_max += (b_max or 0)

        if tests:
            group_index_by_vong[vt.id] = len(groups)
            groups.append({
                "vong_id": vt.id,
                "vong_name": vt.tenVongThi,
                "tests": tests,
                "max": g_max,
            })
            total_max += g_max

    # 3) Map điểm (thiSinh.maNV, baiThi_id) -> avg
    all_test_ids = [t["id"] for g in groups for t in g["tests"]]
    score_qs = (
        PhieuChamDiem.objects
        .filter(cuocThi=selected_ct, baiThi_id__in=all_test_ids)
        .values("thiSinh__maNV", "baiThi_id")
        .annotate(avg=Avg("diem"))
    )
    score_map = {(r["thiSinh__maNV"], r["baiThi_id"]): float(r["avg"]) for r in score_qs}

    # 4) Lấy thí sinh thuộc cuộc thi (m2m + có phiếu chấm)
    ts_m2m = ThiSinh.objects.filter(cuocThi=selected_ct)
    ts_scored = ThiSinh.objects.filter(phieuchamdiem__cuocThi=selected_ct)
    ts_qs = (
        ThiSinh.objects
        .filter(Q(pk__in=ts_m2m.values("pk")) | Q(pk__in=ts_scored.values("pk")))
        .distinct().order_by("maNV")
    )

    rows = []
    for ts in ts_qs:
        # điểm từng bài (flatten theo thứ tự groups/tests)
        flat_scores = []
        group_totals = []
        total_sum = 0.0

        for g in groups:
            g_sum = 0.0
            for t in g["tests"]:
                val = score_map.get((ts.maNV, t["id"]), 0.0)
                flat_scores.append(val)
                g_sum += val
            group_totals.append(g_sum)
            total_sum += g_sum

        rows.append({
            "maNV": ts.maNV,
            "hoTen": ts.hoTen,
            "donVi": ts.donVi or "",
            "scores": flat_scores,       # theo thứ tự groups/tests
            "group_totals": group_totals,  # theo thứ tự groups
            "total": total_sum,
        })

    rows.sort(key=lambda r: (-r["total"], r["maNV"]))

    return render(request, "ranking/index.html", {
        "cuoc_this": cuoc_this,
        "selected_ct": selected_ct,
        "groups": groups,
        "rows": rows,
        "total_max": total_max,
        "title": f"Xếp hạng — {selected_ct.ma} · {selected_ct.tenCuocThi}",
    })
