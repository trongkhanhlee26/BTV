from django.db import models
import re
from urllib.parse import urlparse, parse_qs

# Create your models here.
from django.db import models
from django.utils import timezone
from django.db.models import Max, SET_NULL
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Count
import secrets
import string

def _gen_token_20():
    # 20 ký tự [A-Za-z0-9] an toàn
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(20))

def normalize_drive_url(url: str) -> str:
    """
    Helper chung để convert link Google Drive thành link ảnh trực tiếp.
    Dùng chung cho ThiSinh (và các chỗ khác nếu cần sau này).
    """
    if not url:
        return ""

    if "drive.google.com" not in url:
        return url

    file_id = None

    # /file/d/<id>/
    m = re.search(r"/file/d/([^/]+)", url)
    if m:
        file_id = m.group(1)
    else:
        # ?id=<id>
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if "id" in qs and qs["id"]:
            file_id = qs["id"][0]

    # Nếu vẫn không lấy được id (ví dụ link folders/...), trả lại url gốc
    if not file_id:
        return url

    return f"https://drive.google.com/uc?export=view&id={file_id}"

class BanGiamDoc(models.Model):
    maBGD = models.CharField(primary_key=True, max_length=20)  # "BGD001",...
    ten = models.CharField(max_length=255)
    token = models.CharField(max_length=32, unique=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.token:
            # phát sinh token 20 ký tự
            self.token = _gen_token_20()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.maBGD} — {self.ten}"
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
    chiNhanh = models.CharField(max_length=100, null=True)
    vung = models.CharField(max_length=100, blank=True, null=True)
    donVi = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True, null=True)
    nhom = models.CharField(max_length=50, null=True)
    cuocThi = models.ManyToManyField(
        'CuocThi',
        through='ThiSinhCuocThi',
        related_name='thiSinhs',
        blank=True
    )
    image_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL ảnh (trên Drive) của thí sinh"
    )
    @property
    def display_image_url(self) -> str:
        """
        URL cuối cùng dùng cho <img>.
        Sau này nếu có trường khác (ví dụ hinhAnh) vẫn có thể ưu tiên thêm.
        Hiện tại dùng image_url và convert link Drive nếu cần.
        """
        raw = self.image_url or ""
        return normalize_drive_url(raw)

    def __str__(self):
        return f"{self.maNV} - {self.hoTen}"
class ThiSinhCuocThi(models.Model):
    thiSinh = models.ForeignKey('ThiSinh', on_delete=models.CASCADE, related_name='tham_gia')
    cuocThi = models.ForeignKey('CuocThi', on_delete=models.CASCADE, related_name='thi_sinh_tham_gia')

    class Meta:
        unique_together = ('thiSinh', 'cuocThi')

    def __str__(self):
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

    ROLE_CHOICES = (
        ("ADMIN", "Admin"),
        ("JUDGE", "Giám khảo"),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="JUDGE", db_index=True, null=True)

    contestants_voted = models.ManyToManyField(
        'ThiSinhCapThiDau',
        through='BattleVote',
        related_name='judges',
        blank=True
    )

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
    
class GiamKhaoBaiThi(models.Model):  
    giamKhao = models.ForeignKey('GiamKhao', on_delete=models.CASCADE, related_name='phan_cong_bai_thi') 
    baiThi = models.ForeignKey('BaiThi', on_delete=models.CASCADE, related_name='giam_khao_duoc_chi_dinh') 
    assigned_at = models.DateTimeField(auto_now_add=True) 

    class Meta:  
        unique_together = ('giamKhao', 'baiThi') 
        indexes = [models.Index(fields=['giamKhao', 'baiThi'])]

    def __str__(self): 
        return f"{self.giamKhao.maNV} → {self.baiThi.ma}"

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
    thoiGian = models.PositiveIntegerField(default = 0, help_text="Thời gian (giây)")
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
            
        if getattr(self.giamKhao, "role", "JUDGE") != "ADMIN":
            allowed = GiamKhaoBaiThi.objects.filter(giamKhao=self.giamKhao, baiThi=self.baiThi).exists()
            if not allowed:
                raise PermissionError("Giám khảo chưa được admin chỉ định cho bài thi này.")

        # (TIME/TEMPLATE sẽ được quy đổi/validate ở bước 3B)
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

class CapThiDau(models.Model):
    """
    Một cặp / một trận đối kháng.
    Hiện tại mỗi pair = 1 vs 1.
    Sau này vẫn dùng lại được cho 2 vs 2, N vs N (nhiều member mỗi bên).
    """
    cuocThi = models.ForeignKey(
        CuocThi,
        on_delete=models.CASCADE,
        related_name="battle_pairs"
    )
    vongThi = models.ForeignKey(
        VongThi,
        on_delete=models.CASCADE,
        related_name="battle_pairs",
        null=True,
        blank=True,
        help_text="Có thể gắn với vòng thi (VD: Chung kết, Bán kết...)"
    )

    maCapDau = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        db_index=True
    )
    tenCapDau = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Tên hiển thị cặp đấu (nếu muốn đặt). VD: Bảng A - Trận 1"
    )
    thuTuThiDau = models.PositiveIntegerField(
        default=1,
        help_text="Thứ tự hiển thị cặp đấu"
    )
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Tự sinh mã BK001, BK002...
        if not self.maCapDau:
            from django.db.models import Max
            last_code = CapThiDau.objects.aggregate(max_code=Max("maCapDau"))["max_code"]
            if not last_code:
                self.maCapDau = "CK001"
            else:
                try:
                    num = int(last_code[2:]) + 1
                except ValueError:
                    num = 1
                self.maCapDau = f"CK{num:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.maCapDau} - {self.cuocThi.tenCuocThi} (#{self.thuTuThiDau})"


class ThiSinhCapThiDau(models.Model):
    """
    Một thí sinh cụ thể nằm trong một cặp đấu (ở bên trái / phải).
    - 1 cặp 1vs1: mỗi bên (L/R) có 1 member (slot = 1).
    - 2vs2: mỗi bên có 2 member (slot = 1,2).
    - NvsN: cứ thế tăng slot.
    """
    SIDE_CHOICES = (
        ("L", "Bên trái"),
        ("R", "Bên phải"),
    )

    pair = models.ForeignKey(
        CapThiDau,
        on_delete=models.CASCADE,
        related_name="members"
    )
    thiSinh = models.ForeignKey(
        ThiSinh,
        on_delete=models.CASCADE,
        related_name="battle_entries"
    )
    side = models.CharField(
        max_length=1,
        choices=SIDE_CHOICES,
        help_text="L = đội/trận bên trái, R = đội bên phải"
    )
    slot = models.PositiveSmallIntegerField(
        default=1,
        help_text="Thứ tự trong đội (dùng cho 2vs2, NvsN)"
    )
    @property
    def display_image_url(self) -> str:
        """
        Lấy URL ảnh hiển thị từ ThiSinh.
        Nếu ThiSinh có display_image_url thì dùng lại luôn.
        """
        return getattr(self.thiSinh, "display_image_url", "")
    
    @property
    def total_votes(self) -> int:
        """
        Tổng số phiếu vote cho entry này.
        """
        return self.votes.count()

    @property
    def avg_stars(self):
        """
        Điểm sao trung bình (float) hoặc None nếu chưa có vote.
        """
        from django.db.models import Avg
        agg = self.votes.aggregate(avg=Avg("stars"))
        return agg.get("avg")
    class Meta:
        unique_together = ("pair", "side", "slot")
        indexes = [
            models.Index(fields=["pair", "side"]),
            models.Index(fields=["thiSinh"]),
        ]

    def __str__(self):
        return f"{self.pair.maCapDau} - {self.get_side_display()} - {self.thiSinh.maNV} (slot {self.slot})"
    
class BattleVote(models.Model):
    giamKhao = models.ForeignKey(
        GiamKhao,
        on_delete=models.CASCADE,
        related_name="battle_votes",
        null=True,
        blank=True,
        db_column="giam_khao_id",   # 👈 ĐẶT ĐÚNG TÊN CỘT ĐANG CÓ TRONG DB
    )
    entry = models.ForeignKey(
        ThiSinhCapThiDau,
        on_delete=models.CASCADE,
        related_name="votes"
    )
    stars = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Số sao vote (1–5)"
    )
    note = models.TextField(
        null=True,
        blank=True,
        help_text="Nhận xét của BGD (tuỳ chọn)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("giamKhao", "entry")
        indexes = [
            models.Index(fields=["giamKhao", "entry"]),
            models.Index(fields=["entry"]),
        ]

    def __str__(self):
        gk = self.giamKhao.maNV if self.giamKhao else "N/A"
        ts = getattr(self.entry.thiSinh, "maNV", self.entry.thiSinh_id)
        pair_code = getattr(self.entry.pair, "maCapDau", self.entry.pair_id)
        return f"Vote {self.stars}★ - {gk} -> {ts} ({pair_code})"

