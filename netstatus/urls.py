"""netstatus URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Import the include() function: from django.conf.urls import url, include
    3. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import url
from django.contrib import admin
from netstatus_web import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', views.main, name='main'),
    url(r'^device/list/$', views.device_list, name='device-list'),
    url(r'^device/new$', views.device_new, name='new-device'),
    url(r'^device/new/success$', views.device_new_success, name='new-device_success'),
    url(r'^device/remove$', views.device_remove, name='remove-device'),
    url(r'^device/info/(?P<id>[0-9]+)$', views.device_info, name='device_info'),
    url(r'^device/edit/db/(?P<id>[0-9]+)$', views.device_edit_db, name='device_edit_db'),
    url(r'^device/edit/snmp/(?P<id>[0-9]+)$', views.device_edit_snmp, name='device_edit_snmp'),
    url(r'^piechart-online$', views.piechart_online, name='piechart-online'),
]
