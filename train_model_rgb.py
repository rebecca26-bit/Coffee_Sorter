import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import classification_report
import joblib

# Load normalized training data
df = pd.read_csv("events_labeled_rgb.csv")

X = df[['r','g','b']]
y = df['label']

# No scaler is needed since r,g,b are 0–1 normalized

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.15, random_state=42, stratify=y
)

params = {
    'max_depth': [3, 5, 7, None],
    'min_samples_split': [2, 5, 10]
}

grid = GridSearchCV(
    DecisionTreeClassifier(random_state=42),
    params,
    cv=5
)

grid.fit(X_train, y_train)

print("Best parameters:", grid.best_params_)
predictions = grid.predict(X_test)
print("\nClassification Report:\n")
print(classification_report(y_test, predictions))

joblib.dump({"model": grid.best_estimator_}, "dt_model.joblib")

print("\nModel saved as dt_model.joblib")
