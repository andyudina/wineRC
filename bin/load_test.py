import mechanize
import time

import requests

BASE_URL = 'http://p30112.lab1.stud.tech-mail.ru/api/v1/next/'

max_session = 1

def _get(payload, timers_dict):
    start_timer = time.time()
    r = requests.get(BASE_URL, params = payload)
    latency = time.time() - start_timer
    timers_dict[str(payload)] = latency
    if r.status_code != requests.codes.ok:
        raise ValueError(r.text)
    return r.json()
    
def _get_url_with_answer(session, timers_dict):
    return _get({'user_id': session, 'answer_id': 1})

def _get_url(session):
    return _get({'user_id': session})
 
    
def _process_session(timers_dict):
    global max_session
    session = max_session
    max_session += 1
    
    response = _get_url(session, timers_dict)
    
    while response.get('question'):
         response = _get_url_with_answer(session, timers_dict)
         
         
class Transaction(object):
    def __init__(self):
        self.custom_timers = {}

    def run(self):
        try:
            _process_session(self.custom_timers)
        except ValueError as e:
            print e.args[0]


if __name__ == '__main__':
    trans = Transaction()
    trans.run()
    print trans.custom_timers    
