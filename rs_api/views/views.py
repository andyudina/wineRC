# -*- coding: utf-8 -*-
import json
import random
from django.http import HttpResponse, HttpResponseNotAllowed
from lib.rs import *
from lib.rs import ask_question

def get_next(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed('Method Not Allowed')
    user_id = int(request.GET.get('user_id'))
    answer_id = request.GET.get('answer_id')
    rs = RS(user_id)
    if answer_id: rs.answer_current(int(answer_id))
    if rs.has_next_question():
        question, possible_answers = rs.find_next_question()
        print(question, possible_answers)
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
            'wines': wines
        }
        rs.commit_session()
    return HttpResponse(json.dumps(result))
