import random

import tarantool
from models.base import Base

class Question(Base):
    fields = [
         'category',
         'questions',
    ]
    
    @classmethod
    def load_all(cls):
        print('load all questions')
        raw_questions = cls.get_by_chunks('question.find_by_chunk')
        return {t[0]: Question(**cls.tuple2hash(t)) for t in raw_questions}
        
    def get_random_question(self):
        return random.choice(self.questions)    
        
    def insert(self):
        try:
            #print([[self.category, self.questions],])
            self.tnt.call('question.insert_local', [[self.category, self.questions],])
        except tarantool.error.DatabaseError as e:
            print(e)
            pass         
