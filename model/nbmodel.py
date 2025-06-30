import pandas as pd 
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import cross_val_predict , cross_val_predict

data = pd.read_csv("./csv/A1.csv")
data.fillna(0, inplace= True)

#x = data.drop([x],[y], axis=1)
#print(x.head())

