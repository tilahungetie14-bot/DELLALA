from django.db import migrations

SERVICES = [
    # slug, name, icon, description, fee
    ("house-rent", "ቤት ኪራይ", "🏠", "ቤት ለማከራየት ወይም ለመከራየት", 300),
    ("house-sale", "ቤት ሽያጭ", "🏡", "ቤት ወይም ቦታ ለመሸጥ ወይም ለመግዛት", 500),
    ("car-sale", "መኪና ሽያጭ", "🚗", "መኪና ለመሸጥ ወይም ለመግዛት", 500),
    ("car-rent", "መኪና ኪራይ", "🔑", "መኪና ለማከራየት ወይም ለመከራየት", 300),
    ("items", "የተለያዩ እቃዎች", "📦", "ኤሌክትሮኒክስ፣ ቁሳቁስ፣ የቤት እቃ — ለመሸጥ ወይም ለማከራየት", 150),
    ("other", "ሌላ አገልግሎት", "🤝", "ከላይ ያልተዘረዘረ ማንኛውም ዓይነት ደላላነት", 200),
]

# NOTE: these account numbers are PLACEHOLDERS. Replace them in /admin/ -> የክፍያ አማራጮች before going live.
METHODS = [
    ("ቴሌብር (telebirr)", "ደላላ አገልግሎት", "0900000000", "በቴሌብር መተግበሪያ ወደዚህ ቁጥር ገንዘቡን ይላኩ። ከዚያ የደረሰዎትን የግብይት ቁጥር ያስገቡ።", "#1e88c8"),
    ("የኢትዮጵያ ንግድ ባንክ (CBE)", "ደላላ አገልግሎት", "1000000000000", "ወደዚህ አካውንት ያስገቡ፤ የደረሰኙን ቁጥር ያስገቡ።", "#7a1f6d"),
    ("CBE Birr", "ደላላ አገልግሎት", "0900000000", "", "#a0408f"),
    ("አዋሽ ባንክ", "ደላላ አገልግሎት", "0130000000000", "", "#e8742a"),
    ("አቢሲኒያ ባንክ", "ደላላ አገልግሎት", "00000000", "", "#c9a227"),
    ("ዳሽን ባንክ", "ደላላ አገልግሎት", "0000000000000", "", "#1b4f9c"),
]


def seed(apps, schema_editor):
    Service = apps.get_model("market", "Service")
    PaymentMethod = apps.get_model("market", "PaymentMethod")
    for i, (slug, name, icon, desc, fee) in enumerate(SERVICES):
        Service.objects.get_or_create(
            slug=slug, defaults={"name": name, "icon": icon, "description": desc, "fee": fee, "sort": i}
        )
    for i, (name, acc_name, number, text, color) in enumerate(METHODS):
        PaymentMethod.objects.get_or_create(
            name=name,
            defaults={"account_name": acc_name, "account_number": number, "instructions": text, "color": color, "sort": i},
        )


class Migration(migrations.Migration):
    dependencies = [("market", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
