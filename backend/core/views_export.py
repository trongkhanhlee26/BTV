# core/views_export.py
from __future__ import annotations
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.db.models import Avg
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side  # <- thêm Border, Side
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
    # Thêm nhãn "Tổng" ở cuối
    columns = ['STT', 'Mã NV', 'Họ tên'] + info_titles + score_titles[3:] + ['Tổng']

    scores = (
        PhieuChamDiem.objects
        .filter(cuocThi=ct, baiThi_id__in=[c["id"] for c in cols_meta])
        .values("thiSinh__maNV", "baiThi_id")
        .annotate(avg=Avg("diem"))
    )
    score_map = {(r["thiSinh__maNV"], r["baiThi_id"]): float(r["avg"]) for r in scores}

    ts_qs = ThiSinh.objects.filter(cuocThi=ct).order_by("maNV").distinct()
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
        # cộng điểm theo từng bài
        total = 0.0
        for c in cols_meta:
            val = score_map.get((ts.maNV, c["id"]), "")
            row.append(val)
            if isinstance(val, (int, float)):
                total += float(val)
        # đẩy "Tổng" vào cuối hàng
        row.append(total)
        rows.append(row)
    return columns, rows


# (Giữ export_page như cũ)

# (Tuỳ ý: có thể xoá export_csv và route của nó)
# def export_csv(...):  # <-- BỎ KHI KHÔNG DÙNG NỮA
#     ...

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font, PatternFill
from io import BytesIO
def export_xlsx(request):
    ct_id = request.GET.get("ct")
    ct = get_object_or_404(CuocThi, id=ct_id)

    use_visible = (request.method == "POST")
    if use_visible:
        # Nhận payload từ frontend
        import json
        try:
            payload = json.loads(request.body.decode("utf-8"))
            columns = payload.get("columns") or []
            rows = payload.get("rows") or []
            kinds = payload.get("col_kinds") or ["info"] * len(columns)
        except Exception:
            # fallback sang full nếu payload lỗi
            columns, rows = _flatten(ct)
            kinds = ["info"] * len(columns)
    else:
        columns, rows = _flatten(ct)
        # Tự tính kinds: 3 cột đầu (STT/Mã NV/Họ tên) + 5 cột info tiếp theo = info
        # Các cột điểm là từ sau 8 cột info đến cột "Tổng" (cuối)
        info_count = 3 + 5  # STT, Mã NV, Họ tên + (Đơn vị, Chi nhánh, Vùng, Nhóm, Email)
        kinds = ["info"] * len(columns)
        for j in range(info_count, len(columns) - 1):
            kinds[j] = "score"
        kinds[-1] = "score"  # "Tổng" tô giống cột điểm


    wb = Workbook()
    ws = wb.active
    ws.title = f"{ct.ma}"

    # ==== Header: KHÔNG in đậm ====
    ws.append(columns)
    for c in range(1, len(columns)+1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, size=12)  # KHÔNG in đậm
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # ==== Body: dùng rows đã có (full hoặc visible) ====
    for r in rows:
        ws.append(r)

    # ==== Tô màu theo CỘT ====
    fill_info  = PatternFill(fill_type="solid", start_color="FFEAF4FF", end_color="FFEAF4FF")  # xanh nhạt
    fill_score = PatternFill(fill_type="solid", start_color="FFFFF5E6", end_color="FFFFF5E6")  # vàng nhạt

    max_row = ws.max_row
    max_col = ws.max_column
    for j in range(1, max_col+1):
        kind = kinds[j-1] if (j-1) < len(kinds) else "info"
        fill = fill_score if kind == "score" else fill_info
        for i in range(1, max_row+1):
            ws.cell(row=i, column=j).fill = fill


    # ... sau khi append header + body và tô màu, tính sẵn:
    max_row = ws.max_row
    max_col = ws.max_column

    # ==== Border mảnh cho toàn bộ ô ====
    thin = Side(style="thin", color="FF000000")
    border_all = Border(left=thin, right=thin, top=thin, bottom=thin)

    for r_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=max_row, min_col=1, max_col=max_col), start=1):
        for cell in row:
            cell.border = border_all
            # Font: header (r1) 12pt, body 11pt, không đậm (đúng yêu cầu “không in đậm”)
            if r_idx == 1:
                cell.font = Font(name="Times new roman", size=12, bold=True)
            else:
                cell.font = Font(name="Times new roman", size=11, bold=False)
            # Alignment
            cell.alignment = Alignment(
                vertical="center",
                wrap_text=True,
                horizontal=cell.alignment.horizontal if cell.alignment else "left"
            )

    # (giữ nguyên) Freeze 3 cột + 1 hàng tiêu đề
    ws.freeze_panes = "E2"

    # ==== Auto width (rộng hơn một chút) ====
    for i, col in enumerate(columns, start=1):
        maxlen = len(str(col)) if col is not None else 0
        for r in rows:
            v = r[i-1] if i-1 < len(r) else ""
            l = len(str(v)) if v is not None else 0
            if l > maxlen:
                maxlen = l
        # padding rộng hơn: +4, tối thiểu 12, tối đa 60
        ws.column_dimensions[get_column_letter(i)].width = max(12, min(maxlen + 4, 60))


    # Giữ freeze panes cũ (3 cột trái + 1 hàng tiêu đề)
    ws.freeze_panes = "E2"

    bio = BytesIO(); wb.save(bio); bio.seek(0)
    resp = HttpResponse(
        bio.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    # Tên file: nếu POST visible thì đổi chút cho phân biệt
    fname = f'export_{ct.ma}.xlsx' if not use_visible else f'export_{ct.ma}_visible.xlsx'
    resp["Content-Disposition"] = f'attachment; filename="{fname}"'
    return resp
def export_page(request):
    ct_id = request.GET.get("ct")
    ct = get_object_or_404(CuocThi, id=ct_id)

    # Chỉ lấy các cuộc thi đang bật
    active_cts = CuocThi.objects.filter(trangThai=True).order_by("ma", "tenCuocThi")

    columns, rows = _flatten(ct)
    return render(request, "export/index.html", {
        "contest": ct,
        "columns": columns,
        "rows": rows,
        "active_cts": active_cts,   # <-- thêm vào context
    })
