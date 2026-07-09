from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as file_serve
from django.http import HttpResponseRedirect

FRONTEND = settings.BASE_DIR.parent  # E:\Bhupan Format

def serve_frontend(request, path='index.html'):
    return file_serve(request, path, document_root=FRONTEND)

def ref_redirect(request, ref_code):
    return HttpResponseRedirect(f'/?ref={ref_code.upper()}')

from resellers.views import AdminLoginView

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/admin/login/', AdminLoginView.as_view(), name='admin-login'),
    path('api/reseller/', include('resellers.urls')),
    path('api/store/', include('store.urls')),
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
    re_path(r'^(?P<ref_code>[A-Za-z0-9]{3,15})-ref/?$', ref_redirect),
    path('', serve_frontend),
    re_path(r'^(?P<path>.+)$', serve_frontend),
]
