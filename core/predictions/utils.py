import yfinance as yf
import numpy as np
from sklearn.preprocessing import MinMaxScaler

def fetch_data(ticker):
    df = yf.download(ticker, period="10y")
    df = df[['Close']].dropna()
    return df


def preprocess(df):
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df)

    X = []
    y = []

    for i in range(60, len(scaled)):
        X.append(scaled[i-60:i])
        y.append(scaled[i])

    return np.array(X), np.array(y), scaler
