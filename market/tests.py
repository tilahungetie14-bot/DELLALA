import io

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .forms import normalize_phone
from .models import Listing, PaymentMethod, Service, ServiceRequest

User = get_user_model()


def png(name="x.png"):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "teal").save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT="/tmp/dellala-test-media")
class FlowTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_phone_normalisation(self):
        for raw in ("0912345678", "+251912345678", "251 912-345-678", "912345678"):
            self.assertEqual(normalize_phone(raw), "0912345678")
        self.assertIsNone(normalize_phone("12345"))

    def test_public_pages(self):
        for name in ("home", "listing_list", "login", "register"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        listing = Listing.objects.create(title="T", service=Service.objects.first(), price=1000)
        self.assertEqual(self.client.get(reverse("listing_detail", args=[listing.pk])).status_code, 200)

    def test_full_customer_flow(self):
        # register
        r = self.client.post(reverse("register"), {
            "full_name": "ከበደ አበበ", "phone": "0912345678", "email": "",
            "password1": "Dmu#Safe2026Pass", "password2": "Dmu#Safe2026Pass"})
        self.assertRedirects(r, reverse("dashboard"))
        user = User.objects.get(username="0912345678")
        self.assertEqual(user.first_name, "ከበደ አበበ")
        self.assertContains(self.client.get(reverse("dashboard")), "ቤት ኪራይ")

        # send a request (with photo)
        svc = Service.objects.get(slug="house-rent")
        r = self.client.post(reverse("request_new", args=[svc.slug]), {
            "intent": "rent_out", "title": "ባለ 2 መኝታ", "description": "ሰፊ", "price": "12000",
            "location": "ቦሌ", "contact_phone": "0912345678", "image": png()})
        req = ServiceRequest.objects.get()
        self.assertRedirects(r, reverse("request_pay", args=[req.pk]))
        self.assertEqual(req.fee_amount, svc.fee)

        # pay screen lists telebirr and validates input
        page = self.client.get(reverse("request_pay", args=[req.pk]))
        self.assertContains(page, "ቴሌብር")
        bad = self.client.post(reverse("request_pay", args=[req.pk]), {})
        self.assertEqual(bad.status_code, 200)
        self.assertContains(bad, "የክፍያ አማራጭ ይምረጡ")

        tele = PaymentMethod.objects.get(name__icontains="telebirr")
        r = self.client.post(reverse("request_pay", args=[req.pk]), {
            "payment_method": tele.pk, "payment_ref": "DKE3A7B9XQ", "payment_proof": png("p.png")})
        self.assertRedirects(r, reverse("request_detail", args=[req.pk]))
        req.refresh_from_db()
        self.assertEqual(req.payment_status, "submitted")
        # cannot pay twice
        self.assertRedirects(self.client.get(reverse("request_pay", args=[req.pk])),
                             reverse("request_detail", args=[req.pk]))

        # customers cannot enter the panel
        self.assertEqual(self.client.get(reverse("panel_dashboard")).status_code, 403)
        # nor see other people's requests
        other = User.objects.create_user("0922222222", password="x" * 8)
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("request_detail", args=[req.pk])).status_code, 404)

    def test_admin_flow(self):
        customer = User.objects.create_user("0933333333", password="x" * 8, first_name="ሳራ")
        svc = Service.objects.get(slug="car-sale")
        req = ServiceRequest.objects.create(
            user=customer, service=svc, intent="sell", title="ቶዮታ", price=1500000,
            contact_phone="0933333333", fee_amount=svc.fee, payment_status="submitted",
            image=png("car.png"))
        staff = User.objects.create_user("boss", password="pw123456", is_staff=True)

        # anonymous -> login ; staff logs in with plain username and lands on the panel
        self.assertEqual(self.client.get(reverse("panel_requests")).status_code, 302)
        r = self.client.post(reverse("login"), {"username": "boss", "password": "pw123456"})
        self.assertRedirects(r, reverse("panel_dashboard"))
        self.assertContains(self.client.get(reverse("panel_dashboard")), "የደላላ ፓነል")
        self.assertContains(self.client.get(reverse("panel_requests") + "?payment=submitted"), "ቶዮታ")

        # verify the payment
        r = self.client.post(reverse("panel_request_detail", args=[req.pk]), {
            "status": "approved", "payment_status": "verified", "admin_note": "እናመሰግናለን"})
        self.assertRedirects(r, reverse("panel_request_detail", args=[req.pk]))
        req.refresh_from_db()
        self.assertEqual((req.status, req.payment_status), ("approved", "verified"))

        # add listing prefilled from the request (photo carried over)
        url = reverse("panel_listing_new") + f"?from_request={req.pk}"
        self.assertContains(self.client.get(url), "ቶዮታ")
        r = self.client.post(url, {
            "title": "ቶዮታ ኮሮላ", "service": svc.pk, "deal_type": "sale", "price": "1500000",
            "price_note": "", "location": "ባህር ዳር", "description": "", "contact_name": "ሳራ",
            "contact_phone": "0933333333", "is_active": "on"})
        self.assertRedirects(r, reverse("panel_listings"))
        listing = Listing.objects.get(title="ቶዮታ ኮሮላ")
        self.assertEqual(listing.request, req)
        self.assertTrue(listing.image)

        # edit
        r = self.client.post(reverse("panel_listing_edit", args=[listing.pk]), {
            "title": "ቶዮታ ኮሮላ 2014", "service": svc.pk, "deal_type": "sale", "price": "1400000",
            "price_note": "ድርድር አለው", "location": "ባህር ዳር", "description": "", "contact_name": "ሳራ",
            "contact_phone": "0933333333"})  # is_active omitted -> hidden
        listing.refresh_from_db()
        self.assertEqual(listing.title, "ቶዮታ ኮሮላ 2014")
        self.assertFalse(listing.is_active)
        self.assertNotContains(self.client.get(reverse("listing_list")), "ቶዮታ ኮሮላ 2014")

        # delete
        self.assertEqual(self.client.get(reverse("panel_listing_delete", args=[listing.pk])).status_code, 200)
        self.client.post(reverse("panel_listing_delete", args=[listing.pk]))
        self.assertFalse(Listing.objects.filter(pk=listing.pk).exists())


    def test_registration_rejects_weak_password(self):
        response = self.client.post(reverse("register"), {
            "full_name": "ሙከራ", "phone": "0911111111", "email": "",
            "password1": "12345678", "password2": "12345678",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="0911111111").exists())

    def test_login_is_throttled_after_five_failures(self):
        url = reverse("login")
        for _ in range(5):
            response = self.client.post(url, {"username": "0912345678", "password": "wrong-password"})
            self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {"username": "0912345678", "password": "wrong-password"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ከ15 ደቂቃ በኋላ")

    def test_duplicate_phone_rejected(self):
        User.objects.create_user("0944444444", password="x" * 8)
        r = self.client.post(reverse("register"), {
            "full_name": "A", "phone": "+251944444444", "password1": "Dmu#Safe2026Pass", "password2": "Dmu#Safe2026Pass"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "አስቀድሞ ተመዝግቧል")
