import os

from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


class CustomSpectacularSwaggerView(SpectacularSwaggerView):

    template_name = 'new_swagger.html'


urlpatterns = [
    # Hiding admin URL
    path(f"api/{os.environ['DJANGO_ADMIN_KEY']}/", admin.site.urls),

    path('api/v1/jobs/', include('jobs.urls')),
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    # path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/schema/swagger-ui/',
         CustomSpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
