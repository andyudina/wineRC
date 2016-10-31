from lib.models import Wine

if __name__ == '__main__':
    wines = Wine.load_all()
    wine_keys = list(wines.keys())

    for wine, val in wines.items():
        print(wine)
        if len(wine.split(',')) != 2: continue
        name, year = wine.split(',')
        for key in wine_keys:
            
            if key.startswith(name) and key.endswith(year) and key != wine:
                print(key + '-- yes')
                wines[key].delete()
            else:
                print(key + '--no')
        print('------')
        #print(wine)
        #print(val.__dict__)
        #print('------')
