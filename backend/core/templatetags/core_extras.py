# from django import template
# register = template.Library()

# @register.filter
# def get_item(dictionary, key):
#     if not dictionary:
#         return ""
#     return dictionary.get(key, "")


from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Trả về dictionary[key] nếu tồn tại, nếu không trả về chuỗi rỗng.
    Dùng trong template: {{ scores|get_item:ts.maNV }}
    """
    if not isinstance(dictionary, dict):
        return ""
    return dictionary.get(key, "")
