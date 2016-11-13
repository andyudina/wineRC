from django.conf.urls import url

from lib.rs import *
from rs_api.views.views import views_factory#get_next, get_wine_list

urlpatterns = [
    url(r'^api/v1/next/', views_factory('get_next', RS)),
    url(r'^api/v1/wine_list/(?P<user_id>\d+)/', views_factory('get_wine_list', RS))
]

