#!/usr/bin/env python3
"""
train_decision_tree.py
Train decision tree model for coffee bean classification
"""

import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import glob  # For finding files

# Load data (use glob to find the latest CSV file)
csv_files = glob.glob('coffee_training_data_*.csv')
if not csv_files:
    print("No training data CSV files found. Run collect_training_data.py first.")
    exit(1)

# Use the most recent file
latest_file = max(csv_files, key=lambda x: x.split('_')[-1])
print(f"Loading data from: {latest_file}")
data = pd.read_csv(latest_file)

X = data[['Red', 'Green', 'Blue', 'Weight']]  # Features
y = data['Quality'].map({'good': 1, 'bad': 0})  # Labels

# Split data (80% train, 20% test)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train decision tree
model = DecisionTreeClassifier(max_depth=5, random_state=42)  # Adjust max_depth for complexity
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Model Accuracy: {accuracy:.2f}")
print("Classification Report:")
print(classification_report(y_test, y_pred))

# Save model
joblib.dump(model, 'decision_tree_model.pkl')
print("Model saved as 'decision_tree_model.pkl'")
