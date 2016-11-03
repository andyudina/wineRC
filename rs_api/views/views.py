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
    #"price": wine.get('price'),
    #'food': wine.get('food'),
    #"year": wine.get('vintage'),
    #"description": wine.get('charateristics'),
    #"color": wine.get('color'),
    #"sweetness": wine.get('switness'),
    #'country': wine.get('country'),
    #'image': wine.get('image'),
    #'style': wine.get('style')
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
        rs.answer_current(int(answer_id))
    if rs.has_next_question():
        try:
            question, possible_answers = rs.find_next_question()
        except (TypeError, ValueError):
            return JsonResponse({
                'question': {},
                "is_end": True
            })            
        #print(question)
        if question == 'price':
            parse_price(possible_answers)
        answers_list = sorted([{ 'id': a , 'text' : possible_answers.get(a)} for a in possible_answers.keys()], key=lambda x: x.get('id'))
        rs.commit_session()
        result = {
            'question': {
                'node': question,
                #'Img': '',
                'answers': answers_list
            },
            "is_end": False
        }
    else:
        result = {
            'question': {},
            "is_end": True
        }
        #rs.commit_session()
    return JsonResponse(result)

def parse_price(answers):
    for k in list(answers):
        if answers.get(k) != 'все равно':
            pass
            if k == '1':
                new_answer = { k : 'меньше ' + str(answers.get(k)[1])}
                answers.update(new_answer)
            elif k == str(len(answers) - 1):
                new_answer = { k : 'от ' + str(answers.get(k)[0])}
                answers.update(new_answer)
            else:
                new_answer = { k : str(answers.get(k)[0]) + ' - ' + str(answers.get(k)[1])}
                answers.update(new_answer)

def get_wine_list(request, user_id):
    if request.method != 'GET':
        return HttpResponseNotAllowed('Method Not Allowed')
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return HttpResponseNotAllowed('Invalid user_id')
    rs = RS(user_id)
    try:
        wines, yes_nodes, no_nodes = rs.find_matches()
        result = {
            'wine': len(wines),
            'yes_nodes': yes_nodes,
            'no_nodes' : no_nodes,
            'wines': [
                _form_wine_description(w)
                for w in wines
            ]
        }
        rs.commit_session()
    except Exception as e:
        result = {
            'wine': 0,
            'wines': []
        }
    return JsonResponse(result)
