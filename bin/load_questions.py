import csv

from lib.models import Wine, Question

BASE_QUESTION_ROW_LEN = 3

def load_from_csv(file_name):
    questions = []
    categories = {}
    with open(file_name) as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            questions.append(Question(category=row[0], questions=[row[2], ]))
            categories[row[0]] = row[0]
            if len(row) > BASE_QUESTION_ROW_LEN:
                for category in row[3:]:
                    if not category: continue
                    categories[category] = row[0]
            
    return questions, categories
 
def replace_characteristics(source, category_index):
    return [category_index.get(category) for category in source if category_index.get(category)]
             
if __name__ == '__main__':
    questions, category_index = load_from_csv('csv/space/questions.csv')
    
    for q in questions:
        q.insert()
        
    #print(questions)
    wines = Wine.load_all()
    
    for wine in wines.values():
        categories = replace_characteristics(wine.characteristic_categories, category_index)
        #if categories != wine.characteristic_categories:
        #    print('----')
        #    print(categories)
        #    print(wine.characteristic_categories)
        wine.update(fields='characteristic_categories')
    
