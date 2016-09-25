import random

from models.base import Base

class Question(Base):
    fields = [
         'category',
         'questions'
    ]
    
    @classmethod
    def load_all(cls):
        print('load all questions')
        raw_questions = cls.get_by_chunks('question.find_by_chunk')
        return {t[0]: Question(**cls.tuple2hash(t)) for t in raw_questions}
        
    def get_random_question(self):
        return random.choice(self.questions)     
