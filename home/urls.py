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
    path("booking/<int:booking_id>/", views.booking_details, name="booking_details"),
    path("booking/update/<int:booking_id>/", views.update_booking, name="update_booking"),
    path( "cancel-booking/<int:booking_id>/", views.cancel_booking,name="cancel_booking"),
    path( "emergency/", views.emergency_assistance, name="emergency_assistance"),
    path("hospital/<int:hospital_id>/",views.hospital_details,name="hospital_details"),
    path(
    "profile/",
    views.update_profile,
    name="update_profile"
),
path(
    "verify-luggage-ticket/",
    views.verify_luggage_ticket,
    name="verify_luggage_ticket"
),
path("about/", views.about, name="about"),
path(
    "station-guide/",
    views.station_guide,
    name="station_guide"
),
path(
    "medical-head-login/",
    views.medical_head_login,
    name="medical_head_login"
),
path(
    "medical-head-dashboard/",
    views.medical_head_dashboard,
    name="medical_head_dashboard"
),
path(
    "medical-request/<int:request_id>/respond/",
    views.medical_request_respond,
    name="medical_request_respond"
),

path(
    "medical-request/<int:request_id>/resolve/",
    views.medical_request_resolve,
    name="medical_request_resolve"
),
path(
    "medical-request/update/<int:request_id>/",
    views.update_medical_request,
    name="update_medical_request"
),
path(
    "my-medical-requests/",
    views.my_medical_requests,
    name="my_medical_requests"
),
]