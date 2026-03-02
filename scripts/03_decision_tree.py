"""
================================================================
COFFEE BEAN QUALITY SORTER — STEP 3: DECISION TREE MODEL
Uganda Christian University | Group Trailblazers
S23B23/056 | S23B23/010 | S23B23/046

HOW TO RUN:
  1. Make sure (coffee_env) is active in the terminal
  2. Press Ctrl+` to open terminal in VS Code
  3. Run: python scripts/03_decision_tree.py
  4. Check accuracy results and saved model files

WHAT THIS SCRIPT DOES:
  - Loads the preprocessed sensor data from Step 2
  - Trains a Decision Tree classifier
  - Tunes it using GridSearchCV (finds best settings automatically)
  - Evaluates with accuracy, precision, recall, F1 score
  - Visualises the decision tree structure
  - Saves the final model as models/decision_tree_model.pkl
================================================================
"""

import os
import warnings
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
warnings.filterwarnings("ignore")
plt.style.use("dark_background")

from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree
from sklearn.model_selection import GridSearchCV, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report
)


# ================================================================
# SECTION 1 — LOAD PREPROCESSED DATA
# ================================================================
print("\n" + "="*55)
print("  SECTION 1 — LOADING PREPROCESSED DATA")
print("="*55)

# Check that Step 2 was completed first
required_files = [
    "data/X_train.npy", "data/X_test.npy",
    "data/y_train.npy", "data/y_test.npy",
    "models/scaler.pkl"
]

for f in required_files:
    if not os.path.exists(f):
        print(f"\n  ✗ Missing file: {f}")
        print("  Please run Step 2 first: python scripts/02_data_preprocessing.py")
        exit()

X_train = np.load("data/X_train.npy")
X_test  = np.load("data/X_test.npy")
y_train = np.load("data/y_train.npy")
y_test  = np.load("data/y_test.npy")

print(f"\n  Training set : {X_train.shape[0]} samples, {X_train.shape[1]} features")
print(f"  Test set     : {X_test.shape[0]} samples")
print(f"  Features     : weight_g, red, green, blue")
print(f"  Labels       : 1=good bean, 0=bad bean")
print(f"  Train balance: good={sum(y_train==1)}, bad={sum(y_train==0)}")
print(f"  Test  balance: good={sum(y_test==1)},  bad={sum(y_test==0)}")


# ================================================================
# SECTION 2 — TRAIN A BASELINE DECISION TREE
# ================================================================
print("\n" + "="*55)
print("  SECTION 2 — TRAINING BASELINE DECISION TREE")
print("="*55)

print("\n  Training baseline model (default settings)...")

baseline_model = DecisionTreeClassifier(random_state=42)
baseline_model.fit(X_train, y_train)

baseline_train_acc = accuracy_score(y_train, baseline_model.predict(X_train))
baseline_test_acc  = accuracy_score(y_test,  baseline_model.predict(X_test))

print(f"\n  Baseline Results:")
print(f"    Training accuracy : {baseline_train_acc*100:.2f}%")
print(f"    Test accuracy     : {baseline_test_acc*100:.2f}%")
print(f"    Tree depth        : {baseline_model.get_depth()}")
print(f"    Number of leaves  : {baseline_model.get_n_leaves()}")

if baseline_train_acc > baseline_test_acc + 0.05:
    print(f"\n  ⚠ Gap between train/test accuracy detected.")
    print(f"    This means the tree may be overfitting (memorising training data).")
    print(f"    GridSearchCV in Section 3 will fix this by limiting tree depth.")
else:
    print(f"\n  ✓ Train and test accuracy are close — no overfitting detected.")


# ================================================================
# SECTION 3 — HYPERPARAMETER TUNING WITH GRIDSEARCHCV
# ================================================================
print("\n" + "="*55)
print("  SECTION 3 — HYPERPARAMETER TUNING (GridSearchCV)")
print("="*55)
print("""
  What is hyperparameter tuning?
  A Decision Tree has settings like:
    - max_depth     : how many levels deep the tree grows
    - min_samples_split : minimum samples needed to split a node
    - criterion     : how the tree measures impurity (gini or entropy)

  Instead of guessing the best values, GridSearchCV tests every
  combination automatically and picks the one with the best score.
  This uses 5-fold cross-validation (trains 5 times on different
  data splits to get a reliable average score).
""")

param_grid = {
    "max_depth":          [3, 4, 5, 6, 8, 10, None],
    "min_samples_split":  [2, 5, 10, 20],
    "min_samples_leaf":   [1, 2, 5, 10],
    "criterion":          ["gini", "entropy"]
}

print(f"  Testing {len(param_grid['max_depth']) * len(param_grid['min_samples_split']) * len(param_grid['min_samples_leaf']) * len(param_grid['criterion'])} parameter combinations...")
print(f"  Using 5-fold cross-validation... (this takes ~30 seconds)\n")

grid_search = GridSearchCV(
    DecisionTreeClassifier(random_state=42),
    param_grid,
    cv=5,
    scoring="f1",           # optimise for F1 score (balances precision & recall)
    n_jobs=-1,              # use all CPU cores
    verbose=0
)
grid_search.fit(X_train, y_train)

print(f"  Best parameters found:")
for param, value in grid_search.best_params_.items():
    print(f"    {param:<22} : {value}")

print(f"\n  Best cross-validation F1 score: {grid_search.best_score_*100:.2f}%")


# ================================================================
# SECTION 4 — TRAIN FINAL OPTIMISED MODEL
# ================================================================
print("\n" + "="*55)
print("  SECTION 4 — TRAINING FINAL OPTIMISED MODEL")
print("="*55)

best_model = grid_search.best_estimator_
best_model.fit(X_train, y_train)

y_pred_train = best_model.predict(X_train)
y_pred_test  = best_model.predict(X_test)

train_acc = accuracy_score(y_train, y_pred_train)
test_acc  = accuracy_score(y_test,  y_pred_test)

print(f"\n  Optimised Model Results:")
print(f"    Training accuracy : {train_acc*100:.2f}%")
print(f"    Test accuracy     : {test_acc*100:.2f}%")
print(f"    Tree depth        : {best_model.get_depth()}")
print(f"    Number of leaves  : {best_model.get_n_leaves()}")

# Cross-validation score for reliability
cv_scores = cross_val_score(best_model, X_train, y_train, cv=5, scoring="accuracy")
print(f"\n  5-Fold Cross-Validation:")
print(f"    Scores : {[f'{s*100:.1f}%' for s in cv_scores]}")
print(f"    Mean   : {cv_scores.mean()*100:.2f}%")
print(f"    Std Dev: ±{cv_scores.std()*100:.2f}%")


# ================================================================
# SECTION 5 — EVALUATE THE MODEL
# ================================================================
print("\n" + "="*55)
print("  SECTION 5 — MODEL EVALUATION")
print("="*55)

precision = precision_score(y_test, y_pred_test)
recall    = recall_score(y_test, y_pred_test)
f1        = f1_score(y_test, y_pred_test)
accuracy  = accuracy_score(y_test, y_pred_test)

print(f"""
  What each metric means for a coffee sorter:

  Accuracy  = % of all beans correctly classified
  Precision = of beans predicted 'good', how many were actually good?
              (low precision = good beans wrongly rejected = revenue loss)
  Recall    = of all actual good beans, how many did we correctly find?
              (low recall = defective beans passing through = quality loss)
  F1 Score  = balance between precision and recall (main target metric)

  Results on test set ({X_test.shape[0]} unseen beans):
  ┌─────────────┬──────────┐
  │ Metric      │ Score    │
  ├─────────────┼──────────┤
  │ Accuracy    │ {accuracy*100:>6.2f}%  │
  │ Precision   │ {precision*100:>6.2f}%  │
  │ Recall      │ {recall*100:>6.2f}%  │
  │ F1 Score    │ {f1*100:>6.2f}%  │
  └─────────────┴──────────┘
""")

# Target check
target = 0.90
if test_acc >= target:
    print(f"  ✓ TARGET MET: Accuracy {test_acc*100:.2f}% exceeds the 90% project target!")
else:
    print(f"  ⚠ Accuracy {test_acc*100:.2f}% is below the 90% target.")
    print(f"    This is expected with synthetic data.")
    print(f"    Real sensor data from actual beans will improve accuracy significantly.")

print(f"\n  Full Classification Report:")
print(classification_report(y_test, y_pred_test,
                             target_names=["bad bean (0)", "good bean (1)"]))


# ================================================================
# SECTION 6 — CONFUSION MATRIX CHART
# ================================================================
print("\n" + "="*55)
print("  SECTION 6 — VISUALISATIONS")
print("="*55)

os.makedirs("data", exist_ok=True)

# Chart 1: Confusion Matrix
cm = confusion_matrix(y_test, y_pred_test)
fig1, ax1 = plt.subplots(figsize=(7, 5))
sns.heatmap(cm, annot=True, fmt="d", cmap="Greens",
            xticklabels=["Predicted BAD", "Predicted GOOD"],
            yticklabels=["Actual BAD", "Actual GOOD"],
            ax=ax1, linewidths=1)
ax1.set_title("Confusion Matrix — Decision Tree", fontsize=13,
              fontweight="bold", color="white", pad=15)
ax1.set_ylabel("Actual Label", color="white")
ax1.set_xlabel("Predicted Label", color="white")

# Annotate what each quadrant means
ax1.text(0.5, -0.18,
    f"TN={cm[0,0]} (correctly rejected bad)  FP={cm[0,1]} (bad passed as good)\n"
    f"FN={cm[1,0]} (good wrongly rejected)    TP={cm[1,1]} (correctly passed good)",
    transform=ax1.transAxes, ha="center", fontsize=9,
    color="#6a8a6a", fontfamily="monospace")

plt.tight_layout()
plt.savefig("data/confusion_matrix.png", dpi=150, bbox_inches="tight")
plt.show()
print("  ✓ Saved: data/confusion_matrix.png")

# Chart 2: Feature Importance
fig2, ax2 = plt.subplots(figsize=(8, 5))
feature_names  = ["weight_g", "red", "green", "blue"]
importances    = best_model.feature_importances_
sorted_idx     = np.argsort(importances)[::-1]
bar_colors     = ["#00e676", "#ff5252", "#00b8ff", "#ffab00"]

bars = ax2.bar(
    [feature_names[i] for i in sorted_idx],
    [importances[i]   for i in sorted_idx],
    color=[bar_colors[i] for i in sorted_idx],
    edgecolor="white", linewidth=0.5
)
for bar, imp in zip(bars, [importances[i] for i in sorted_idx]):
    ax2.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 0.005,
             f"{imp*100:.1f}%", ha="center", va="bottom",
             color="white", fontsize=11, fontweight="bold")

ax2.set_title("Feature Importance — Which sensor matters most?",
              fontsize=13, fontweight="bold", color="white")
ax2.set_ylabel("Importance Score", color="white")
ax2.set_xlabel("Sensor Feature", color="white")
ax2.set_ylim(0, max(importances) + 0.1)
plt.tight_layout()
plt.savefig("data/feature_importance.png", dpi=150, bbox_inches="tight")
plt.show()
print("  ✓ Saved: data/feature_importance.png")
print(f"\n  Most important feature: {feature_names[sorted_idx[0]].upper()}")
print(f"  This sensor contributes {importances[sorted_idx[0]]*100:.1f}% to decisions")

# Chart 3: Decision Tree Structure (limited to depth 4 for readability)
fig3, ax3 = plt.subplots(figsize=(22, 10))
plot_tree(
    best_model,
    feature_names=feature_names,
    class_names=["bad", "good"],
    filled=True, rounded=True,
    max_depth=4,              # show top 4 levels only
    fontsize=9,
    ax=ax3,
    impurity=False
)
ax3.set_title(
    "Decision Tree Structure (top 4 levels) — Coffee Bean Classifier",
    fontsize=14, fontweight="bold", color="white", pad=20
)
plt.tight_layout()
plt.savefig("data/decision_tree_structure.png", dpi=120, bbox_inches="tight")
plt.show()
print("  ✓ Saved: data/decision_tree_structure.png")

# Text version of tree rules
print(f"\n  Decision Tree Rules (top 3 levels):")
rules = export_text(best_model, feature_names=feature_names, max_depth=3)
print(rules)


# ================================================================
# SECTION 7 — SAVE THE MODEL
# ================================================================
print("\n" + "="*55)
print("  SECTION 7 — SAVING THE MODEL")
print("="*55)

os.makedirs("models", exist_ok=True)
joblib.dump(best_model, "models/decision_tree_model.pkl")
print(f"\n  ✓ Model saved: models/decision_tree_model.pkl")

# Quick test — reload and predict one bean
loaded_model = joblib.load("models/decision_tree_model.pkl")
scaler       = joblib.load("models/scaler.pkl")

# Simulate one test bean
test_bean = np.array([[0.31, 138, 92, 58]])   # typical good bean values
test_bean_scaled = scaler.transform(test_bean)
prediction       = loaded_model.predict(test_bean_scaled)
confidence       = loaded_model.predict_proba(test_bean_scaled)

print(f"\n  Quick prediction test:")
print(f"    Input  : weight=0.31g, R=138, G=92, B=58")
print(f"    Output : {'GOOD BEAN ✓' if prediction[0]==1 else 'BAD BEAN ✗'}")
print(f"    Confidence: bad={confidence[0][0]*100:.1f}%  good={confidence[0][1]*100:.1f}%")


# ================================================================
# SECTION 8 — FINAL SUMMARY
# ================================================================
print("\n" + "="*55)
print("  STEP 3 COMPLETE — DECISION TREE SUMMARY")
print("="*55)
print(f"""
  MODEL PERFORMANCE:
    Accuracy    : {accuracy*100:.2f}%
    Precision   : {precision*100:.2f}%
    Recall      : {recall*100:.2f}%
    F1 Score    : {f1*100:.2f}%

  MODEL DETAILS:
    Algorithm   : Decision Tree Classifier
    Best depth  : {best_model.get_depth()}
    Leaves      : {best_model.get_n_leaves()}
    Criterion   : {best_model.criterion}
    CV Score    : {cv_scores.mean()*100:.2f}% ± {cv_scores.std()*100:.2f}%

  FILES SAVED:
    models/decision_tree_model.pkl  (main model)
    models/scaler.pkl               (already from Step 2)
    data/confusion_matrix.png
    data/feature_importance.png
    data/decision_tree_structure.png

  READY FOR:
    Step 4 — CNN Image Model
    Step 5 — Model Fusion (combines this + CNN)
    Step 6 — Deploy to Raspberry Pi
""")
print("="*55)