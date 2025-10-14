# after
import csv
import unicodedata  # NEW
import re          # NEW
from io import TextIOWrapper
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.db import transaction
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from openpyxl import load_workbook

from .models import ThiSinh, GiamKhao

REQUIRED_COLUMNS = {
    "thisinh": ["maNV", "hoTen", "chiNhanh", "vung", "donVi", "email", "nhom"],
    "giamkhao": ["maNV", "hoTen", "email"],
}

# ===== Alias & chuẩn hóa header =====
def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")  # bỏ dấu
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "", s)  # bỏ ký tự lạ & khoảng trắng
    return s

HEADER_ALIASES = {
    # maNV
    "manv": "maNV", "manhanvien": "maNV", "manvnv": "maNV", "ma": "maNV", "ma_nv": "maNV",
    # hoTen
    "hoten": "hoTen", "ten": "hoTen", "hovaten": "hoTen", "ho_ten": "hoTen",
    # chiNhanh
    "chinhanh": "chiNhanh", "chi_nhanh": "chiNhanh", "cn": "chiNhanh",
    # vung
    "vung": "vung", "mien": "vung",
    # donVi
    "donvi": "donVi", "don_vi": "donVi", "dv": "donVi", "don": "donVi", "donvichuyendoi": "donVi",
    # email
    "email": "email", "mail": "email", "e-mail": "email",
    # nhom
    "nhom": "nhom", "group": "nhom", "nhomthi": "nhom",
}

def _map_header_list(header, expected_cols):
    """
    Trả về: (canon_order, source_idx)
    canon_order: danh sách tên cột đã được map về canonical (theo thứ tự header gốc)
    source_idx: dict {canonical_name: index_goc}
    """
    canon_order = []
    for h in header:
        key = _normalize(h or "")
        canon = HEADER_ALIASES.get(key)
        canon_order.append(canon or (h or "").strip())

    src_idx = {}
    for i, canon in enumerate(canon_order):
        if canon not in src_idx:
            src_idx[canon] = i

    missing = [c for c in expected_cols if c not in src_idx]
    return canon_order, src_idx, missing

# after
def _read_xlsx(file, expected_cols):
    wb = load_workbook(file, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    header = [str(c).strip() if c is not None else "" for c in rows[0]]

    _, src_idx, missing = _map_header_list(header, expected_cols)
    if missing:
        raise ValueError(f"Thiếu cột: {', '.join(missing)}")

    data = []
    for r in rows[1:]:
        if r is None:
            continue
        row = {}
        for c in expected_cols:
            idx = src_idx[c]
            val = r[idx] if idx < len(r) else None
            row[c] = "" if val is None else str(val).strip()
        data.append(row)
    return data

# after
def _read_csv(file, expected_cols):
    # file là UploadedFile -> cần decode UTF-8
    text_stream = TextIOWrapper(file, encoding="utf-8")
    reader = csv.DictReader(text_stream)
    header = reader.fieldnames or []

    # map header gốc -> canonical
    canon_order, src_idx, missing = _map_header_list(header, expected_cols)
    if missing:
        raise ValueError(f"Thiếu cột: {', '.join(missing)}")

    # Xây map canonical -> tên cột gốc để lấy dữ liệu
    # (ưu tiên đúng chữ canonical nếu đã có, nếu không lấy từ alias)
    canon_to_source = {}
    for i, h in enumerate(header):
        key = _normalize(h or "")
        canon = HEADER_ALIASES.get(key) or (h or "").strip()
        if canon not in canon_to_source:
            canon_to_source[canon] = h

    data = []
    for row in reader:
        out = {}
        for c in expected_cols:
            src = canon_to_source.get(c, c)
            out[c] = (row.get(src, "") or "").strip()
        data.append(out)
    return data
    
@staff_member_required
def import_view(request):
    if request.method == "POST":
        target = request.POST.get("target")  # thisinh | giamkhao
        f = request.FILES.get("file")
        if target not in REQUIRED_COLUMNS:
            messages.error(request, "Vui lòng chọn loại dữ liệu hợp lệ.")
            return redirect(request.path)
        if not f:
            messages.error(request, "Vui lòng chọn tệp CSV/XLSX.")
            return redirect(request.path)

        expected = REQUIRED_COLUMNS[target]
        try:
            if isinstance(f, (InMemoryUploadedFile, TemporaryUploadedFile)) and f.name.lower().endswith(".xlsx"):
                rows = _read_xlsx(f, expected)
            else:
                rows = _read_csv(f, expected)
        except Exception as e:
            messages.error(request, f"Lỗi đọc tệp: {e}")
            return redirect(request.path)

        created = updated = skipped = 0
        with transaction.atomic():
            if target == "thisinh":
                for r in rows:
                    ma = r["maNV"]
                    if not ma:
                        skipped += 1
                        continue

                    obj, is_created = ThiSinh.objects.update_or_create(
                        pk=ma,
                        defaults=dict(
                            hoTen=r["hoTen"],
                            chiNhanh=r["chiNhanh"],
                            vung=r["vung"],
                            donVi=r["donVi"],
                            email=r["email"],
                            nhom=r["nhom"],
                        )
                    )

                    created += int(is_created)
                    updated += int(not is_created)
            else:  # giamkhao
                for r in rows:
                    ma = r["maNV"]
                    if not ma:
                        skipped += 1
                        continue
                    obj, is_created = GiamKhao.objects.update_or_create(
                        pk=ma,
                        defaults=dict(
                            hoTen=r["hoTen"],
                            email=r["email"],
                        )
                    )
                    created += int(is_created)
                    updated += int(not is_created)

        messages.success(request, f"Import xong: thêm {created}, cập nhật {updated}, bỏ qua {skipped}.")
        return redirect(request.path)

    return render(request, "admin/import_csv.html", {})
