#FORMAL
import re
import datetime

def _сut_aged_in_oak(style):
    if isinstance(style, list):
        return
    style = [f.strip() for f in style.split(',')]
    features = []
    aged_in_oak = 2
    for i in style:
        if re.search(r'.*не выдерж.*', i):
            aged_in_oak = 2
        elif re.search(r'.*выдерж.*', i):
            aged_in_oak = 1
        elif i:
            features.append(i)
    features[0] = [f.strip() for f in features[0].split(' - ')][1]
    return aged_in_oak, features

def _change_produced_year2vintage(year):
    produced_year = year
    if not produced_year: return
    return datetime.datetime.now().year - int(produced_year)

def _cut_price_range(bottom, top, price):
    if price <= top and price >= bottom:
        return True
    else:
        return False

def select_wine(type, tuples):
    #tnt = tarantool.connect(**TARANTOOL_CONNCTION)
    #offset = 0
    #tuples = tnt.call('wine.find_by_chunk', [offset, 2000, True ]).data
    wines  = []
    for i in tuples:
        oak, style = _сut_aged_in_oak(i[11])
        price = i[22] if i[22] else 0
        wine = [i[0], i[2].lower(), i[3].lower(), i[5].lower(), _change_produced_year2vintage(i[10]), oak, style, price]
        wines.append(wine)
    suitable = []
    for wine in wines:
        temp = 1
        #if _cut_price_range(1000, 200000, float(wine[7])):
        for i in range(1, 6):
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
    results = [s[1] for s in suitable]
    return results


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
