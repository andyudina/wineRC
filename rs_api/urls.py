from django.conf.urls import url

from lib.models import Wine, Feature, Question
from rs_api.views.views import get_next, get_wine_list

urlpatterns = [
    url(r'^api/v1/next/', get_next),
    url(r'^api/v1/wine_list/(?P<user_id>\d+)/', get_wine_list)
]


# хак для единовременной загрузки -- очень стремный
initial_data = {
    #wine: {'wine': Wine(categories=[category1, category2], name='wine')}
    'wines': Wine.load_all(),

    #features_raw: [['wine1', [0, 1, .. ]] ...
    'features_raw': Feature.load_all(), # return pandas dataframe
    'features_names': Feature.load_all_names(),

    #questions = ['category': Question(categories=['cat1', 'cat2'])]
    'questions': Question.load_all()
}
