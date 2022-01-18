import pandas as pd;
from sklearn import linear_model
import pyodbc
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
from sklearn.metrics import mean_squared_error
import numpy as np

def cost(X, y, theta):
    m = len(y)
    J = 0

    h = X * theta
    error = h-y
    J = (1/(2*m))*sum(error^2)
    return J


def gradient_descent(X, y, theta, alpha, iterations):
    m = len(y)
    J_history = X

def test():
    connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
    sql = 'SELECT * FROM BasicSnapshots'
    df = pd.read_sql(sql, connection)
    X = df.drop(['GameId', 'HomeScore', 'AwayScore'], axis=1)
    y = df['HomeScore'] + df['AwayScore']
    x_train, x_test, y_train, y_test = train_test_split(X, y, test_size = 0.2, random_state = 42)

    regr = linear_model.LinearRegression()
    regr.fit(x_train, y_train) 

    y_prediction =  regr.predict(x_test)
    score=r2_score(y_test,y_prediction)
    print('r2 socre is ?',score)
    print('mean_sqrd_error is ?',mean_squared_error(y_test,y_prediction))
    print('root_mean_squared error of is ?', np.sqrt(mean_squared_error(y_test,y_prediction)))
