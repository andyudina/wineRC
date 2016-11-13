from lib.models import Wine, Feature

if __name__ == '__main__':
    wines = Wine.load_all()
    features = Feature.load_hash()

    wine_keys = list(features.keys())
    for wine, val in wines.items():
        #print(wine)
        if len(wine.split(',')) > 2: continue
        wine_arr = wine.split(',')
        #print(wine_arr)
        if len(wine_arr) == 1:
            for key in wine_keys:            
                if key.startswith(wine) and key != wine:
                    features[key].replace_name(wine)

        else:
            for key in wine_keys:
                if key.startswith(wine_arr[0]) and key.endswith(wine_arr[1]) and key != wine:
                    features[key].replace_name(wine)
        #print(wine)
        #print(val.__dict__)
        #print('------')
