import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import LabelEncoder

# === STEP 1: Load dataset ===
df = pd.read_csv("test/datadisease.csv")
df.fillna(0, inplace=True)

X = df.drop(['x', 'y', 'location'], axis=1)
y = df['location']

# Encode target labels
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# === STEP 2: Define parameter grid ===
param_grid = {
    "n_estimators": [100, 200, 300],
    "max_depth": [None, 10, 20],
    "min_samples_split": [2, 4],
    "min_samples_leaf": [1, 2],
    "class_weight": [None, "balanced"]
}

# === STEP 3: Set up cross-validation ===
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# === STEP 4: Create GridSearchCV ===
grid_search = GridSearchCV(
    estimator=RandomForestClassifier(random_state=42),
    param_grid=param_grid,
    cv=cv,
    scoring="f1_macro",
    n_jobs=-1,
    verbose=1
)

# === STEP 5: Run GridSearch ===
grid_search.fit(X, y_encoded)

# === STEP 6: Show results for all parameter combinations ===
cv_results = pd.DataFrame(grid_search.cv_results_)

print("\n=== Results for all parameter combinations ===")
for i, row in cv_results.iterrows():
    params = row['params']
    f1_macro = row['mean_test_score']

    # Train model again to check training accuracy
    model = RandomForestClassifier(**params, random_state=42)
    model.fit(X, y_encoded)
    y_pred_train = model.predict(X)
    acc = accuracy_score(y_encoded, y_pred_train)

    print(f" Set {i+1}: {params}")
    print(f"    F1-score (macro): {f1_macro:.4f}")
    print(f"    Accuracy (train): {acc:.4f}")
    print("-" * 60)

# === STEP 7: Show best result ===
print("\n Best Parameters:")
print(grid_search.best_params_)
print(f" Best F1-score (macro avg): {grid_search.best_score_:.4f}")