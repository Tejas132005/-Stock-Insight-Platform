import matplotlib 
matplotlib.use("Agg")

import matplotlib.pyplot as plt

def plot_history(df, path):
    df.plot(y='Close', title='Closing Price History')
    plt.savefig(path)
    plt.close()

def plot_prediction(actual, predicted, path):
    plt.plot(actual, label='Actual')
    plt.plot(predicted, label='Predicted')
    plt.title('Actual vs Predicted')
    plt.legend()
    plt.savefig(path)
    plt.close()
