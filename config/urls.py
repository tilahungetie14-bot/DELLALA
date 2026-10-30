from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "ደላላ – አስተዳደር"
admin.site.site_title = "ደላላ"
admin.site.index_title = "አገልግሎቶች፣ የክፍያ አማራጮች እና ተጠቃሚዎች"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("market.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
