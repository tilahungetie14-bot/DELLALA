import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
import hashlib

from .models import Listing, PaymentMethod, ServiceRequest

User = get_user_model()

PHONE_RE = re.compile(r"^(?:\+?251|0)?([79]\d{8})$")


def normalize_phone(raw):
    """09xx / 07xx / +2519xx / 2519xx  ->  09xxxxxxxx. Returns None if invalid."""
    cleaned = re.sub(r"[\s\-()]", "", raw or "")
    match = PHONE_RE.match(cleaned)
    return "0" + match.group(1) if match else None


class StyledMixin:
    """Adds the CSS classes the templates expect."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.RadioSelect, forms.CheckboxInput)):
                continue
            widget.attrs.setdefault("class", "input")


class RegisterForm(StyledMixin, forms.Form):
    full_name = forms.CharField(label="ሙሉ ስም", max_length=80)
    phone = forms.CharField(
        label="ስልክ ቁጥር",
        max_length=20,
        help_text="ለምሳሌ፦ 0912345678 — በዚህ ቁጥር ይገባሉ",
        widget=forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel"}),
    )
    email = forms.EmailField(label="ኢሜይል (አማራጭ)", required=False)
    password1 = forms.CharField(label="የይለፍ ቃል", widget=forms.PasswordInput, help_text="ቢያንስ 8 ቁምፊ፤ ቀላል ወይም በቁጥር ብቻ የተሰራ የይለፍ ቃል አይጠቀሙ")
    password2 = forms.CharField(label="የይለፍ ቃል ድገም", widget=forms.PasswordInput)

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if not phone:
            raise forms.ValidationError("ትክክለኛ የኢትዮጵያ ስልክ ቁጥር ያስገቡ (ለምሳሌ 0912345678)።")
        if User.objects.filter(username=phone).exists():
            raise forms.ValidationError("ይህ ስልክ ቁጥር አስቀድሞ ተመዝግቧል። ይግቡ።")
        return phone

    def clean(self):
        data = super().clean()
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "ሁለቱ የይለፍ ቃሎች አይመሳሰሉም።")
        if p1 and not self.errors.get("password1"):
            candidate = User(
                username=data.get("phone", ""),
                first_name=data.get("full_name", ""),
                email=data.get("email", ""),
            )
            try:
                validate_password(p1, user=candidate)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return data

    def save(self):
        d = self.cleaned_data
        return User.objects.create_user(
            username=d["phone"],
            password=d["password1"],
            first_name=d["full_name"],
            email=d.get("email", ""),
        )


class LoginForm(StyledMixin, AuthenticationForm):
    MAX_ATTEMPTS = 5
    LOCKOUT_SECONDS = 15 * 60

    username = forms.CharField(
        label="ስልክ ቁጥር",
        widget=forms.TextInput(attrs={"autofocus": True, "inputmode": "tel", "autocomplete": "username"}),
    )
    password = forms.CharField(label="የይለፍ ቃል", widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))
    error_messages = {
        "invalid_login": "ስልክ ቁጥሩ ወይም የይለፍ ቃሉ ትክክል አይደለም። እባክዎ እንደገና ይሞክሩ።",
        "inactive": "ይህ አካውንት ዝግ ነው።",
    }

    def _throttle_key(self, username):
        ip = self.request.META.get("REMOTE_ADDR", "unknown")
        digest = hashlib.sha256(f"{ip}:{username}".encode("utf-8")).hexdigest()
        return f"dellala-login:{digest}"

    def clean(self):
        username = self.cleaned_data.get("username", "")
        if username:
            key = self._throttle_key(username)
            if cache.get(key, 0) >= self.MAX_ATTEMPTS:
                raise forms.ValidationError(
                    "ብዙ ጊዜ ተሳስተዋል። እባክዎ ከ15 ደቂቃ በኋላ እንደገና ይሞክሩ።"
                )
        data = super().clean()
        if self.get_user():
            cache.delete(self._throttle_key(self.cleaned_data.get("username", "")))
        return data

    def clean_username(self):
        raw = self.cleaned_data["username"].strip()
        # Customers log in with a phone number (any format); staff may use a plain username.
        return normalize_phone(raw) or raw

    def record_failed_attempt(self):
        username = self.data.get(self.add_prefix("username"), "").strip()
        username = normalize_phone(username) or username
        if username:
            key = self._throttle_key(username)
            attempts = cache.get(key, 0)
            cache.set(key, attempts + 1, self.LOCKOUT_SECONDS)


MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_image_size(upload):
    if upload and upload.size > MAX_IMAGE_SIZE:
        raise forms.ValidationError("ፎቶው ከ5 MB መብለጥ የለበትም።")
    return upload


class RequestForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ["intent", "title", "description", "price", "location", "contact_phone", "image"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "intent": forms.RadioSelect,
            "image": forms.FileInput(attrs={"accept": "image/*"}),
        }
        labels = {"price": "ዋጋ ወይም በጀት (ብር)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].widget.attrs["placeholder"] = "ለምሳሌ፦ ባለ 2 መኝታ ቤት በቦሌ"
        self.fields["description"].widget.attrs["placeholder"] = "ስፋት፣ ሁኔታ፣ ዓመት፣ ሌሎች ዝርዝሮች…"

    def clean_image(self):
        return validate_image_size(self.cleaned_data.get("image"))

    def clean_contact_phone(self):
        phone = normalize_phone(self.cleaned_data["contact_phone"])
        if not phone:
            raise forms.ValidationError("ትክክለኛ የኢትዮጵያ ስልክ ቁጥር ያስገቡ።")
        return phone


class PaymentForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ["payment_method", "payment_ref", "payment_proof"]
        widgets = {
            "payment_method": forms.RadioSelect,
            "payment_proof": forms.FileInput(attrs={"accept": "image/*"}),
        }
        labels = {"payment_ref": "የግብይት ቁጥር (Transaction ID)", "payment_proof": "የክፍያ ደረሰኝ ፎቶ (አማራጭ)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["payment_method"].queryset = PaymentMethod.objects.filter(is_active=True)
        self.fields["payment_method"].required = True
        self.fields["payment_method"].error_messages["required"] = "የክፍያ አማራጭ ይምረጡ።"
        self.fields["payment_ref"].required = True
        self.fields["payment_ref"].error_messages["required"] = "ከክፍያ በኋላ የደረሰዎትን የግብይት ቁጥር ያስገቡ።"
        self.fields["payment_ref"].widget.attrs["placeholder"] = "ለምሳሌ፦ DKE3A7B9XQ"

    def clean_payment_proof(self):
        return validate_image_size(self.cleaned_data.get("payment_proof"))


class ListingForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Listing
        fields = [
            "title", "service", "deal_type", "price", "price_note", "location",
            "description", "image", "contact_name", "contact_phone", "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "image": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def clean_image(self):
        return validate_image_size(self.cleaned_data.get("image"))


class PanelRequestForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ["status", "payment_status", "admin_note"]
        labels = {"status": "የጥያቄው ሁኔታ", "payment_status": "የክፍያ ሁኔታ"}
        widgets = {"admin_note": forms.Textarea(attrs={"rows": 3})}
