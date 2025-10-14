from django.contrib import admin
from .models import ThiSinh, GiamKhao, CuocThi, VongThi, BaiThi, PhieuChamDiem

@admin.register(ThiSinh)
class ThiSinhAdmin(admin.ModelAdmin):
    list_display = ("maNV", "hoTen", "chiNhanh", "vung", "donVi", "nhom")
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
