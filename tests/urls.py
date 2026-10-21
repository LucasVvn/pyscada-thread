from django.urls import path
from pyscada.admin import admin_site

urlpatterns = [
    path("admin/", admin_site.urls),
]
