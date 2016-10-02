import csv
import random

from lib.models import Wine
from utils.words_graph import create_reverse_index, build_word_graph, print_graph, find_synonyms_and_antonyms
 
def generate_random_wines_subset(wines):
    keys = list(wines.keys())
    random_keys = [random.choice(keys) for i in range(random.choice(range(10, 200)))]
    return {key: wines[key] for key in random_keys} 
                
if __name__ == '__main__':
    wines = generate_random_wines_subset(Wine.load_all())
    
    def extract_function(wine, field):
        if field == 'words': field = 'characteristic_categories'
        return getattr(wine, field)
    index = create_reverse_index(list(wines.values()), extract_function)
    index = { key: {'wines': value, 'label': value} for key, value in index.items()}
    #print([[key, len(word_categories[key]['wines'])] for key in word_categories.keys()])
    
    s, s_labels, u = find_synonyms_and_antonyms(index)
    graph = build_word_graph(s, s_labels)
    print_graph(graph)
    
