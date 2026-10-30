from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("listings/", views.listing_list, name="listing_list"),
    path("listings/<int:pk>/", views.listing_detail, name="listing_detail"),
    # customer
    path("dashboard/", views.dashboard, name="dashboard"),
    path("request/new/<slug:slug>/", views.request_new, name="request_new"),
    path("request/<int:pk>/", views.request_detail, name="request_detail"),
    path("request/<int:pk>/pay/", views.request_pay, name="request_pay"),
    # broker panel (staff only)
    path("panel/", views.panel_dashboard, name="panel_dashboard"),
    path("panel/requests/", views.panel_requests, name="panel_requests"),
    path("panel/requests/<int:pk>/", views.panel_request_detail, name="panel_request_detail"),
    path("panel/listings/", views.panel_listings, name="panel_listings"),
    path("panel/listings/new/", views.panel_listing_form, name="panel_listing_new"),
    path("panel/listings/<int:pk>/edit/", views.panel_listing_form, name="panel_listing_edit"),
    path("panel/listings/<int:pk>/delete/", views.panel_listing_delete, name="panel_listing_delete"),
]
