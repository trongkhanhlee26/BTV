from django.contrib import admin
from .models import (
    ThiSinh, GiamKhao, CuocThi, VongThi, BaiThi, PhieuChamDiem,
    BaiThiTemplateSection, BaiThiTemplateItem,
)

@admin.register(ThiSinh)
class ThiSinhAdmin(admin.ModelAdmin):
    list_display = ("maNV", "hoTen", "chiNhanh", "vung", "donVi", "nhom", "ma_ct", "ten_cuoc_thi")
    list_select_related = ("cuocThi",)  # tăng tốc truy vấn
    list_filter = ("cuocThi",)          # lọc theo cuộc thi
    search_fields = ("maNV", "hoTen", "maCuocThi")

    # NEW: cột mã CT
    def ma_ct(self, obj):
        return obj.maCuocThi or (obj.cuocThi.ma if obj.cuocThi else "")
    ma_ct.short_description = "maCT"
    ma_ct.admin_order_field = "maCuocThi"

    # NEW: cột tên cuộc thi
    def ten_cuoc_thi(self, obj):
        return obj.cuocThi.tenCuocThi if obj.cuocThi else ""
    ten_cuoc_thi.short_description = "Cuộc thi"

    search_fields = ("maNV", "hoTen", "email", "vung", "donVi")

@admin.register(GiamKhao)
class GiamKhaoAdmin(admin.ModelAdmin):
    list_display = ("maNV", "hoTen", "email")
    search_fields = ("maNV", "hoTen")

@admin.register(CuocThi)
class CuocThiAdmin(admin.ModelAdmin):
    list_display = ("ma", "tenCuocThi", "trangThai")
    search_fields = ("maCuocThi", "tenCuocThi")
    list_filter = ("trangThai",)

@admin.register(VongThi)
class VongThiAdmin(admin.ModelAdmin):
    list_display = ("ma", "tenVongThi", "cuocThi")
    search_fields = ("maVongThi", "tenVongThi")
    list_filter = ("cuocThi",)

@admin.register(BaiThi)
class BaiThiAdmin(admin.ModelAdmin):
    list_display = ("ma", "tenBaiThi", "cachChamDiem", "vongThi")
    search_fields = ("maBaiThi", "tenBaiThi")
    list_filter = ("vongThi",)

@admin.register(PhieuChamDiem)
class PhieuChamDiemAdmin(admin.ModelAdmin):
    list_display = ("maPhieu", "thiSinh", "giamKhao", "baiThi", "diem", "maCuocThi", "updated_at")
    search_fields = ("thiSinh__maNV", "giamKhao__maNV", "baiThi__maBaiThi", "maCuocThi")
    list_filter = ("maCuocThi", "baiThi")
    
@admin.register(BaiThiTemplateSection)
class BaiThiTemplateSectionAdmin(admin.ModelAdmin):
    list_display = ("id", "baiThi", "stt", "title")
    list_filter = ("baiThi",)
    search_fields = ("title", "baiThi__ma")

@admin.register(BaiThiTemplateItem)
class BaiThiTemplateItemAdmin(admin.ModelAdmin):
    list_display = ("id", "section", "stt", "content", "max_score")
    list_filter = ("section__baiThi",)
    search_fields = ("content", "section__title", "section__baiThi__ma")