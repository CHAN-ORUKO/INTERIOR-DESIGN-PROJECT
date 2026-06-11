# interior_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('pay/stk/<int:package_id>/', views.trigger_stk_push, name='stk_push'),
    path('pay/callback/', views.mpesa_callback, name='mpesa_callback'),
]