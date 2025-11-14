from django.contrib import admin
from .models import (
    ThiSinh, GiamKhao, CuocThi, VongThi, BaiThi, PhieuChamDiem,
    BaiThiTemplateSection, BaiThiTemplateItem, CapThiDau, ThiSinhCapThiDau
)

@admin.register(ThiSinh)
class ThiSinhAdmin(admin.ModelAdmin):
    list_display = ("maNV", "hoTen", "chiNhanh", "vung", "donVi", "nhom", "ds_cuoc_thi")
    list_filter = ("cuocThi",)   # đúng tên field M2M
    search_fields = ("maNV", "hoTen", "email", "vung", "donVi")

    def ds_cuoc_thi(self, obj):
        try:
            return ", ".join(ct.ma for ct in obj.cuocThi.all())
        except Exception:
            return ""
    ds_cuoc_thi.short_description = "Cuộc thi"



@admin.register(GiamKhao)
class GiamKhaoAdmin(admin.ModelAdmin):
    list_display = ("maNV", "hoTen", "email", "role", "bai_thi")
    search_fields = ("maNV", "hoTen")

    def bai_thi(self, obj):
        try:
            # obj.phan_cong_bai_thi yields GiamKhaoBaiThi instances (assignment objects)
            # access the related BaiThi via .baiThi
            return ", ".join([assign.baiThi.tenBaiThi for assign in obj.phan_cong_bai_thi.all()])
        except Exception:
            return ""
    bai_thi.short_description = "Bài thi"
    
@admin.register(CuocThi)
class CuocThiAdmin(admin.ModelAdmin):
    list_display = ("ma", "tenCuocThi", "trangThai")
    search_fields = ("ma", "tenCuocThi")
    list_filter = ("trangThai",)


@admin.register(VongThi)
class VongThiAdmin(admin.ModelAdmin):
    list_display = ("ma", "tenVongThi", "cuocThi")
    search_fields = ("ma", "tenVongThi")  
    list_filter = ("cuocThi",)

@admin.register(BaiThi)
class BaiThiAdmin(admin.ModelAdmin):
    list_display = ("ma", "tenBaiThi", "cachChamDiem", "vongThi", "giam_khao")
    search_fields = ("ma", "tenBaiThi")
    list_filter = ("vongThi",)

    def giam_khao(self, obj):
        return ", ".join([gk.giamKhao.hoTen for gk in obj.giam_khao_duoc_chi_dinh.all()])

@admin.register(PhieuChamDiem)
class PhieuChamDiemAdmin(admin.ModelAdmin):
    list_display = ("maPhieu", "thiSinh", "giamKhao", "baiThi", "diem", "maCuocThi", "thoiGian", "updated_at")
    search_fields = ("thiSinh__maNV", "giamKhao__maNV", "baiThi__ma", "maCuocThi")
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

    # core/admin.py
from .models import BanGiamDoc  # ADD

@admin.register(BanGiamDoc)
class BanGiamDocAdmin(admin.ModelAdmin):
    list_display = ("maBGD", "ten", "token", "created_at")
    search_fields = ("maBGD", "ten", "token")
class ThiSinhCapThiDauInline(admin.TabularInline):
    model = ThiSinhCapThiDau
    extra = 0
    fields = ("side", "slot", "thiSinh", "image_url")
@admin.register(CapThiDau)
class CapThiDauAdmin(admin.ModelAdmin):
    list_display = ("maCapDau", "cuocThi", "vongThi", "thuTuThiDau", "active", "created_at")
    list_filter = ("cuocThi", "vongThi", "active")
    search_fields = ("maCapDau", "cuocThi__ma", "cuocThi__tenCuocThi")
    ordering = ("cuocThi", "thuTuThiDau")
    inlines = [ThiSinhCapThiDauInline]

@admin.register(ThiSinhCapThiDau)
class ThiSinhCapThiDauAdmin(admin.ModelAdmin):
    list_display = ("pair", "side", "slot", "thiSinh", "image_url")
    list_filter = ("pair__cuocThi", "side")
    search_fields = ("thiSinh__maNV", "thiSinh__hoTen", "pair__maCapDau")
