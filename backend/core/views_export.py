# core/views_export.py
from __future__ import annotations
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.db.models import Avg

from .models import CuocThi, VongThi, BaiThi, ThiSinh, PhieuChamDiem

def _score_type(bt) -> str:
    v = getattr(bt, "phuongThucCham", None)
    if v is None:
        return "POINTS"
    s = str(v).strip().upper()
    if s in {"TIME", "2"}:
        return "TIME"
    if s in {"TEMPLATE", "1"}:
        return "TEMPLATE"
    return "POINTS"

def _build_columns(ct: CuocThi):
    vong_ids = VongThi.objects.filter(cuocThi=ct).values_list("id", flat=True)
    bai_qs = (
        BaiThi.objects
        .filter(vongThi_id__in=vong_ids)
        .select_related("vongThi")
        .prefetch_related("time_rules", "template_sections__items")
        .order_by("vongThi_id", "id")
    )

    cols = []
    for b in bai_qs:
        if _score_type(b) == "TIME":
            rules = list(b.time_rules.all()) if hasattr(b, "time_rules") else []
            b_max = max([r.score for r in rules], default=0)
        elif _score_type(b) == "TEMPLATE":
            b_max = sum(
                i.max_score
                for s in b.template_sections.all()
                for i in s.items.all()
            )
        else:
            b_max = b.cachChamDiem

        # >>> ĐỔI: tiêu đề 2 dòng cùng 1 ô (Vòng↵Bài thi)
        cols.append({
            "id": b.id,
            "code": b.ma,
            "title": f"{b.vongThi.tenVongThi}\n{b.tenBaiThi}",
            "max": b_max,
        })

    titles = ["STT", "Mã NV", "Họ tên"] + [c["title"] for c in cols]
    return cols, titles

def _flatten(ct: CuocThi):
    cols_meta, score_titles = _build_columns(ct)
    info_titles = ['Đơn vị', 'Chi nhánh', 'Vùng', 'Nhóm', 'Email']
    columns = ['STT', 'Mã NV', 'Họ tên'] + info_titles + score_titles[3:]

    scores = (
        PhieuChamDiem.objects
        .filter(cuocThi=ct, baiThi_id__in=[c["id"] for c in cols_meta])
        .values("thiSinh__maNV", "baiThi_id")
        .annotate(avg=Avg("diem"))
    )
    score_map = {(r["thiSinh__maNV"], r["baiThi_id"]): float(r["avg"]) for r in scores}

    ts_qs = (ThiSinh.objects.filter(cuocThi=ct).order_by("maNV").distinct())
    def _sv(x): return "" if x is None else str(x)

    rows = []
    for idx, ts in enumerate(ts_qs, start=1):
        row = [
            idx,
            _sv(getattr(ts, "maNV", "")),
            _sv(getattr(ts, "hoTen", "")),
            _sv(getattr(ts, "donVi", "")),
            _sv(getattr(ts, "chiNhanh", "")),
            _sv(getattr(ts, "vung", "")),
            _sv(getattr(ts, "nhom", "")),
            _sv(getattr(ts, "email", "")),
        ]
        for c in cols_meta:
            row.append(score_map.get((ts.maNV, c["id"]), ""))
        rows.append(row)
    return columns, rows

# (Giữ export_page như cũ)

# (Tuỳ ý: có thể xoá export_csv và route của nó)
# def export_csv(...):  # <-- BỎ KHI KHÔNG DÙNG NỮA
#     ...

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font

def export_xlsx(request):
    ct_id = request.GET.get("ct")
    ct = get_object_or_404(CuocThi, id=ct_id)
    columns, rows = _flatten(ct)

    wb = Workbook()
    ws = wb.active
    ws.title = f"{ct.ma}"

    # Header
    ws.append(columns)
    for c in range(1, len(columns)+1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, size=13)    # to hơn
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Body
    for r in rows:
        ws.append(r)

    # Auto width
    for i, col in enumerate(columns, start=1):
        maxlen = max([len(str(col))] + [len(str(r[i-1])) for r in rows if r[i-1] is not None])
        ws.column_dimensions[get_column_letter(i)].width = min(maxlen + 2, 48)

    # Freeze 3 cột + 1 hàng tiêu đề
    ws.freeze_panes = "D2"

    from io import BytesIO
    bio = BytesIO()
    wb.save(bio); bio.seek(0)
    resp = HttpResponse(
        bio.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename=export_{ct.ma}.xlsx'
    return resp
def export_page(request):
    ct_id = request.GET.get("ct")
    ct = get_object_or_404(CuocThi, id=ct_id)
    columns, rows = _flatten(ct)  # dùng hàm đã có ở dưới
    return render(request, "export/index.html", {
        "contest": ct,
        "columns": columns,
        "rows": rows
    })