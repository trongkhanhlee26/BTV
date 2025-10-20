from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone
from django.db.models import Max, SET_NULL
from django.core.validators import MinValueValidator
# Helper để sinh mã tự động CTxxx, VTxxx, BTxxx
def generate_code(model, prefix):
    last_code = model.objects.aggregate(max_code=Max("ma"))["max_code"]
    if not last_code:
        return f"{prefix}001"
    num = int(last_code[len(prefix):]) + 1
    return f"{prefix}{num:03d}"


class ThiSinh(models.Model):
    maNV = models.CharField(max_length=20, primary_key=True)
    hoTen = models.CharField(max_length=100)
    chiNhanh = models.CharField(max_length=100)
    vung = models.CharField(max_length=100, blank=True, null=True)
    donVi = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True)
    nhom = models.CharField(max_length=50)
    cuocThi = models.ManyToManyField(
        'CuocThi',
        through='ThiSinhCuocThi',
        related_name='thiSinhs',
        blank=True
    )

    def __str__(self):
        return f"{self.maNV} - {self.hoTen}"
class ThiSinhCuocThi(models.Model):
    thiSinh = models.ForeignKey('ThiSinh', on_delete=models.CASCADE, related_name='tham_gia')
    cuocThi = models.ForeignKey('CuocThi', on_delete=models.CASCADE, related_name='thi_sinh_tham_gia')

    class Meta:
        unique_together = ('thiSinh', 'cuocThi')

    def __str__(self):
        # đổi 'maNV' hoặc 'ma' tuỳ đúng tên trường trong model của bạn
        try:
            ts = getattr(self.thiSinh, 'maNV', self.thiSinh_id)
            ct = getattr(self.cuocThi, 'ma', self.cuocThi_id)
        except Exception:
            ts, ct = self.thiSinh_id, self.cuocThi_id
        return f"{ts} ↔ {ct}"


class GiamKhao(models.Model):
    maNV = models.CharField(max_length=20, primary_key=True)
    hoTen = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.maNV} - {self.hoTen}"


class CuocThi(models.Model):
    ma = models.CharField(max_length=10, unique=True, editable=False)
    tenCuocThi = models.CharField(max_length=200)
    trangThai = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.ma:
            self.ma = generate_code(CuocThi, "CT")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ma} - {self.tenCuocThi}"


class VongThi(models.Model):
    ma = models.CharField(max_length=10, editable=False)
    tenVongThi = models.CharField(max_length=200)
    cuocThi = models.ForeignKey(CuocThi, on_delete=models.CASCADE, related_name="vong_thi")

    def save(self, *args, **kwargs):
        if not self.ma:
            self.ma = generate_code(VongThi, "VT")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ma} - {self.tenVongThi}"


class BaiThi(models.Model):
    ma = models.CharField(max_length=10, editable=False)
    tenBaiThi = models.CharField(max_length=200)
    cachChamDiem = models.IntegerField()
    vongThi = models.ForeignKey(VongThi, on_delete=models.CASCADE, related_name="bai_thi")
    PHUONG_THUC_CHOICES = (
        ("TIME", "Chấm theo thời gian"),
        ("TEMPLATE", "Chấm theo mẫu"),
        ("POINTS", "Chấm theo thang điểm"),
    )
    phuongThucCham = models.CharField(max_length=20, choices=PHUONG_THUC_CHOICES, default="POINTS")
    def save(self, *args, **kwargs):
        if not self.ma:
            self.ma = generate_code(BaiThi, "BT")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ma} - {self.tenBaiThi}"
class BaiThiTimeRule(models.Model):
    baiThi = models.ForeignKey(BaiThi, on_delete=models.CASCADE, related_name="time_rules")
    start_seconds = models.IntegerField()  # inclusive
    end_seconds = models.IntegerField()    # inclusive
    score = models.IntegerField()

    class Meta:
        ordering = ["start_seconds", "end_seconds", "score"]


# NEW: Mẫu chấm theo "TEMPLATE" gắn với từng bài thi
class BaiThiTemplateSection(models.Model):
    baiThi = models.ForeignKey(BaiThi, on_delete=models.CASCADE, related_name="template_sections")
    stt = models.PositiveIntegerField(default=1)  # thứ tự mục lớn
    title = models.CharField(max_length=255)      # tên mục lớn (vd: Phần I: Kiến thức)
    note = models.CharField(max_length=255, blank=True, null=True)  # ghi chú (nếu có)

    class Meta:
        ordering = ["baiThi_id", "stt"]

    def __str__(self):
        return f"{self.baiThi.ma} - [{self.stt}] {self.title}"


class BaiThiTemplateItem(models.Model):
    section = models.ForeignKey(BaiThiTemplateSection, on_delete=models.CASCADE, related_name="items")
    stt = models.PositiveIntegerField(default=1)     # thứ tự mục con trong section
    content = models.CharField(max_length=500)       # nội dung tiêu chí/câu hỏi
    max_score = models.IntegerField(default=0)       # điểm tối đa cho mục con
    note = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["section_id", "stt"]

    def __str__(self):
        return f"{self.section.baiThi.ma} - {self.section.title} - [{self.stt}] {self.content}"

class PhieuChamDiem(models.Model):
    maPhieu = models.AutoField(primary_key=True)
    thiSinh = models.ForeignKey(ThiSinh, on_delete=models.CASCADE)
    giamKhao = models.ForeignKey(GiamKhao, on_delete=models.CASCADE)
    cuocThi = models.ForeignKey(CuocThi, on_delete=models.CASCADE)
    maCuocThi = models.CharField(max_length=10, db_index=True, editable=False)  # NEW
    vongThi = models.ForeignKey(VongThi, on_delete=models.CASCADE)
    baiThi = models.ForeignKey(BaiThi, on_delete=models.CASCADE)
    diem = models.IntegerField(validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("thiSinh", "giamKhao", "baiThi")

    def save(self, *args, **kwargs):
        # đồng bộ mã cuộc thi từ FK (lưu CTxxx để báo cáo/search nhanh)
        self.maCuocThi = self.cuocThi.ma

        # kiểm tra điểm hợp lệ theo phương thức chấm
        method = getattr(self.baiThi, "phuongThucCham", "POINTS")
        if self.diem is None or self.diem < 0:
            raise ValueError("Điểm không hợp lệ!")

        if method == "POINTS":
            # chỉ áp trần khi là thang điểm
            if self.diem > self.baiThi.cachChamDiem:
                raise ValueError("Điểm vượt quá điểm tối đa của bài thi!")

        # (TIME/TEMPLATE sẽ được quy đổi/validate ở bước 3B)
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)