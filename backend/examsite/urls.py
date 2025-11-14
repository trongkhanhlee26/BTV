"""
URL configuration for examsite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from core.views_home import home_view, manage_view
from core.views_auth import login_view, logout_view
from core.views_organize import organize_view, competition_list_view    
from core.views_score import score_view
from core.views_ranking import ranking_view
from core.views_management import management_view
from core.views_export import export_page, export_xlsx
from django.urls import path
from core import views_score
from core.views_admin import import_view
from core.views_battle import battle_view, manage_battle_view, save_pairing, pairing_state

urlpatterns = [
    path("", home_view, name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path('score/', score_view),
    path('organize/competitions/', competition_list_view, name='competition-list'),  
    path("organize/<int:ct_id>/", organize_view, name="organize-detail"),         
    path('organize/', organize_view),
    path('admin/tools/', include('core.urls_admin')),
    path('admin/', admin.site.urls),
    path('ranking/', ranking_view), 
    path("manage/", manage_view, name="manage"),
    path("management/", management_view, name="management"),
    path("score/template/<int:btid>/", views_score.score_template_api, name="score_template_api"),
    path("export", export_page, name="export-page"),     # trang bảng “Excel-like”
    path("export-xlsx", export_xlsx, name="export-xlsx"),
    path("import/", import_view, name="import"),
    path("battle/", battle_view, name="battle"),
    path("battle/manage/", manage_battle_view, name="manage-battle"),

    path("battle/pairing/save", save_pairing, name="battle-pairing-save"),
    path("battle/pairing/state", pairing_state, name="battle-pairing-state"),
]