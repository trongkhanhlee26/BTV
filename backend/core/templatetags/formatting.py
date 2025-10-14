# core/templatetags/formatting.py
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def status_badge(v):
    """
    v: bool, int (0/1), hoặc chuỗi 'true'/'false'
    -> trả về span badge HTML
    """
    true_values = {True, 1, "1", "true", "True", "on", "ON"}
    is_on = v in true_values
    label = "Đang bật" if is_on else "Đang tắt"
    # class dùng Tailwind (hoặc class bạn đang có)
    classes = "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold"
    color = "bg-green-600/20 text-green-300 border border-green-600/40" if is_on else \
            "bg-red-600/20 text-red-300 border border-red-600/40"
    html = f'<span class="{classes} {color}">{label}</span>'
    return mark_safe(html)
