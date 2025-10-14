from django.urls import path
from .views_admin import import_view

app_name = "core_admin_tools"

urlpatterns = [
    path("import/", import_view, name="import"),
]
