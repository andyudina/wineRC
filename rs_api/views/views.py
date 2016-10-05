# -*- coding: utf-8 -*-
import random
from django.http import JsonResponse, HttpResponseNotAllowed
from lib.rs import *
#from lib.rs import ask_question

def _form_wine_description(wine):
    #return {key: wine.get(key) for key in ['title', 'description', 'sweetness', 'color', 'year', 'price']}
    #print(wine)
    return {
    "title": wine.get('name'),
    "price": None,
    "year": wine.get('vintage'),
    "description": wine.get('charateristics'),
    "color": "белое",
    "sweetness": wine.get('switness')
    }
    
def get_next(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed('Method Not Allowed')
    try:
        user_id = int(request.GET.get('user_id'))
    except (ValueError, TypeError):
        return HttpResponseNotAllowed('Invalid user_id')
    answer_id = request.GET.get('answer_id')
    rs = RS(user_id)
    if answer_id: 
        print(answer_id)
        rs.answer_current(int(answer_id))
    if rs.has_next_question():
        question, possible_answers = rs.find_next_question()
        #print(question, possible_answers)
        rs.commit_session()
        result = {
            'question': {
                'text': question,
                'Img': '',
                'answers': [possible_answers]
            }
        }
    else:
        wines = rs.find_matches()
        result = {
            'wine': len(wines),
            'wines': [
                _form_wine_description(w)
                for w in wines
            ]
        }
        rs.commit_session()
    return JsonResponse(result)
