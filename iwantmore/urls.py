"""
URL configuration for iwantmore project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from iwm.admin import admin_site

urlpatterns = [
    path('admin/', admin_site.urls),
    path('ckeditor5/upload/', include('django_ckeditor_5.urls')),
    path('',include('iwm.urls')),
    path('accounts/', include('allauth.urls'))
] 

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'iwm.views._404_view'
handler500 = 'iwm.views._500_view'
