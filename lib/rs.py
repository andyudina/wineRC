import random
import math
import re
import datetime
from itertools import chain

#import pandas
import numpy as np
import networkx as nx
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.preprocessing import normalize
from scipy.spatial.distance import cdist

from models import Wine, Feature, Question

SHOW_WINES_NUMBER = 10
QUESTIONS_NUMBER = 4
WINE_SUBSET_RANGE = range(20, 30)
LOG_BASE = 5
RELATIVE_NODES_MX_RATIO = 0.5
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
    
    def __init__(self, wine_names):
        self.features_x,  self.features_y = self._construct_features4wines(wine_names)
        self.graph = self._build_subgraph_by_wines(wine_names)
        
        # initialize seanse
        self.yes_categories = {}
        self.no_categories = {}
        self.answered_questions_number = 0
        self.current_category = None
        self.current_relative_nodes = [] #Nodes which has the same degree as selected one
        
     
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
        
    def _find_next_question_category(self, graph, selected_nodes):
        #return node with maximum degree
        return next(
            node[0] for node in sorted(graph.degree().items(), key=lambda x: x[1], reverse=True)
            if not selected_nodes.get(node[0])
        )
 
    def _round_degrees(self, degrees):
        print(degrees)
        return [[d[0], int(math.log(d[1], LOG_BASE)) / 10 * 10] for d in degrees if d[1] > 0]

        
    def _find_next_question_category_random(self, graph, selected_nodes):
        #return node with maximum degree
        #print(len(graph.nodes()))
        degrees = list(list(n) for n in graph.degree().items() if n[0] not in selected_nodes)
        degrees = self._round_degrees(degrees)
        #rint(degrees)
        max_degree = max(d[1] for d in degrees)
        self.current_relative_nodes = [d[0] for d in degrees if d[1] == max_degree]
        return random.choice(self.current_relative_nodes)
               
    def find_next_question(self):
        category = self._find_next_question_category_random(self.graph, self.yes_categories)
        #print(category)
        question = self.questions.get(category)
        if not question: return
        self.current_category = category
        self.answered_questions_number += 1
        return question.get_random_question()
    
    def _remove_relative_nodes(self):
        for node in self.current_relative_nodes:
            if node == self.current_category: continue
            self.graph.remove_node(node) 
            
    def answer_yes(self):
        #subgraph graph by node
        self.yes_categories[self.current_category] = 1
        #print(self.graph.neighbors(self.current_category))
        if len(self.current_relative_nodes) < RELATIVE_NODES_MX_RATIO * len(self.graph.nodes()):
            self._remove_relative_nodes()   
        self.graph = nx.subgraph(self.graph, self.graph.neighbors(self.current_category)) #nx.node_connected_component(self.graph, self.current_category)) 
        
    def answer_no(self):
        #rm node from graph
        self.no_categories[self.current_category] = 1
        self.graph.remove_node(self.current_category)
        
    def has_next_question(self):
        #graph has nodes
        return (not not [n for n in self.graph.nodes() if not self.yes_categories.get(n)]) \
               and self.answered_questions_number < QUESTIONS_NUMBER
       
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
        
    def find_matches(self):
        answer_vector, indexes = self._form_vector(self.yes_categories, self.no_categories)
        #minimize euclidean_distances
        valuable_features = self.features_x[:, indexes]
        distances = cdist(valuable_features, answer_vector, 'euclidean') 
        wines = np.concatenate((distances, self.features_y, valuable_features), axis=1)
        wines = wines[np.argsort(wines[:, 0])]
        return wines[:, :SHOW_WINES_NUMBER] #TODO: get descriptions
        
  
def generate_random_wines_subset(wines):
    return [random.choice(wines) for i in range(random.choice(WINE_SUBSET_RANGE))] 
    
def ask_question(question):
    answer = input(question + ' [y/n]\n')
    while answer not in ['y', 'n']:
        answer = input('Please, answer question: "{}". Posible answers are "y" on "n"\n'.format(question))
    return (answer == 'y')    

ANSWER_MAP = {
    'да': 1,
    'нет': 2,
    'все равно': 0 
}


def ask_formal_question(question, answers):
    answer = input(question + str(answers) + '\n')
    while answer not in answers:
        answer = input('Please, answer question: "{}". Posible answers are: {}\n'.format(question, str(answers)))
  
    return ANSWER_MAP.get(answer, answer)
         
def select_formal_features(questions):
    result = []
    for question, answers in questions:
        result.append(ask_formal_question(question, answers))
    return result
        
#FORMAL

def _сut_aged_in_oak(style):
    if isinstance(style, list):
        return
    style = [f.strip() for f in style.split(',')]
    features = []
    aged_in_oak = 1
    for i in style:
        if re.search(r'.*не выдерж.*', i):
            aged_in_oak = 1
        elif re.search(r'.*выдерж.*', i):
            aged_in_oak = 2
        elif i:
            features.append(i)
    features[0] = [f.strip() for f in features[0].split(' - ')][1]
    return aged_in_oak, features

def _change_produced_year2vintage(year):
    produced_year = year
    if not produced_year: return
    return datetime.datetime.now().year - int(produced_year)

def select_wine(type, tuples):
    #tnt = tarantool.connect(**TARANTOOL_CONNCTION)
    #offset = 0
    #tuples = tnt.call('wine.find_by_chunk', [offset, 2000, True ]).data
    wines  = []
    for i in tuples:
        oak, style = _сut_aged_in_oak(i[11])
        wine = [i[0], i[2].lower(), i[3].lower(), i[5].lower(), _change_produced_year2vintage(i[10]), oak, style]
        wines.append(wine)
    suitable = []
    for wine in wines:
        temp = 1
        for i in range(1, len(wine)):
            if i == 6 and len(type[i - 1]) != 0 and temp != 0:
                style = wine[i]
                temp = check_style(type[i - 1], style)
            elif i == 4 and type[ i - 1] != 0 and wine[i] == None:
                temp = 0
                break
            elif i == 4 and type[ i - 1] != 0  and not (((wine[i] - int(type[i -1])) >= 0 and int(type[i -1]) > 0) or ((-wine[i] - int(type[i -1])) >= 0 and int(type[i -1]) < 0)):
                temp = 0
            elif wine[i] != type[ i - 1 ] and type[ i - 1] != 0 and i != 6 and i != 4:
                temp = 0
                break
        if temp != 0:
            wine.insert(0, temp)
            suitable.append(wine)
    suitable.sort(reverse=True)
    #for wine in suitable:
        #print(wine)
    results = [s[1] for s in suitable]
    return results

def get_all_style():
    tnt = tarantool.connect(**TARANTOOL_CONNCTION)
    offset = 0
    tuples = tnt.call('wine.find_by_chunk', [offset, 2000, True ]).data
    styles = []
    for i in tuples:
        oak, style = _сut_aged_in_oak(i[11])
        for s in style:
            if s not in styles:
                styles.append(s)
    return styles

def check_style(type, wine):
    check = 0
    for style in type:
        if re.search(r'.*легк.*', style):
            for wine_style in wine:
                if re.search(r'.*мощн.*', wine_style) or re.search(r'.*крепл.*', wine_style) or re.search(r'.*концентр.*', wine_style):
                    return 0
        if re.search(r'.*мощн.*', style) or re.search(r'.*крепл.*', style) or re.search(r'.*концентр.*', style):
            for wine_style in wine:
                if re.search(r'.*легк.*', wine_style):
                    return 0
        if re.search(r'.*кисл.*', style):
            for wine_style in wine:
                if re.search(r'.*кисл.*', wine_style):
                    check += 1
        if style in wine:
            check += 1
    return check
 
FORMAL_QUESTIONS = [
#(белое, красное, розовое), (сухое, сладкое, полусладкое, полусухое), страна, год, выдержка(1 да, 2 нет 0 пофиг), ['стиль', 'стиль']
    ['Красное или белое?', ['белое', 'красное', 'розовое', 'все равно']],
    ['Что насчет сладости?', ['сухое', 'сладкое', 'полусладкое', 'полусухое', 'все равно']],
    ['Любишь выдерженное вино?', ['да', 'нет', 'все равно']]
      
]
    
if __name__ == '__main__':
    features = select_formal_features(FORMAL_QUESTIONS)
    features = features[: 2] + [0, 0] + [features[2], ] + [[], ]
    #print(features) 
    tuples = [Wine.hash2tuple(wine.__dict__) for wine in RS.wines.values()]
    wine_names = select_wine(features, tuples)#generate_random_wines_subset(list(RS.features_raw.index)) #list(RS.wines.keys())) 
    #print(wine_names) 
    rs = RS(wine_names)

    while rs.has_next_question():
        question = rs.find_next_question() 
        #print(question)
        if not question: break
        res = ask_question(question)
        if res:
            rs.answer_yes()
        else:
            rs.answer_no()
    print(rs.find_matches())

#TODO: Multiple answers with values
