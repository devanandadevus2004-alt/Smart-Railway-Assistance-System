from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login, name="login"),
    path("register/", views.register, name="register"),
    path("logout/", views.logout, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("luggage-booking/", views.luggage_booking, name="luggage_booking"),
    path("my-bookings/",views.my_bookings,name="my_bookings"),
    path("officer-login/", views.officer_login, name="officer_login"),
    path("officer-dashboard/", views.officer_dashboard, name="officer_dashboard"),
]