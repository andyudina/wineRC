import csv
import tarantool
from settings import TARANTOOL_CONNCTION, CHUNK_LENGTH

tnt = tarantool.connect(**TARANTOOL_CONNCTION)   
def save_questions2tnt(questions):
    for tuple_ in questions:
        try:
            tnt.call('question.insert_local', [tuple_, ])
        except tarantool.error.DatabaseError as e:
            print(e)
            pass

def load_from_csv(file_name):
    with open(file_name) as csvfile:
        reader = csv.reader(csvfile)
        res =[[row[0], row[2:]] for row in reader]
    return res


           
if __name__ == '__main__':
    questions = load_from_csv('csv/space/questions.csv')
    #print(questions)
    save_questions2tnt(questions)
