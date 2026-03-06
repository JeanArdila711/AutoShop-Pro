"""
URL configuration for autoshop project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from workorders.views import LandingPageView

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Landing Page ──
    path('', LandingPageView.as_view(), name='landing'),

    # ── Vistas HTML del taller ──
    path('workorders/', include('workorders.urls')),

    # ── API REST (DRF) ──
    path('api/v1/', include('api.urls')),
]
