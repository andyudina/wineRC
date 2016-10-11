from django.conf.urls import url
from rs_api.views.views import get_next, get_wine_list

urlpatterns = [
    url(r'^api/v1/next/', get_next),
    url(r'^api/v1/wine_list/', get_wine_list)
]
