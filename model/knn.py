import pandas as pd 
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import cross_val_predict, GridSearchCV, StratifiedKFold
from sklearn.metrics import (
    confusion_matrix, accuracy_score, precision_score, f1_score, recall_score,classification_report
)
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import confusion_matrix
import joblib as jb
import numpy as np


data = pd.read_csv("C:/LoraProject/LoraProject/csv/data.csv")
data.fillna(0, inplace=True)

x = data.drop(['x', 'y', 'location'], axis=1).values
le = LabelEncoder()
y = data['location']
y_encode = le.fit_transform(y)

model = KNeighborsClassifier(algorithm='auto', leaf_size=40, metric= 'minkowski', n_neighbors= 3, p=1, weights= 'distance')

cv = StratifiedKFold(n_splits=5, shuffle= True, random_state=42)
y_pred = cross_val_predict(model, x, y_encode, cv=cv)

acc = accuracy_score(y_encode , y_pred)
pre = precision_score(y_encode, y_pred, average='macro')
rec = recall_score(y_encode, y_pred, average='macro')
f1 = f1_score(y_encode, y_pred, average='macro')

print("=== Report===")
print(f" Accuracy : {acc:.2%}")
print(f" Precision : {pre:.2%}")
print(f" Recall : {rec:.2%}")
print(f" F1-Score : {f1:.2%}")
print(classification_report(y_encode, y_pred, target_names=le.classes_))

model.fit(x, y_encode)

# บันทึกโมเดลเป็นไฟล์ .pkl
jb.dump(model, "knn.pkl")

# บันทึก LabelEncoder ด้วย (สำคัญสำหรับ decode ตอนใช้งานจริง)
jb.dump(le, "label_encoder.pkl")