import random
import math
from itertools import chain

#import pandas
import numpy as np
import networkx as nx
from sklearn.metrics.pairwise import euclidean_distances

from models import Wine, Feature, Question

SHOW_WINES_NUMBER = 10
QUESTIONS_NUMBER = 4
WINE_SUBSET_RANGE = range(20, 30)
LOG_BASE = 5

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
        for d in degrees:
            d[1] = int(math.log(d[1], LOG_BASE)) / 10 * 10 
        return degrees
        
    def _find_next_question_category_random(self, graph, selected_nodes):
        #return node with maximum degree
        #print(len(graph.nodes()))
        degrees = list(list(n) for n in graph.degree().items() if n[0] not in selected_nodes)
        degrees = self._round_degrees(degrees)
        #rint(degrees)
        max_degree = max(d[1] for d in degrees)
        node_candidates = [d[0] for d in degrees if d[1] == max_degree]
        return random.choice(node_candidates)
               
    def find_next_question(self):
        category = self._find_next_question_category_random(self.graph, self.yes_categories)
        #print(category)
        question = self.questions.get(category)
        if not question: return
        self.current_category = category
        self.answered_questions_number += 1
        return question.get_random_question()
    
    def answer_yes(self):
        #subgraph graph by node
        self.yes_categories[self.current_category] = 1
        #print(self.graph.neighbors(self.current_category))
        self.graph = nx.subgraph(self.graph, self.graph.neighbors(self.current_category)) #nx.node_connected_component(self.graph, self.current_category)) 
        
    def answer_no(self):
        #rm node from graph
        self.no_categories[self.current_category] =1
        self.graph.remove_node(self.current_category)
        
    def has_next_question(self):
        #graph has nodes
        #TODO: not self.yes_categories.get(n) 
        return (not not [n for n in self.graph.nodes() if not self.yes_categories.get(n)]) \
               and self.answered_questions_number < QUESTIONS_NUMBER
       
    def _form_vector(self, yes_categories, no_categories):
        res_vector = []
        for category in self.features_names:
            if yes_categories.get(category): res_vector.append(1)
            elif no_categories.get(category): res_vector.append(-1)
            else: res_vector.append(0)
        return np.array(res_vector)
        
    def find_matches(self):
        answer_vector = self._form_vector(self.yes_categories, self.no_categories)
        #minimize euclidean_distances
        distances = euclidean_distances(self.features_x, [answer_vector,]) 
        #print(self.features_x)
        #print(distances)
        #print(distances)
        #print(self.features_y)
        #print(len(self.features_y))
        #print(self.features_y)
        wines = np.concatenate((distances, self.features_y), axis=1)
        wines = np.sort(wines, axis=0) #TODO: check that sort 
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

#TODO: split degrees to groups
#if yes: put all other in group to zero --> and don't ask!   
