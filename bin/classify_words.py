from itertools import product, chain
from collections import Counter
import csv
import re

import numpy
import networkx as nx
import tarantool
from settings import TARANTOOL_CONNCTION, CHUNK_LENGTH, BAG_OF_WORDS_INDEXES
from sklearn.preprocessing import normalize

SYNONYMS_INTERSECTION_TRESHOLD = 0.8
MAX_MERGE_COUNTS = 100

# 1: name: str
# 2: image_url str
# 3: color: red/white/pink str
# 4: switness: dry/sweet/semi-sweet str
# 5: grape str
# 6: country str
# 7: region str
# 8: alcohol str -> num
# 9: serving temperature str
# 10: decantation str
# 11: vintage num
# 12: ageing str

# [need to be treated as bag of words]
# 13: style
# 14: charateristics
# 15: gastronomy

#[postprocessed results]
# 16: downloaded photo name
# 17: temperature min
# 18: temperature max
# 19: bag of words_style
# 20: bag of words_characteristics
# 21: bag of words_gastronomy
 
# 22: features characteristics
# 23: features gastronomy

tnt = tarantool.connect(**TARANTOOL_CONNCTION)                                  
def load_docs_from_tnt():
    offset = 0
    tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, False ]).data
    
    result_tuples = []
    while len(tuples) > 0 and tuples[0]:
        result_tuples.extend(tuples)
        offset += CHUNK_LENGTH    
        tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, False ]).data       
    return result_tuples

def save_features2tnt(features, labels):
    for tuple_ in features:
        try:
            tnt.call('feature.insert_feature', [[tuple_, ]])
        except tarantool.error.DatabaseError as e:
            print(e)
            pass #its ok to loose some wines
    tnt.call('feature.replace_feature_names', [[list(labels), ]]) 
    
def create_reverse_index(tuples, order):
    index = {}
    for t in tuples:
        name  = t[0]
        for descr in t[order]:
            index[descr] = index.get(descr, set())
            index[descr].add(name)
    return index
 
def _is_valid_row(row):
    return len(row) >= 3 and not re.match('цвет', row[2])   
    
def _form_word_category(row):
    return {
        'labels': ['_'.join(row[2:i]) for i in range(len(row) + 1)],
        'word': row[0]
    }
 
       
def load_word_space(file_name):
    reader = csv.reader(open(file_name))
    word_categories = {}
    for row in reader:
        if row[-1] == '': 
            row = row[: -1]
        if not _is_valid_row(row): continue
        category = _form_word_category(row)
        for label in category['labels']:
            word_categories[label] = word_categories.get(label, {'words': []})
            word_categories[label]['words'].append(category['word']) 

    # delete too broad categories
    for label in ['вкус', 'аромат', '']: 
        try:       
            del word_categories[label]
        except KeyError: pass
    return word_categories
    
def replace_word_with_wine(word_categories, index):
    for label, info in word_categories.items():
         word_categories[label]['wines'] = word_categories[label].get('wines', set())
         for word in info['words']:
             word_categories[label]['wines'].update(set(index.get(word, [])))
    return word_categories    
   
def _are_synonyms(s, d):
    # don't merge verbode subcategories
    if s['label'] in d['label'] or d['label'] in s['label']: return False
    # skip абстрактный
    if 'абстрактный' in s['label'] or 'абстрактный' in d['label']: return False
    intersection_len = float(len(s['wines'] & d['wines']))
    ratios = [ intersection_len / len(category['wines']) for category in [s, d] ]
    for ratio in ratios:
        if ratio >= SYNONYMS_INTERSECTION_TRESHOLD: 
            #print(ratios)
            return True
    return False

def _merge_synonyms(s, d):
    #print(s['label'])
    #print(d['label'])
    #print(s['labels'])
    #print(d['labels'])
    #print(s['wines'])
    #print(d['wines'])
    res_labels = s['labels'] | d['labels']
    return {
        #'labels': s['labels'] | d['labels'],
        #'wines': s['wines'] | d['wines'],
        'labels': [s['label'], d['label']],
        'pair_label': '__'.join(sorted([s['label'], d['label']])),
        'wines_intersect_num': len(s['wines'] & d['wines']),        
        'label': '_'.join(sorted(list(res_labels))),
        'is_synonym_group': True
    }
    
def _find_synonyms(categories):
    syn_groups = []
    uniques = []
    merge_counts = 0
    
    for i, source_category in enumerate(categories):
        was_merged = False
        for j, dest_category in  enumerate(categories[i:]):
            if _are_synonyms(source_category, dest_category):
                merge = _merge_synonyms(source_category, dest_category) 
                categories[i + j] = merge
                was_merged = True
                
        if was_merged: 
            merge_counts += 1
        if merge_counts > MAX_MERGE_COUNTS: break
        if not was_merged and not source_category.get('is_synonym_group'):
            uniques.append(source_category)
    return syn_groups, uniques
            
    
def _word_categories2list(word_categories):
    res = []
    for label, wc in word_categories.items():
        if not wc.get('wines'): continue
        res.append({
            'labels': {label},
            'wines': wc.get('wines'),
            'wines_num': len(wc.get('wines')),
            'label': label,
            'is_synonym_group': False
            })
    return res
    
def _find_synonyms_pairs(wc_list):
    synonyms_raw = [
        _merge_synonyms(*x) for x in product(wc_list, repeat=2)
        if x[0]['label'] != x[1]['label'] and _are_synonyms(*x)
    ]
    
    pair_labels = {}
    synonyms = []
    
    for s in synonyms_raw:
        if not pair_labels.get(s['pair_label']):
            pair_labels[s['pair_label']] = 1
            synonyms.append(s)
            
    synonyms_labels = set(
        list(
            chain.from_iterable(
                 s['labels'] for s in synonyms
            )
        )
    )
    #print(synonyms_labels)
    uniques = [
        x for x in wc_list if x['label'] not in synonyms_labels
    ]
    
    return synonyms, synonyms_labels, uniques
    
def _save_data2csv(f, features):
    with open(f, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for feature in features:
            writer.writerow(feature)
                
def save2csv(keys, list_of_dicts, file_name, **kwargs):
    #print(list_of_dicts[0])
    if kwargs.get('order'):
        list_of_dicts = sorted(list_of_dicts, key=lambda x: x[kwargs.get('order')]) 
        
    features = [
        [d[key] for key in keys]
        for d in list_of_dicts
    ]
    _save_data2csv(file_name, features)
     
def find_synonyms_and_antonyms(word_categories):
    wc_list = _word_categories2list(word_categories)
    #synonyms, unique_words = _find_synonyms(wc_list)
    return _find_synonyms_pairs(wc_list)

def build_word_graph(synonyms, labels):
    word_graph = nx.Graph(name="words")
    word_graph.add_nodes_from(labels)
    for s in synonyms:
        word_graph.add_edge(*s['labels'])
    return word_graph
 
def print_graph2file(g):
    import pydotplus
    from networkx.drawing.nx_pydot import graphviz_layout
    import matplotlib.pyplot as plt
    plt.figure(1, figsize=(8, 8))
    
    # layout graphs with positions using graphviz neato
    pos = graphviz_layout(g, prog="neato")
    # color nodes the same in each connected subgraph
    connected_components = nx.connected_component_subgraphs(g)
    for subgraph in connected_components:
        color = [random.random()] * nx.number_of_nodes(subgraph)
        nx.draw(subgraph,
             pos,
             node_size=40,
             node_color=color,
             vmin=0.0,
             vmax=1.0,
             with_labels=True
             )
    plt.savefig("words_graph.png", dpi=100)
 
def print_graph(G):
    import matplotlib.pyplot as plt
    nx.draw(G)      
    plt.show()
  
def find_graph_stat(G):
    degrees = nx.degree(G)    
    degrees_list = sorted(degrees.items(), key=lambda x: x[1])
    return degrees_list

def _wines2dict(tuples):
    return {t[0]: [t[0], ] for t in tuples}

def _norm_features(features):
    f = numpy.array(features)
    y, x = numpy.split(f, [1, ], axis=1)
    x_norm = normalize(x)
    return numpy.concatenate((y, x_norm), axis=1).tolist()
    
def form_features(tuples, word_categories, s_labels):
    wines_dict = _wines2dict(tuples)
    for label in s_labels:
        wines_set = word_categories[label]['wines']
        for key in wines_dict.keys():
            if key in wines_set:
                wines_dict[key].append(1)
            else:
                wines_dict[key].append(0)
   
    features = _norm_features(list(wines_dict.values()))
    return features    
    
if __name__ == '__main__':
    ORDER = 19
    SPACE_FILE_NAME = 'characteristics.csv'
    FEATURE_ORDER = 21
    tuples = load_docs_from_tnt()
    word_categories = load_word_space('csv/space/{}'.format(SPACE_FILE_NAME))
    index = create_reverse_index(tuples, ORDER)
    word_categories = replace_word_with_wine(word_categories, index)
    #print([[key, len(word_categories[key]['wines'])] for key in word_categories.keys()])
    
    s, s_labels, u = find_synonyms_and_antonyms(word_categories)
    graph = build_word_graph(s, s_labels)
    stat = find_graph_stat(graph)
    #_save_data2csv('csv/space/graph.csv', stat)
    
    features = form_features(tuples, word_categories, s_labels)
    save_features2tnt(features, s_labels)
    #print_graph(graph)
    
    #save2csv(['pair_label', 'wines_intersect_num'], s, 'csv/space/c_synonyms.csv', order='wines_intersect_num')
    #save2csv(['label', 'wines_num'], u, 'csv/space/c_uniques.csv', order='wines_num')
    
    #TODO: построить граф синонимов
