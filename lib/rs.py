import random
import math
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
      
if __name__ == '__main__':
    wine_names = generate_random_wines_subset(list(RS.features_raw.index)) #list(RS.wines.keys()))
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
