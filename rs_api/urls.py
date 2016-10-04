from django.conf.urls import url
from rs_api.views.views import get_next

urlpatterns = [
    url(r'^api/v1/next/', get_next)
]
