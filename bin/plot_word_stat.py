import pandas
import tarantool
import matplotlib.pyplot as plt

XTICKS_ROTATION = 17

def load_csv(file_name):
    return pandas.read_csv(file_name).as_matrix()
      
def plot_counters(counters):
    counters = counters[:, 1]
    features = counters[:, 0]
    x = list(range(counters.size))
    
    plt.plot(x, y)
    plt.xticks(x, features,  rotation=XTICKS_ROTATION)
    plt.show()
    
def find_n_max_counters(counters, n):
    return counters[:n, :]
    
def find_n_min_counters(counters, n):
    return counters[:-n, :]

def find_n_middle_counters(counters, n):
    #n should be < rows_number
    rows_number = counters.shape[0]
    return counters[(rows_number - n) / 2: (rows_number + n) / 2, :]
    
