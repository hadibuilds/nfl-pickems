# dashboard/urls.py
from django.urls import path
from .views import home_top3_api

urlpatterns = [
    path("api/home-top3/", home_top3_api, name="home_top3"),
]
