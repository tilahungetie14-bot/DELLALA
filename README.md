# ደላላ (Dellala) — የደላላ ድረ-ገጽ

Django (Python) ድረ-ገጽ፦ ቤት ኪራይ/ሽያጭ፣ መኪና ሽያጭ/ኪራይ እና ልዩ ልዩ እቃዎች።

## ማስኬድ

```bash
pip install -r requirements.txt
python manage.py migrate        # ሠንጠረዦችን + አገልግሎቶችን + የክፍያ አማራጮችን ይፈጥራል
python manage.py seed_demo      # (አማራጭ) 6 የሙከራ ዝርዝሮች; admin በተለየ ይፈጠራል
python manage.py runserver
```

ከዚያ http://127.0.0.1:8000 ይክፈቱ።

- Admin ለመፍጠር፦ `python manage.py createsuperuser`። `seed_demo` ከአሁን በኋላ ቀላል/ታዋቂ የDefault Password አይፈጥርም። የDemo admin ካስፈለገ `DELLALA_DEMO_ADMIN_PASSWORD` በEnvironment ውስጥ ቢያንስ 12 ቁምፊ ያለው የይለፍ ቃል ያስቀምጡ።

## ፍሰት

**ደንበኛ**፦ ተመዝገብ (ስልክ ቁጥር + የይለፍ ቃል) → ግባ → አገልግሎት ምረጥ → ዝርዝር ሙላ (መሸጥ/ማከራየት/መግዛት/መከራየት፣ ፎቶ) → ጥያቄ ላክ → ክፍያ (ቴሌብር ወይም ባንክ) → የግብይት ቁጥር አስገባ → ሁኔታውን በ«የእኔ ገጽ» ተከታተል።

**አስተዳዳሪ** (`/panel/`)፦ ጥያቄዎችን ማየት እና ማጣራት፣ ክፍያ ማረጋገጥ/መመለስ፣ ጥያቄውን ወደ ዝርዝር መቀየር፣ ዝርዝር መጨመር / ማስተካከል / ማስወገድ።

## አስፈላጊ — ከመክፈትዎ በፊት

1. **የክፍያ አካውንቶች ምሳሌ ናቸው** (`0900000000` ወዘተ)። በ `/admin/` → «የክፍያ አማራጮች» ውስጥ በእውነተኛ ቴሌብር ቁጥርዎና የባንክ አካውንትዎ ይተኩ።
2. **የአገልግሎት ክፍያ መጠን** (300፣ 500 ብር…) ምሳሌ ነው። በ `/admin/` → «አገልግሎቶች» ይቀይሩ።
3. ክፍያው **በእጅ የሚረጋገጥ** ነው፦ ደንበኛው ከከፈለ በኋላ የግብይት ቁጥር ያስገባል፤ አስተዳዳሪው በፓነሉ ላይ ያረጋግጣል። በራስ-ሰር ለማድረግ (telebirr ክፍያ API) ከቴሌብር ንግድ አካውንት (merchant) ማግኘት ያስፈልጋል።
4. ለእውነተኛ አገልግሎት፦ `DJANGO_DEBUG=0`፣ ጠንካራ `DJANGO_SECRET_KEY`፣ `DJANGO_ALLOWED_HOSTS` እና ካስፈለገ `DJANGO_CSRF_TRUSTED_ORIGINS` ያዘጋጁ። HTTPS ያስፈልጋል፤ `media/` እና static ፋይሎችን በዌብ ሰርቨር ያቅርቡ።
5. የደንበኛ የይለፍ ቃል ቢያንስ 8 ቁምፊ መሆን አለበት፤ በተደጋጋሚ የተሳሳተ Login ከ5 ሙከራ በኋላ ለ15 ደቂቃ ይታገዳል። የLogin rate limit በአንድ የDjango process ውስጥ ነው፤ በብዙ worker የሚሰራ Production ላይ Redis ወይም shared cache ያዋቅሩ።
6. የሚጫኑ ፎቶዎች ከ5 MB መብለጥ የለባቸውም።
