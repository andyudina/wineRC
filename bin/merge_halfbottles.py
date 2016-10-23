from lib.models import Wine

SYN_TRESHOLD = 0.3

def merge_wine_weights(wines):
    wines_without_weights = {}
    for key, wine in wines.items():
        #Вино Pomino Bianco, 0.75 л., 2015 г.
        wine_name = key.split(',')
        real_name, weight = wine_name[:2]
        year = 'all'
        if len(wine_name) == 3: year = wine_name[2]
        real_name = real_name.strip(' \t\n\r')
        year = year.strip(' \t\n\r')
        wines_without_weights[real_name] = wines_without_weights.get(real_name, {})
        wines_without_weights[real_name][year] = wine
    return wines_without_weights
    
 
def _are_synonums(s, d):
    characteristics = set(s.characteristic_categories + d.characteristic_categories)
    distance = 0
    for c in characteristics: 
        if c not in s.characteristic_categories or c not in d.characteristic_categories:
            distance += 1

    if float(distance) / len(characteristics) < SYN_TRESHOLD: 
        #print('Are synonyms')
        #print(s.name)
        #print(d.name)
        return True
    #print('Not synonyms')
    #print(s.name)
    #print(d.name)
    return False 
    
def merge_wine_years(wines):
    def _hash2list(years):
        return [{'y': key, 'w': val} for key, val in years.items()]
        
    result = {}
    for name, years in wines.items():
        years = _hash2list(years)
        if len(years) == 1: 
            result[name] = years[0]['w']
            continue
        indexes4deletion = {}
        for i, y_source in enumerate(years):
            for j, y_dest in enumerate(years[i + 1: ]):
                if _are_synonums(y_source['w'], y_dest['w']):
                    indexes4deletion[i] = 1
                    break
        years_left = [w for i, w in enumerate(years) if not indexes4deletion.get(i)]
        if len(years_left) == 1: 
            result[name] = years_left[0]['w']
            continue         
        for year in years_left:
            result[', '.join([name, year['y']])] = year['w']
    return result
         
if __name__ == '__main__':
    wines = Wine.load_all()
    wines_without_weights = merge_wine_weights(wines)
    wines = merge_wine_years(wines_without_weights)
    Wine.delete_all()
    for wine, val in wines.items():
        val.name = wine
        val.replace()
        #print(wine)
        #print(val.__dict__)
        #print('------')
