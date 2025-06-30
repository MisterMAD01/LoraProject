import pandas as pd 
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import cross_val_predict, cross_val_score
from sklearn.metrics import accuracy_score, classification_report

data = pd.read_csv("./csv/A2.csv")
data.fillna(0, inplace=True)
print(data)
