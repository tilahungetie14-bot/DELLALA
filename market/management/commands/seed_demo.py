from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
import os

from market.models import Listing, Service

DEMO = [
    ("house-rent", "rent", "ባለ 2 መኝታ ቤት ለኪራይ", 12000, "በወር", "ቦሌ፣ አዲስ አበባ", "ሰፊ ግቢ፣ የውሃና የኤሌክትሪክ ቆጣሪ የተለየ፣ ፎቅ ላይ።"),
    ("house-sale", "sale", "ባለ 3 መኝታ ቪላ ለሽያጭ", 9500000, "ድርድር አለው", "ባህር ዳር", "G+1 ቪላ፣ 250 ካሬ ቦታ ላይ ያረፈ፣ ካርታ ያለው።"),
    ("car-sale", "sale", "ቶዮታ ኮሮላ 2014 ሞዴል", 1850000, "", "ደብረ ማርቆስ", "ንጹህ፣ ዓመታዊ ምርመራ የተደረገለት፣ ነዳጅ ቆጣቢ።"),
    ("car-rent", "rent", "ሚኒባስ ለቀን ኪራይ", 6000, "በቀን", "ጎንደር", "ለጉብኝት እና ለሠርግ፤ ሹፌር ጋር ወይም ያለ ሹፌር።"),
    ("items", "sale", "ላፕቶፕ HP ProBook", 38000, "", "ደብረ ማርቆስ", "Core i5፣ 8GB RAM፣ 256GB SSD፤ ከአንድ ዓመት ያነሰ ጥቅም ላይ የዋለ።"),
    ("items", "rent", "የሠርግ ድንኳን ለኪራይ", 4500, "በቀን", "ባህር ዳር", "ለ300 ሰው የሚበቃ፣ ወንበር እና ጠረጴዛ ጋር።"),
]


class Command(BaseCommand):
    help = "Create a demo admin account and a few demo listings."

    def handle(self, *args, **options):
        User = get_user_model()
        # Never create a publicly predictable administrator password.
        demo_password = os.environ.get("DELLALA_DEMO_ADMIN_PASSWORD", "")
        if not User.objects.filter(username="admin").exists() and demo_password:
            if len(demo_password) < 12:
                raise CommandError("DELLALA_DEMO_ADMIN_PASSWORD must be at least 12 characters.")
            try:
                validate_password(demo_password)
            except ValidationError as exc:
                raise CommandError("DELLALA_DEMO_ADMIN_PASSWORD is too weak: " + "; ".join(exc.messages)) from exc
            User.objects.create_superuser(
                "admin", "admin@example.com", demo_password, first_name="ደላላ"
            )
            self.stdout.write("Demo admin created. Change its password after first login.")
        elif not User.objects.filter(username="admin").exists():
            self.stdout.write(
                "Demo admin skipped. Set DELLALA_DEMO_ADMIN_PASSWORD (12+ characters) "
                "or run: python manage.py createsuperuser"
            )
        if Listing.objects.exists():
            return
        for slug, deal, title, price, note, loc, desc in DEMO:
            Listing.objects.create(
                title=title, service=Service.objects.get(slug=slug), deal_type=deal, price=price,
                price_note=note, location=loc, description=desc, contact_name="ደላላ", contact_phone="0911000000",
            )
        self.stdout.write(f"Created {len(DEMO)} demo listings.")
