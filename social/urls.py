from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.user_register),
    path('login/', views.user_login),
    path('posts/', views.post_list),
    path('posts/<int:pk>/', views.post_detail),
    path('posts/<int:pk>/like/', views.toggle_like),
    path('users/', views.user_list),
    path('users/<str:username>/', views.user_profile),
    path('users/<str:username>/follow/', views.toggle_follow),
    path('profile/bio/', views.update_bio),
]