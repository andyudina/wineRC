#FORMAL
import re
import datetime
from numpy import percentile

def _сut_aged_in_oak(style):
    if isinstance(style, list):
        return
    style = [f.strip() for f in style.split(',')]
    features = []
    aged_in_oak = 2
    for i in style:
        if re.search(r'.*не выдерж.*', i):
            #aged_in_oak = 2
            aged_in_oak = 'нет'
        elif re.search(r'.*выдерж.*', i):
            #aged_in_oak = 1
            aged_in_oak = 'да'
        elif i:
            features.append(i)
    features[0] = [f.strip() for f in features[0].split(' - ')][1]
    return aged_in_oak, features

def _change_produced_year2vintage(year):
    produced_year = year
    if not produced_year: return
    return datetime.datetime.now().year - int(produced_year)

def _cut_price_range(price_range, price):
    if price_range == 0: return True
    if not price: return False
    bottom = float(price_range[0])
    top = float(price_range[1])
    if (float(price) <= top or top == 0) and float(price) >= bottom:
        return True
    else:
        return False


def get_price_ranges(tuples):
    price_list = [float(t[22])/100 for t in tuples if t[22]]
    #percentiles = [int(round(percentile(price_list, percent),0) * 100 + 100) for percent in (25, 50, 75, 90, 100)]
    percentiles = [int(round(percentile(price_list, percent),0) * 100 + 100) for percent in (40, 70, 100)]
    percentiles.insert(0,0)
    return {str(i) : (percentiles[i - 1], percentiles[i]) for i in range(1, len(percentiles))}

def get_formal_answers(feature, expected_answers, tuples):
    indexes = {'color': 2, 'sweetness': 3, 'aging': 11}
    index = indexes.get(feature)
    if feature == 'price':
        result = get_price_ranges(tuples)
    else:
        result = get_answers(feature, index, expected_answers, tuples)
    if len(result) < 2 : return {'1' : 'все равно'}
    result.update({ str(len(result) + 1) : 'все равно'})
    return result

def cut_price(answer, tuples):
    new_tuple = []
    for t in tuples:
        if _cut_price_range(answer, t[22]):
            new_tuple.append(t)
    return new_tuple

def cut_tuple(feature, answer, tuples):
    if answer == 'все равно':
        new_tuple = tuples
    elif feature == 'price':
        new_tuple = cut_price(answer, tuples)
    else:
        new_tuple = []
        indexes = {'color': 2, 'sweetness': 3, 'aging': 11}
        index = indexes.get(feature)
        for t in tuples:
            temp = t[index]
            if feature == 'aging': temp, style = _сut_aged_in_oak(t[index])
            if temp == answer:
                new_tuple.append(t)
    return new_tuple

def get_answers(feature, index, expected_answers, tuples):
    values = list(expected_answers.values())
    values.remove('все равно')
    result_answers = {}
    i = 1
    for t in tuples:
        if len(values) == 0: break
        temp = t[index]
        if feature == 'aging': temp, style = _сut_aged_in_oak(t[index])
        if temp in values:
            result_answers.update({ str(i) : temp })
            values.remove(temp)
            i += 1
    #if len(result_answers): result_answers.update({ i : 'все равно'})
    return result_answers

#'price', 'color', 'sweetness', 'aging', 'country', 'vintage' ,'styling'
def select_wine(type, tuples):
    wines  = []
    for i in tuples:
        oak, style = _сut_aged_in_oak(i[11])
        price = i[22] if i[22] else 0
        wine = [i[0], price, i[2].lower(), i[3].lower(), oak, i[5].lower(), _change_produced_year2vintage(i[10]),style]
        wines.append(wine)
    suitable = []
    for wine in wines:
        if _cut_price_range(type[0], float(wine[1])):
            temp = 1
            for i in range(2, 6):
                if wine[i] != type[ i - 1 ] and type[ i - 1] != 0:
                    temp = 0
                    break
            if temp == 1: suitable.append(wine)
    results = [s[0] for s in suitable]
    return results

'''def select_wine(type, tuples):
    #tnt = tarantool.connect(**TARANTOOL_CONNCTION)
    #offset = 0
    #tuples = tnt.call('wine.find_by_chunk', [offset, 2000, True ]).data
    wines  = []
    for i in tuples:
        oak, style = _сut_aged_in_oak(i[11])
        price = i[22] if i[22] else 0
        wine = [i[0], i[2].lower(), i[3].lower(), i[5].lower(), _change_produced_year2vintage(i[10]), price, oak, style]
        wines.append(wine)
    suitable = []
    for wine in wines:
        temp = 1
        for i in range(1, 7):
            if i == 5 and _cut_price_range(float(type[4][0]), float(type[4][1]), float(wine[5])) != True:
                temp = 0
                break
            if i == 7 and len(type[i - 1]) != 0 and temp != 0:
                style = wine[i]
                temp = check_style(type[i - 1], style)
            elif i == 4 and type[ i - 1] != 0 and wine[i] == None:
                temp = 0
                break
            elif i == 4 and type[ i - 1] != 0  and not (((wine[i] - int(type[i -1])) >= 0 and int(type[i -1]) > 0) or ((-wine[i] - int(type[i -1])) >= 0 and int(type[i -1]) < 0)):
                temp = 0
            elif wine[i] != type[ i - 1 ] and type[ i - 1] != 0 and i != 7 and i != 4:
                temp = 0
                break
        if temp != 0:
            wine.insert(0, temp)
            suitable.append(wine)
    suitable.sort(reverse=True)
    for w in suitable:
        print(w)
    results = [s[1] for s in suitable]
    return results'''


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
