# core/views_export.py
from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.db.models import Avg

# BÁM ĐÚNG MODEL HIỆN TẠI
from .models import CuocThi, VongThi, BaiThi, ThiSinh, PhieuChamDiem
from io import BytesIO
from django.shortcuts import get_object_or_404
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font

# ==== Helpers ====
def _score_type(bt) -> str:
    """
    Chuẩn hóa loại chấm giống các view khác:
    POINTS / TIME / TEMPLATE (mặc định POINTS).
    """
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
    """
    Trả về (columns_meta, columns_titles):
      - columns_meta: list dict [{id, code, title, max}]
      - columns_titles: list str tiêu đề hiển thị (mặc định: STT/Mã NV/Họ tên + các bài)
    """
    # Lấy tất cả vòng của cuộc thi → các bài trong từng vòng
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
        # Max điểm (tham chiếu giống ranking)
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

        cols.append({
            "id": b.id,
            "code": b.ma,
            "title": f"{b.vongThi.tenVongThi} – {b.tenBaiThi}",
            "max": b_max,
        })

    titles = ["STT", "Mã NV", "Họ tên"] + [c["title"] for c in cols]
    return cols, titles


def _flatten(ct: CuocThi):
    """
    columns: ['STT','Mã NV','Họ tên','Đơn vị','Chi nhánh','Vùng','Nhóm','Email', '<V1 – B1>', ...]
    rows:    [[1,'0001','Nguyễn A','P.Truyền thông','CN1','Miền Đông','Nhóm 1','a@x.com', 9.5, ...], ...]
    """
    cols_meta, score_titles = _build_columns(ct)

    # ===== Thêm cột thông tin TS =====
    info_titles = ['Đơn vị', 'Chi nhánh', 'Vùng', 'Nhóm', 'Email']
    columns = ['STT', 'Mã NV', 'Họ tên'] + info_titles + score_titles[3:]  # score_titles đã có 3 cột đầu

    # ===== Map điểm TB mỗi thí sinh–bài =====
    scores = (
        PhieuChamDiem.objects
        .filter(cuocThi=ct, baiThi_id__in=[c["id"] for c in cols_meta])
        .values("thiSinh__maNV", "baiThi_id")
        .annotate(avg=Avg("diem"))
    )
    score_map = {(r["thiSinh__maNV"], r["baiThi_id"]): float(r["avg"]) for r in scores}

    # ===== DS thí sinh thuộc cuộc thi =====
    ts_qs = (ThiSinh.objects.filter(cuocThi=ct).order_by("maNV").distinct())

    def _sv(x):  # safe value -> string
        return "" if x is None else str(x)

    rows = []
    for idx, ts in enumerate(ts_qs, start=1):
        # Các field hiện có trong model ThiSinh: maNV, hoTen, donVi, chiNhanh, vung, nhom, email
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


# ==== Views ====
def export_page(request):
    """
    Trang Excel-like (render HTML). Dữ liệu trả cho JS:
      - columns: danh sách tiêu đề cột theo thứ tự
      - rows   : list<list> đã “phẳng”
    """
    ct_id = request.GET.get("ct")
    ct = get_object_or_404(CuocThi, id=ct_id)

    columns, rows = _flatten(ct)

    ctx = {
        "contest": ct,
        "columns": columns,
        "rows": rows,
    }
    return render(request, "export/index.html", ctx)


def export_csv(request):
    ct_id = request.GET.get("ct")
    ct = get_object_or_404(CuocThi, id=ct_id)
    columns, rows = _flatten(ct)

    from io import StringIO
    import csv

    # Dùng TAB làm delimiter + CRLF; Excel đọc UTF-16 có BOM tốt
    sio = StringIO(newline="")
    writer = csv.writer(
        sio,
        delimiter="\t",
        lineterminator="\r\n",
        quoting=csv.QUOTE_MINIMAL,
    )

    # Gợi ý cho Excel: delimiter là TAB
    writer.writerow(["sep=\t"])
    writer.writerow(columns)
    for r in rows:
        writer.writerow(["" if v is None else str(v) for v in r])

    # Encode UTF-16 (Python tự chèn BOM)
    data_bytes = sio.getvalue().encode("utf-16")

    resp = HttpResponse(data_bytes, content_type="text/csv; charset=utf-16")
    resp["Content-Disposition"] = f'attachment; filename=export_{ct.ma}.csv'
    return resp
# ---- Thêm vào views_export.py ----
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font

def export_xlsx(request):
    ct_id = request.GET.get("ct")
    ct = get_object_or_404(CuocThi, id=ct_id)  # thay import CuocThi nếu cần
    columns, flat_rows = _flatten(ct)

    wb = Workbook()
    ws = wb.active
    ws.title = f"{ct.ma}"

    # Header
    ws.append(columns)
    for c in range(1, len(columns)+1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Body
    for r in flat_rows:
        ws.append(r)

    # Auto width nhẹ
    for i, col in enumerate(columns, start=1):
        maxlen = max([len(str(col))] + [len(str(row[i-1])) for row in flat_rows if row[i-1] is not None])
        ws.column_dimensions[get_column_letter(i)].width = min(maxlen + 2, 48)

    # Freeze 3 cột + 1 hàng (hàng 1 là header -> freeze D2)
    ws.freeze_panes = "D2"

    bio = BytesIO()
    wb.save(bio); bio.seek(0)
    resp = HttpResponse(
        bio.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename=export_{ct.ma}.xlsx'
    return resp

