from itertools import product, chain

import networkx as nx

SYNONYMS_INTERSECTION_TRESHOLD = 1

def create_reverse_index(tuples, extract_function):
    index = {}
    for t in tuples:
        name  = extract_function(t, 'name')
        for descr in extract_function(t, 'words'):
            index[descr] = index.get(descr, set())
            index[descr].add(name)
    return index

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

def are_synonyms(s, d, syn_treshold=SYNONYMS_INTERSECTION_TRESHOLD):
    # don't merge verbode subcategories
    if s['label'] in d['label'] or d['label'] in s['label']: return False
    # skip абстрактный
    if 'абстрактный' in s['label'] or 'абстрактный' in d['label']: return False
    intersection_len = float(len(s['wines'] & d['wines']))
    ratios = [ intersection_len / len(category['wines']) for category in [s, d] ]
    for ratio in ratios:
        if ratio >= syn_treshold: 
            return True
    return False

def merge_synonyms(s, d):
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
    
            
def _find_synonyms_pairs(wc_list):
    synonyms_raw = [
        merge_synonyms(*x) for x in product(wc_list, repeat=2)
        if x[0]['label'] != x[1]['label'] and are_synonyms(*x)
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
    
def print_graph(G):
    import matplotlib.pyplot as plt
    nx.draw(G)      
    plt.show()
