from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import (
    ListingForm,
    LoginForm,
    PanelRequestForm,
    PaymentForm,
    RegisterForm,
    RequestForm,
)
from .models import Listing, PaymentMethod, Service, ServiceRequest

User = get_user_model()


def staff_required(view):
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def paginate(request, queryset, per_page):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


# ---------------------------------------------------------------- public pages

def home(request):
    return render(
        request,
        "market/home.html",
        {
            "services": Service.objects.filter(is_active=True),
            "latest": Listing.objects.filter(is_active=True).select_related("service")[:6],
        },
    )


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"እንኳን ደህና መጡ {user.first_name}! አካውንትዎ ተከፍቷል።")
        return redirect("dashboard")
    return render(request, "market/register.html", {"form": form})


class CustomLoginView(LoginView):
    template_name = "market/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_invalid(self, form):
        if isinstance(form, LoginForm):
            form.record_failed_attempt()
        return super().form_invalid(form)

    def get_default_redirect_url(self):
        return reverse("panel_dashboard" if self.request.user.is_staff else "dashboard")


def listing_list(request):
    qs = Listing.objects.filter(is_active=True).select_related("service")
    q = request.GET.get("q", "").strip()
    service = request.GET.get("service", "")
    deal = request.GET.get("deal", "")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(location__icontains=q) | Q(description__icontains=q))
    if service:
        qs = qs.filter(service__slug=service)
    if deal in Listing.Deal.values:
        qs = qs.filter(deal_type=deal)
    return render(
        request,
        "market/listing_list.html",
        {
            "page": paginate(request, qs, 12),
            "services": Service.objects.filter(is_active=True),
            "q": q,
            "service_sel": service,
            "deal_sel": deal,
            "deals": Listing.Deal.choices,
        },
    )


def listing_detail(request, pk):
    listing = get_object_or_404(Listing.objects.select_related("service"), pk=pk, is_active=True)
    related = (
        Listing.objects.filter(is_active=True, service=listing.service)
        .exclude(pk=listing.pk)
        .select_related("service")[:3]
    )
    return render(request, "market/listing_detail.html", {"listing": listing, "related": related})


# ------------------------------------------------------------------- customer

@login_required
def dashboard(request):
    if request.user.is_staff:
        return redirect("panel_dashboard")
    return render(
        request,
        "market/dashboard.html",
        {
            "services": Service.objects.filter(is_active=True),
            "my_requests": ServiceRequest.objects.filter(user=request.user).select_related("service"),
        },
    )


@login_required
def request_new(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    phone = request.user.username if request.user.username.isdigit() else ""
    form = RequestForm(request.POST or None, request.FILES or None, initial={"contact_phone": phone})
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.service = service
        obj.fee_amount = service.fee
        if service.fee <= 0:
            obj.payment_status = ServiceRequest.PaymentStatus.VERIFIED
        obj.save()
        if obj.can_pay:
            messages.success(request, "ጥያቄዎ ተልኳል። አሁን የአገልግሎት ክፍያውን ይፈጽሙ።")
            return redirect("request_pay", pk=obj.pk)
        messages.success(request, "ጥያቄዎ ተልኳል። ደላላው በቅርብ ጊዜ ያነጋግርዎታል።")
        return redirect("request_detail", pk=obj.pk)
    return render(request, "market/request_form.html", {"form": form, "service": service})


@login_required
def request_detail(request, pk):
    req = get_object_or_404(ServiceRequest.objects.select_related("service", "payment_method"), pk=pk, user=request.user)
    return render(request, "market/request_detail.html", {"req": req})


@login_required
def request_pay(request, pk):
    req = get_object_or_404(ServiceRequest.objects.select_related("service"), pk=pk, user=request.user)
    if not req.can_pay:
        messages.info(request, "ለዚህ ጥያቄ ክፍያ አስቀድሞ ተልኳል።")
        return redirect("request_detail", pk=req.pk)
    form = PaymentForm(request.POST or None, request.FILES or None, instance=req)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.payment_status = ServiceRequest.PaymentStatus.SUBMITTED
        obj.save()
        messages.success(request, "የክፍያ መረጃዎ ተልኳል። ደላላው አረጋግጦ ያሳውቅዎታል።")
        return redirect("request_detail", pk=req.pk)
    return render(
        request,
        "market/request_pay.html",
        {"req": req, "form": form, "methods": PaymentMethod.objects.filter(is_active=True)},
    )


# ---------------------------------------------------------------- broker panel

@staff_required
def panel_dashboard(request):
    Pay = ServiceRequest.PaymentStatus
    revenue = ServiceRequest.objects.filter(payment_status=Pay.VERIFIED).aggregate(t=Sum("fee_amount"))["t"] or 0
    stats = {
        "pending": ServiceRequest.objects.filter(status=ServiceRequest.Status.PENDING).count(),
        "to_verify": ServiceRequest.objects.filter(payment_status=Pay.SUBMITTED).count(),
        "listings": Listing.objects.filter(is_active=True).count(),
        "customers": User.objects.filter(is_staff=False).count(),
        "revenue": revenue,
    }
    recent = ServiceRequest.objects.select_related("service", "user")[:8]
    return render(request, "market/panel_dashboard.html", {"stats": stats, "recent": recent})


@staff_required
def panel_requests(request):
    qs = ServiceRequest.objects.select_related("service", "user")
    status = request.GET.get("status", "")
    pay = request.GET.get("payment", "")
    q = request.GET.get("q", "").strip()
    if status in ServiceRequest.Status.values:
        qs = qs.filter(status=status)
    if pay in ServiceRequest.PaymentStatus.values:
        qs = qs.filter(payment_status=pay)
    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__username__icontains=q)
            | Q(payment_ref__icontains=q)
        )
    return render(
        request,
        "market/panel_requests.html",
        {
            "page": paginate(request, qs, 20),
            "q": q,
            "status_sel": status,
            "pay_sel": pay,
            "statuses": ServiceRequest.Status.choices,
            "pay_statuses": ServiceRequest.PaymentStatus.choices,
        },
    )


@staff_required
def panel_request_detail(request, pk):
    req = get_object_or_404(ServiceRequest.objects.select_related("service", "user", "payment_method"), pk=pk)
    form = PanelRequestForm(request.POST or None, instance=req)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "ለውጦቹ ተቀምጠዋል።")
        return redirect("panel_request_detail", pk=req.pk)
    return render(
        request,
        "market/panel_request_detail.html",
        {"req": req, "form": form, "listings": req.listings.all()},
    )


@staff_required
def panel_listings(request):
    qs = Listing.objects.select_related("service")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(location__icontains=q) | Q(contact_name__icontains=q))
    return render(request, "market/panel_listings.html", {"page": paginate(request, qs, 20), "q": q})


@staff_required
def panel_listing_form(request, pk=None):
    listing = get_object_or_404(Listing, pk=pk) if pk else None
    source = None
    initial = {}
    if listing is None and request.GET.get("from_request", "").isdigit():
        source = get_object_or_404(ServiceRequest.objects.select_related("user"), pk=request.GET["from_request"])
        initial = {
            "title": source.title,
            "service": source.service_id,
            "deal_type": source.deal_type,
            "price": source.price,
            "location": source.location,
            "description": source.description,
            "contact_name": source.user.first_name or source.user.username,
            "contact_phone": source.contact_phone,
        }
    form = ListingForm(request.POST or None, request.FILES or None, instance=listing, initial=initial)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if source:
            obj.request = source
            if not obj.image and source.image:
                obj.image.name = source.image.name
        obj.save()
        if source and source.status == ServiceRequest.Status.PENDING:
            source.status = ServiceRequest.Status.APPROVED
            source.save(update_fields=["status", "updated_at"])
        messages.success(request, "ዝርዝሩ ተቀምጧል።")
        return redirect("panel_listings")
    return render(request, "market/panel_listing_form.html", {"form": form, "listing": listing, "source": source})


@staff_required
def panel_listing_delete(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if request.method == "POST":
        listing.delete()
        messages.success(request, "ዝርዝሩ ተወግዷል።")
        return redirect("panel_listings")
    return render(request, "market/panel_confirm_delete.html", {"listing": listing})
