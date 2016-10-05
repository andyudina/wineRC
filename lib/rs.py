# Логика подбора остается здесь

import random
import math
from itertools import chain

#import pandas
import numpy as np
import networkx as nx
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.preprocessing import normalize
from scipy.spatial.distance import cdist

from lib.models import Wine, Feature, Question, Session
from lib.formal_features import select_wine

SHOW_WINES_NUMBER = 10
QUESTIONS_NUMBER = 10
GRAPH_EDGES_TRESHOLD = 10
WINE_SUBSET_RANGE = range(20, 30)
LOG_BASE = 5
RELATIVE_NODES_MX_RATIO = 0.5
FORMAL_FEATURES_DICT = {
    'color': ['Красное или белое?', {'1': 'белое', '2': 'красное', '3': 'розовое', '4': 'все равно'}],
    'sweetness': ['Что насчет сладости?', {'1': 'сухое', '2': 'сладкое', '3': 'полусладкое', '4': 'полусухое', '5': 'все равно'}],
    'aging': ['Любишь выдерженное вино?', {'1': 'да', '2': 'нет', '3': 'все равно'}]
}

DEFAULT_ANSWERS = {'1': 'да', '2': 'нет'}
FORMAL_ANSWER_MAP = {
    'да': 1,
    'нет': 2,
    'все равно': 0 
}

#TODO:
#    Wine:
#        load_all
#        get_category_pairs
#        get_descriptions
#    Feature
#        load_all
#        load_all_names
#    Question
#        load_all
#        get_random_question
       
class RS:
    #wine: {'wine': Wine(categories=[category1, category2], name='wine')}
    wines = Wine.load_all()
    
    #features_raw: [['wine1', [0, 1, .. ]] ...
    features_raw = Feature.load_all() # return pandas dataframe
    features_names = Feature.load_all_names()
    
    #questions = ['category': Question(categories=['cat1', 'cat2'])]
    questions = Question.load_all()
    
    def __init__(self, user_id):
        self._session = Session.get_session(user_id)
        #self.features_x,  self.features_y = self._construct_features4wines(wine_names)
        #self._session.graph = self._build_subgraph_by_wines(wine_names)
        
        # initialize session
        #self.yes_categories = {}
        #self.no_categories = {}
        #self.answered_questions_number = 0
        #self.current_category = None
        #self.current_relative_nodes = [] #Nodes which has the same degree as selected one
    
    def commit_session(self, **kwargs):
        self._session.update(**kwargs)    
     
    def _construct_features4wines(self, wine_names):
        res = self.features_raw.loc[wine_names,]
        return res.as_matrix(), np.array([[val, ] for val in res.index.values])
        
    def _find_category_pairs(self, wine_names):
        category_set = set()
        category_pairs = []
        for wine_name in wine_names:
            wine = self.wines.get(wine_name)
            if not wine: continue
            category_pairs.extend(wine.get_category_pairs())
            category_set.update(wine.characteristic_categories)
        return category_pairs, list(category_set)
        

    def _create_graph(self, pairs, labels):
        word_graph = nx.MultiGraph(name="words")
        word_graph.add_nodes_from(labels)
        for p in pairs:
            word_graph.add_edge(p[0], p[1], key=p[2])
        return word_graph
                   
    def _build_subgraph_by_wines(self, wine_names):
        wine_category_pairs, wine_categories_subset = self._find_category_pairs(wine_names) 
        graph = self._create_graph(wine_category_pairs, list(wine_categories_subset))
        return graph
 
    def _round_degrees(self, degrees):
        #print(degrees)
        return [[d[0], int(math.log(d[1], LOG_BASE)) / 10 * 10] for d in degrees if d[1] > 0]

        
    def _find_next_question_category_random(self, graph, selected_nodes):
        #return node with maximum degree
        #print(len(graph.nodes()))
        degrees = list(list(n) for n in graph.degree().items() if n[0] not in selected_nodes)
        degrees = self._round_degrees(degrees)
        max_degree = max(d[1] for d in degrees)
        self._session.current_relative_nodes = [d[0] for d in degrees if d[1] == max_degree]
        return random.choice(self._session.current_relative_nodes)
               
    def _find_next_taste_question(self):
        category = self._find_next_question_category_random(self._session.graph, self._session.yes_categories)
        #print(category)
        question = self.questions.get(category)
        if not question: return
        self._session.current_question = category
        self._session.answered_questions_number += 1
        return question.get_random_question(), DEFAULT_ANSWERS
    
    def _form_wine_graph(self):
        features = self._session.get_formal_features()
        tuples = [Wine.hash2tuple(wine.__dict__) for wine in self.wines.values()]
        self._session.wine_names = select_wine(features, tuples)
        #print(self._session.wine_names)
        self._session.features_x,  self._session.features_y = self._construct_features4wines(self._session.wine_names)
        self._session.graph = self._build_subgraph_by_wines(self._session.wine_names)
        #print(self._session.graph.nodes)
    
    def find_next_question(self):
        #check formal features first
        formal_feature = self._session.get_next_not_answered_formal_feature()
        if formal_feature:
            self._session.current_question = formal_feature
            return FORMAL_FEATURES_DICT.get(formal_feature)
            
        #if formal features are answered but graph is not initialized
        #TODO: dangerous: assume that wines filtered by formal featrues can never be empty
        if not self._session.wine_names: 
            self._form_wine_graph()
            
        return self._find_next_taste_question()

    def _remove_relative_nodes(self):
        for node in self._session.current_relative_nodes:
            if node == self._session.current_question: continue
            self._session.graph.remove_node(node) 
            
    def _answer_yes(self):
        #subgraph graph by node
        self._session.yes_categories[self._session.current_question] = 1
        if len(self._session.current_relative_nodes) < RELATIVE_NODES_MX_RATIO * len(self._session.graph.nodes()):
            self._remove_relative_nodes()   
        self._session.graph = nx.subgraph(self._session.graph, self._session.graph.neighbors(self._session.current_question))\
        #nx.node_connected_component(self._session.graph, self.current_category)) 
        self.commit_session(fields=['yes_categories', 'graph'])
        
    def _answer_no(self):
        #rm node from graph
        self._session.no_categories[self._session.current_question] = 1
        self._session.graph.remove_node(self._session.current_question)
        self.commit_session(fields=['no_categories', 'graph'])
      
    def answer_current(self, answer):

        if FORMAL_FEATURES_DICT.get(self._session.current_question):
            answer = FORMAL_FEATURES_DICT.get(self._session.current_question)[1].get(answer)
            self._session.update_formal_feature(self._session.current_question, FORMAL_ANSWER_MAP.get(answer, answer))
        else:
            answer = DEFAULT_ANSWERS.get(answer)
            if answer == 'да':
                self._answer_yes()
            elif answer == 'нет':
                self._answer_no()
            else: raise ValueError('Invalid answer')
         
    def has_next_question(self):
        return (
                   #not all formal questions are answeres
                   any(f is None for f in self._session.get_formal_features()) 
               ) or\
               (
                   #graph nodes are more then treshold
                   #answered questions are less then treshold
                   (
                       len([
                               n for n in self._session.graph.edges() 
                               if not self._session.yes_categories.get(n[0]) and not self._session.yes_categories.get(n[1])
                           ]) > GRAPH_EDGES_TRESHOLD
                    ) \
                    and self._session.answered_questions_number < QUESTIONS_NUMBER
               ) or\
               (
                   #transition from formal to taste
                   self._session.answered_questions_number == 0
               )
       
    def _form_vector(self, yes_categories, no_categories):
        res_vector = []
        indexes = []
        for i, category in enumerate(self.features_names):
            if yes_categories.get(category): 
                 indexes.append(i)
                 res_vector.append(1)
            elif no_categories.get(category):
                 indexes.append(i) 
                 res_vector.append(-1)
            #else: res_vector.append(0)
        return np.array([np.array(res_vector)]), indexes
        
    def _get_wines_description(self, wines):
        return [
            self.wines.get(w[1]).__dict__
            for w in wines
        ]
        
    def find_matches(self):
        print(self._session.yes_categories)
        print(self._session.no_categories)
        answer_vector, indexes = self._form_vector(self._session.yes_categories, self._session.no_categories)
        #minimize euclidean_distances
        print(self._session.features_x)
        print(indexes)
        valuable_features = self._session.features_x[:, indexes]
        distances = cdist(valuable_features, answer_vector, 'euclidean') 
        wines = np.concatenate((distances, self._session.features_y, valuable_features), axis=1)
        wines = wines[np.argsort(wines[:, 0])][:, :SHOW_WINES_NUMBER]
        self._session.results = wines.tolist()
        print(wines)
        return self._get_wines_description(wines) #TODO: get descriptions
        
  
def generate_random_wines_subset(wines):
    return [random.choice(wines) for i in range(random.choice(WINE_SUBSET_RANGE))] 
    
def ask_question(question, answers):
    answer = input(question + ' ' + str(answers) + '\n')
    while answer not in answers:
        answer = input('Please, answer question: "{}". Posible answers are: {}\n'.format(question, str(answers)))
    return answer    


#def ask_formal_question(question, answers):
#    answer = input(question + str(answers) + '\n')
#    while answer not in answers:
#        answer = input('Please, answer question: "{}". Posible answers are: {}\n'.format(question, str(answers)))
#  
#    return ANSWER_MAP.get(answer, answer)
         
#def select_formal_features(questions):
#    result = []
#    for question, answers in questions:
#        result.append(ask_formal_question(question, answers))
#    return result
        
     
if __name__ == '__main__':
    USER_ID = 6
    answer = None
    while True:
        rs = RS(USER_ID)
        if answer: rs.answer_current(answer)
        if rs.has_next_question():
            question, possible_answers = rs.find_next_question()
            answer = ask_question(question, possible_answers)
            rs.commit_session()
        else:
            print(rs.find_matches())
            rs.commit_session()
            break
            
    #features = select_formal_features(FORMAL_QUESTIONS)
    #features = features[: 2] + [0, 0] + [features[2], ] + [[], ]
    #print(features) 
    #tuples = [Wine.hash2tuple(wine.__dict__) for wine in RS.wines.values()]
    #wine_names = select_wine(features, tuples)#generate_random_wines_subset(list(RS.features_raw.index)) #list(RS.wines.keys())) 
    #print(wine_names) 
    #rs = RS(wine_names)

    #while rs.has_next_question():
    #    question = rs.find_next_question() 
    #    #print(question)
    #    if not question: break
    #    res = ask_question(question)
    #    if res:
    #        rs.answer_yes()
    #    else:
    #        rs.answer_no()
    #print(rs.find_matches())

#TODO: Multiple answers with values
