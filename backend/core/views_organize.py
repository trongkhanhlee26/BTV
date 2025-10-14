from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db.models import Prefetch
from .models import CuocThi, VongThi, BaiThi, BaiThiTimeRule



@require_http_methods(["GET", "POST"])
def organize_view(request):
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "create_ct":
                ten = (request.POST.get("tenCuocThi") or "").strip()
                trang_thai = request.POST.get("trangThai") == "on"
                if not ten:
                    messages.error(request, "Vui lòng nhập tên cuộc thi.")
                else:
                    ct = CuocThi(tenCuocThi=ten, trangThai=trang_thai)
                    ct.save()  # auto-gen ct.ma
                    messages.success(request, f"Tạo cuộc thi {ct.ma} thành công.")
                return redirect(request.path)

            if action == "create_vt":
                ct_id = request.POST.get("cuocThi_id")
                ten_vt = (request.POST.get("tenVongThi") or "").strip()
                if not ct_id or not ten_vt:
                    messages.error(request, "Vui lòng chọn cuộc thi và nhập tên vòng thi.")
                else:
                    cuoc_thi = CuocThi.objects.get(id=ct_id)
                    vt = VongThi(tenVongThi=ten_vt, cuocThi=cuoc_thi)
                    vt.save()  # auto-gen vt.ma
                    messages.success(request, f"Tạo vòng thi {vt.ma} trong {cuoc_thi.ma} thành công.")
                return redirect(request.path)

            if action == "create_bt":
                vt_id = request.POST.get("vongThi_id")
                ten_bt = (request.POST.get("tenBaiThi") or "").strip()
                method = request.POST.get("phuongThucCham") or "POINTS"
                max_diem = request.POST.get("cachChamDiem")
                # POINTS thì phải có max_diem; TIME/TEMPLATE thì cho phép max_diem=0 tạm thời
                if not vt_id or not ten_bt:
                    messages.error(request, "Vui lòng chọn vòng thi và nhập tên bài thi.")
                elif method == "POINTS" and not max_diem:
                    messages.error(request, "Vui lòng nhập điểm tối đa cho phương thức thang điểm.")
                else:
                    vong_thi = VongThi.objects.get(id=vt_id)
                    bt = BaiThi(
                        tenBaiThi=ten_bt,
                        vongThi=vong_thi,
                        phuongThucCham=method,
                        cachChamDiem=int(max_diem) if (method == "POINTS" and max_diem) else 0,
                    )
                    bt.save()  # auto-gen bt.ma
                    messages.success(request, f"Tạo bài thi {bt.ma} trong {vong_thi.ma} thành công.")
                return redirect(request.path)
            # NEW: cấu hình thang thời gian
            if action == "config_time_rules":
                import json
                btid = request.POST.get("baiThi_id")
                

                raw = request.POST.get("time_rules_json") or "[]"
                try:
                    bt = BaiThi.objects.get(id=btid)
                except BaiThi.DoesNotExist:
                    messages.error(request, "Bài thi không tồn tại.")
                    return redirect(request.path)
                if bt.phuongThucCham != "TIME":
                    messages.error(request, "Bài thi này không dùng phương thức chấm theo thời gian.")
                    return redirect(request.path)
                try:
                    rows = json.loads(raw)
                except Exception:
                    messages.error(request, "Dữ liệu cấu hình không hợp lệ.")
                    return redirect(request.path)
                # validate sơ bộ & lưu
                cleaned = []
                for r in rows:
                    try:
                        s = int(r.get("start", 0))
                        e = int(r.get("end", 0))
                        sc = int(r.get("score", 0))
                    except Exception:
                        continue
                    if s < 0 or e < 0 or e < s:
                        continue
                    cleaned.append((s, e, sc))
                from django.db import transaction
                with transaction.atomic():
                    bt.time_rules.all().delete()
                    BaiThiTimeRule.objects.bulk_create([
                        BaiThiTimeRule(baiThi=bt, start_seconds=s, end_seconds=e, score=sc)
                        for (s, e, sc) in cleaned
                    ])
                messages.success(request, f"Đã lưu {len(cleaned)} dòng thang thời gian cho {bt.ma}.")
                return redirect(request.path)

            messages.error(request, "Hành động không hợp lệ.")
            return redirect(request.path)

        except CuocThi.DoesNotExist:
            messages.error(request, "Cuộc thi không tồn tại.")
            return redirect(request.path)
        except VongThi.DoesNotExist:
            messages.error(request, "Vòng thi không tồn tại.")
            return redirect(request.path)
        except ValueError:
            messages.error(request, "Giá trị điểm tối đa không hợp lệ.")
            return redirect(request.path)

    # GET: hiển thị danh sách CT → VT → BT
    cuoc_this = (
        CuocThi.objects
        .prefetch_related(Prefetch("vong_thi", queryset=VongThi.objects.prefetch_related("bai_thi__time_rules")))
        .order_by("-id")
    )
    return render(request, "organize/index.html", {"cuoc_this": cuoc_this})


@require_http_methods(["GET", "POST"])
def competition_list_view(request):
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "create":
                ten = (request.POST.get("tenCuocThi") or "").strip()
                trang_thai = request.POST.get("trangThai") == "on"
                if not ten:
                    messages.error(request, "Vui lòng nhập tên cuộc thi.")
                else:
                    ct = CuocThi(tenCuocThi=ten, trangThai=trang_thai)
                    ct.save()
                    messages.success(request, f"Đã tạo {ct.ma}.")
                return redirect(request.path)

            if action == "update":
                ct_id = request.POST.get("id")
                ten = (request.POST.get("tenCuocThi") or "").strip()
                trang_thai = request.POST.get("trangThai") == "on"
                ct = CuocThi.objects.get(id=ct_id)
                if not ten:
                    messages.error(request, "Tên cuộc thi không được rỗng.")
                else:
                    ct.tenCuocThi = ten
                    ct.trangThai = trang_thai
                    ct.save(update_fields=["tenCuocThi", "trangThai"])
                    messages.success(request, f"Đã cập nhật {ct.ma}.")
                return redirect(request.path)

            if action == "delete":
                ct_id = request.POST.get("id")
                ct = CuocThi.objects.get(id=ct_id)
                code = ct.ma
                ct.delete()
                messages.success(request, f"Đã xoá {code}.")
                return redirect(request.path)

            messages.error(request, "Hành động không hợp lệ.")
            return redirect(request.path)
        except CuocThi.DoesNotExist:
            messages.error(request, "Cuộc thi không tồn tại.")
            return redirect(request.path)

    # GET
    items = CuocThi.objects.order_by("-id")
    return render(request, "organize/competitions.html", {"items": items})