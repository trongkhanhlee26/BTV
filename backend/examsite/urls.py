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

urlpatterns = [\
    path("", home_view, name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path('score/', score_view),
    path('organize/competitions/', competition_list_view),            
    path('organize/', organize_view),
    path('admin/tools/', include('core.urls_admin')),
    path('admin/', admin.site.urls),
    path('ranking/', ranking_view), 
    path("manage/", manage_view, name="manage"),
]