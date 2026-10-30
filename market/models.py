from django.conf import settings
from django.db import models


class Service(models.Model):
    """A service the broker offers (house rent, car sale, ...). The fee is editable in the admin."""

    slug = models.SlugField(unique=True)
    name = models.CharField("ስም", max_length=60)
    icon = models.CharField("ምልክት (emoji)", max_length=8, default="📋")
    description = models.CharField("አጭር መግለጫ", max_length=160, blank=True)
    fee = models.DecimalField("የአገልግሎት ክፍያ (ብር)", max_digits=10, decimal_places=2, default=0)
    sort = models.PositiveSmallIntegerField("ቅደም ተከተል", default=0)
    is_active = models.BooleanField("ንቁ", default=True)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = "አገልግሎት"
        verbose_name_plural = "አገልግሎቶች"

    def __str__(self):
        return self.name


class PaymentMethod(models.Model):
    """A bank / mobile-money account customers can pay into (telebirr, CBE, ...)."""

    name = models.CharField("ስም", max_length=60)
    account_name = models.CharField("የአካውንት ባለቤት ስም", max_length=100)
    account_number = models.CharField("የአካውንት / ስልክ ቁጥር", max_length=40)
    instructions = models.TextField("ተጨማሪ መመሪያ", blank=True)
    color = models.CharField("ቀለም (hex)", max_length=9, default="#0e3b43")
    sort = models.PositiveSmallIntegerField("ቅደም ተከተል", default=0)
    is_active = models.BooleanField("ንቁ", default=True)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = "የክፍያ አማራጭ"
        verbose_name_plural = "የክፍያ አማራጮች"

    def __str__(self):
        return self.name


class ServiceRequest(models.Model):
    class Intent(models.TextChoices):
        SELL = "sell", "መሸጥ እፈልጋለሁ"
        RENT_OUT = "rent_out", "ማከራየት እፈልጋለሁ"
        BUY = "buy", "መግዛት እፈልጋለሁ"
        RENT_IN = "rent_in", "መከራየት እፈልጋለሁ"

    class Status(models.TextChoices):
        PENDING = "pending", "በመጠባበቅ ላይ"
        APPROVED = "approved", "ተቀባይነት አግኝቷል"
        COMPLETED = "completed", "ተጠናቋል"
        REJECTED = "rejected", "ውድቅ ተደርጓል"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "አልተከፈለም"
        SUBMITTED = "submitted", "ክፍያ እየተረጋገጠ ነው"
        VERIFIED = "verified", "ክፍያ ተረጋግጧል"
        REJECTED = "rejected", "ክፍያ አልተረጋገጠም"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="requests"
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="requests")
    intent = models.CharField("ምን ይፈልጋሉ?", max_length=10, choices=Intent.choices)
    title = models.CharField("ርዕስ", max_length=120)
    description = models.TextField("ዝርዝር መግለጫ", blank=True)
    price = models.DecimalField("ዋጋ (ብር)", max_digits=14, decimal_places=2, null=True, blank=True)
    location = models.CharField("አድራሻ / ቦታ", max_length=120, blank=True)
    contact_phone = models.CharField("የመገናኛ ስልክ", max_length=20)
    image = models.ImageField("ፎቶ", upload_to="requests/", blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    admin_note = models.TextField("የአስተዳዳሪ ማስታወሻ", blank=True)

    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="የክፍያ አማራጭ"
    )
    payment_ref = models.CharField("የግብይት ቁጥር", max_length=60, blank=True)
    payment_proof = models.ImageField("የክፍያ ማረጋገጫ ፎቶ", upload_to="proofs/", blank=True)
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "ጥያቄ"
        verbose_name_plural = "ጥያቄዎች"

    def __str__(self):
        return f"#{self.pk} {self.title}"

    @property
    def deal_type(self):
        """Matching Listing deal type when the request is turned into a listing."""
        return Listing.Deal.RENT if self.intent in (self.Intent.RENT_OUT, self.Intent.RENT_IN) else Listing.Deal.SALE

    @property
    def can_pay(self):
        return self.fee_amount > 0 and self.payment_status in (
            self.PaymentStatus.UNPAID,
            self.PaymentStatus.REJECTED,
        )


class Listing(models.Model):
    """An item published on the site. Only the admin adds, edits and removes these."""

    class Deal(models.TextChoices):
        SALE = "sale", "ለሽያጭ"
        RENT = "rent", "ለኪራይ"

    title = models.CharField("ርዕስ", max_length=120)
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name="listings", verbose_name="ዓይነት"
    )
    deal_type = models.CharField("ሽያጭ / ኪራይ", max_length=4, choices=Deal.choices, default=Deal.SALE)
    price = models.DecimalField("ዋጋ (ብር)", max_digits=14, decimal_places=2, null=True, blank=True)
    price_note = models.CharField("የዋጋ ማስታወሻ", max_length=30, blank=True, help_text="ለምሳሌ፦ በወር፣ ድርድር አለው")
    location = models.CharField("አድራሻ / ቦታ", max_length=120, blank=True)
    description = models.TextField("መግለጫ", blank=True)
    image = models.ImageField("ፎቶ", upload_to="listings/", blank=True)
    contact_name = models.CharField("የባለቤት ስም", max_length=80, blank=True)
    contact_phone = models.CharField("የመገናኛ ስልክ", max_length=20, blank=True)
    request = models.ForeignKey(
        ServiceRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="listings"
    )
    is_active = models.BooleanField("በድረ-ገጹ ላይ ይታይ", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "ዝርዝር"
        verbose_name_plural = "ዝርዝሮች"

    def __str__(self):
        return self.title
