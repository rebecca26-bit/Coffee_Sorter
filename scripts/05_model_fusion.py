"""
================================================================
COFFEE BEAN QUALITY SORTER — STEP 5: MODEL FUSION
Uganda Christian University | Group Trailblazers
S23B23/056 | S23B23/010 | S23B23/046

HOW TO RUN:
  1. Make sure (coffee_env) is active in the terminal
  2. Press Ctrl+` to open terminal in VS Code
  3. Run: python scripts/05_model_fusion.py

WHAT THIS SCRIPT DOES:
  - Loads both trained models (Decision Tree + CNN TFLite)
  - Combines their predictions using 3 fusion strategies
  - Compares all strategies and picks the best one
  - Tests the final fusion system on simulated bean data
  - Saves the fusion configuration for Raspberry Pi deployment
  - Produces a full performance comparison report
================================================================
"""

import os
import warnings
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import json
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
plt.style.use("dark_background")

import tensorflow as tf
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report
)


# ================================================================
# SECTION 1 — LOAD ALL MODELS
# ================================================================
print("\n" + "="*55)
print("  SECTION 1 — LOADING ALL MODELS")
print("="*55)

required_files = [
    "models/decision_tree_model.pkl",
    "models/cnn_model.tflite",
    "models/scaler.pkl",
    "data/X_test.npy",
    "data/y_test.npy"
]

for f in required_files:
    if not os.path.exists(f):
        print(f"\n  ✗ Missing: {f}")
        print("  Please complete Steps 2, 3 and 4 first.")
        exit()

# Load Decision Tree + scaler
dt_model = joblib.load("models/decision_tree_model.pkl")
scaler   = joblib.load("models/scaler.pkl")
print(f"\n  ✓ Decision Tree loaded")
print(f"    Depth   : {dt_model.get_depth()}")
print(f"    Leaves  : {dt_model.get_n_leaves()}")

# Load CNN TFLite interpreter
interpreter = tf.lite.Interpreter(model_path="models/cnn_model.tflite")
interpreter.allocate_tensors()
input_details  = interpreter.get_input_details()
output_details = interpreter.get_output_details()
print(f"\n  ✓ CNN TFLite model loaded")
print(f"    Input shape : {input_details[0]['shape']}")
print(f"    Output shape: {output_details[0]['shape']}")

# Load sensor test data
X_test = np.load("data/X_test.npy")
y_test = np.load("data/y_test.npy")
print(f"\n  ✓ Test data loaded: {X_test.shape[0]} sensor samples")


# ================================================================
# SECTION 2 — HELPER FUNCTIONS
# ================================================================
print("\n" + "="*55)
print("  SECTION 2 — SETTING UP FUSION FUNCTIONS")
print("="*55)

IMG_SIZE = 224

def predict_with_dt(sensor_data_scaled):
    """
    Predict using Decision Tree.
    Input : scaled sensor array shape (n, 4) — [weight, R, G, B]
    Output: probabilities shape (n, 2) — [prob_bad, prob_good]
    """
    return dt_model.predict_proba(sensor_data_scaled)


def predict_with_cnn(image_array):
    """
    Predict using CNN TFLite model.
    Input : normalised image array shape (224, 224, 3) values 0.0-1.0
    Output: float 0.0-1.0 (probability of being a good bean)
    """
    img = np.expand_dims(image_array, axis=0).astype(np.float32)
    interpreter.set_tensor(input_details[0]["index"], img)
    interpreter.invoke()
    prob_good = interpreter.get_tensor(output_details[0]["index"])[0][0]
    return float(prob_good)


def generate_synthetic_image(sensor_row_scaled):
    """
    Generate a synthetic test image based on sensor values.
    In real deployment this is replaced by actual camera capture.
    sensor_row_scaled: array of [weight_scaled, R_scaled, G_scaled, B_scaled]
    """
    # Reverse scale to get approximate RGB range 0-255
    weight_s, r_s, g_s, b_s = sensor_row_scaled

    # Map scaled values back to approximate 0-255 range
    r = int(np.clip((r_s * 30) + 120, 0, 255))
    g = int(np.clip((g_s * 25) + 90,  0, 255))
    b = int(np.clip((b_s * 20) + 60,  0, 255))

    # Create simple bean-shaped image
    from PIL import Image, ImageDraw, ImageFilter
    img  = Image.new("RGB", (IMG_SIZE, IMG_SIZE), color=(20, 12, 6))
    draw = ImageDraw.Draw(img)
    cx, cy = IMG_SIZE//2, IMG_SIZE//2
    draw.ellipse([cx-55, cy-40, cx+55, cy+40], fill=(r, g, b))
    draw.line([cx, cy-35, cx, cy+35],
              fill=(max(0,r-30), max(0,g-20), max(0,b-15)), width=2)
    img = img.filter(ImageFilter.GaussianBlur(radius=1))
    return np.array(img) / 255.0


print("  ✓ predict_with_dt()     — Decision Tree predictor")
print("  ✓ predict_with_cnn()    — CNN TFLite predictor")
print("  ✓ generate_synthetic_image() — test image generator")


# ================================================================
# SECTION 3 — THREE FUSION STRATEGIES
# ================================================================
print("\n" + "="*55)
print("  SECTION 3 — FUSION STRATEGIES EXPLAINED")
print("="*55)
print("""
  We combine the Decision Tree and CNN predictions using
  3 different strategies and compare which works best:

  ┌──────────────────┬────────────────────────────────────────┐
  │ Strategy         │ How it works                           │
  ├──────────────────┼────────────────────────────────────────┤
  │ 1. AND Rule      │ BOTH models must say GOOD for the bean │
  │                  │ to pass. Either saying BAD = rejected. │
  │                  │ Most strict — lowest false pass rate.  │
  ├──────────────────┼────────────────────────────────────────┤
  │ 2. OR Rule       │ Either model saying GOOD = bean passes.│
  │                  │ Most lenient — catches most good beans.│
  ├──────────────────┼────────────────────────────────────────┤
  │ 3. Weighted Avg  │ DT contributes 65%, CNN contributes    │
  │                  │ 35% of the final decision score.       │
  │                  │ DT weighted higher = more reliable     │
  │                  │ with sensor data. Balanced approach.   │
  └──────────────────┴────────────────────────────────────────┘

  For a coffee sorter, Strategy 1 (AND Rule) is safest because
  it minimises defective beans reaching the market.
  Strategy 3 (Weighted Average) balances quality vs yield.
""")


# ================================================================
# SECTION 4 — RUN FUSION ON TEST SET
# ================================================================
print("\n" + "="*55)
print("  SECTION 4 — RUNNING FUSION ON TEST SET")
print("="*55)
print(f"\n  Processing {len(X_test)} beans through fusion pipeline...")
print(f"  (Generating synthetic images for CNN — real deployment uses camera)\n")

# Collect predictions from both models
dt_probs   = []   # Decision Tree probability of being good
cnn_probs  = []   # CNN probability of being good

for i, row in enumerate(X_test):
    # Decision Tree prediction
    prob = predict_with_dt(row.reshape(1, -1))
    dt_probs.append(prob[0][1])   # probability of good (class 1)

    # CNN prediction (using synthetic image based on sensor values)
    img = generate_synthetic_image(row)
    cnn_probs.append(predict_with_cnn(img))

    if (i+1) % 30 == 0:
        print(f"  Processed {i+1}/{len(X_test)} beans...")

dt_probs  = np.array(dt_probs)
cnn_probs = np.array(cnn_probs)

print(f"\n  ✓ All {len(X_test)} beans processed")
print(f"\n  Average DT  confidence (good): {dt_probs.mean()*100:.1f}%")
print(f"  Average CNN confidence (good): {cnn_probs.mean()*100:.1f}%")

# Apply the 3 fusion strategies
# Strategy 1: AND Rule — both must predict good (prob >= 0.5)
y_pred_and = ((dt_probs >= 0.5) & (cnn_probs >= 0.5)).astype(int)

# Strategy 2: OR Rule — either predicts good
y_pred_or  = ((dt_probs >= 0.5) | (cnn_probs >= 0.5)).astype(int)

# Strategy 3: Weighted Average — DT=65%, CNN=35%
DT_WEIGHT  = 0.65
CNN_WEIGHT = 0.35
combined   = (DT_WEIGHT * dt_probs) + (CNN_WEIGHT * cnn_probs)
y_pred_weighted = (combined >= 0.5).astype(int)

# Individual model predictions for comparison
y_pred_dt  = (dt_probs  >= 0.5).astype(int)
y_pred_cnn = (cnn_probs >= 0.5).astype(int)


# ================================================================
# SECTION 5 — COMPARE ALL STRATEGIES
# ================================================================
print("\n" + "="*55)
print("  SECTION 5 — STRATEGY COMPARISON")
print("="*55)

strategies = {
    "Decision Tree only" : y_pred_dt,
    "CNN only"           : y_pred_cnn,
    "Fusion: AND Rule"   : y_pred_and,
    "Fusion: OR Rule"    : y_pred_or,
    "Fusion: Weighted"   : y_pred_weighted,
}

results = {}
print(f"""
  {'Strategy':<22} {'Accuracy':>9} {'Precision':>10} {'Recall':>8} {'F1':>8}
  {'─'*22} {'─'*9} {'─'*10} {'─'*8} {'─'*8}""")

for name, preds in strategies.items():
    acc  = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds, zero_division=0)
    rec  = recall_score(y_test, preds, zero_division=0)
    f1   = f1_score(y_test, preds, zero_division=0)
    results[name] = {"accuracy": acc, "precision": prec,
                     "recall": rec, "f1": f1, "preds": preds}
    marker = " ◄ BEST" if f1 == max(
        f1_score(y_test, p, zero_division=0) for p in strategies.values()
    ) else ""
    print(f"  {name:<22} {acc*100:>8.2f}% {prec*100:>9.2f}% "
          f"{rec*100:>7.2f}% {f1*100:>7.2f}%{marker}")

# Pick best strategy by F1 score
best_name = max(
    [k for k in strategies.keys()],
    key=lambda k: results[k]["f1"]
)
best_preds = results[best_name]["preds"]
print(f"\n  ✓ Best strategy : {best_name}")
print(f"  ✓ Best F1 Score : {results[best_name]['f1']*100:.2f}%")


# ================================================================
# SECTION 6 — DETAILED ANALYSIS OF BEST STRATEGY
# ================================================================
print("\n" + "="*55)
print(f"  SECTION 6 — DETAILED ANALYSIS: {best_name.upper()}")
print("="*55)

best_acc  = results[best_name]["accuracy"]
best_prec = results[best_name]["precision"]
best_rec  = results[best_name]["recall"]
best_f1   = results[best_name]["f1"]
cm        = confusion_matrix(y_test, best_preds)

tn, fp, fn, tp = cm.ravel()

print(f"""
  Confusion Matrix Breakdown:
  ┌─────────────────────────────────────────────┐
  │ True  Negatives (TN) = {tn:>4}                │
  │   Defective beans correctly REJECTED ✓      │
  │                                             │
  │ False Positives (FP) = {fp:>4}                │
  │   Defective beans wrongly PASSED ✗          │
  │   → These reach the market — quality risk   │
  │                                             │
  │ False Negatives (FN) = {fn:>4}                │
  │   Good beans wrongly REJECTED ✗             │
  │   → Revenue loss for farmer                 │
  │                                             │
  │ True  Positives (TP) = {tp:>4}                │
  │   Good beans correctly PASSED ✓             │
  └─────────────────────────────────────────────┘

  False Pass Rate  : {fp/(fp+tn)*100:.1f}% of bad beans slip through
  False Reject Rate: {fn/(fn+tp)*100:.1f}% of good beans wrongly rejected
""")

print(f"  Full report for best strategy:")
print(classification_report(y_test, best_preds,
                             target_names=["bad (0)", "good (1)"],
                             zero_division=0))


# ================================================================
# SECTION 7 — VISUALISATIONS
# ================================================================
print("\n" + "="*55)
print("  SECTION 7 — VISUALISATIONS")
print("="*55)

os.makedirs("data", exist_ok=True)

# Chart 1 — Strategy comparison bar chart
fig1, axes1 = plt.subplots(1, 2, figsize=(14, 6))
fig1.suptitle("Fusion Strategy Comparison — Coffee Bean Sorter",
              fontsize=14, fontweight="bold", color="white")

strategy_names = list(strategies.keys())
accuracies  = [results[s]["accuracy"]*100  for s in strategy_names]
f1_scores   = [results[s]["f1"]*100        for s in strategy_names]
bar_colors  = ["#6a8a6a","#4a6a8a","#00e676","#ffab00","#00b8ff"]

x = np.arange(len(strategy_names))
bars1 = axes1[0].bar(x, accuracies, color=bar_colors,
                      edgecolor="white", linewidth=0.5)
axes1[0].set_title("Accuracy by Strategy", color="white")
axes1[0].set_xticks(x)
axes1[0].set_xticklabels(strategy_names, rotation=20, ha="right", fontsize=9)
axes1[0].set_ylabel("Accuracy %"); axes1[0].set_ylim(0, 110)
axes1[0].axhline(y=90, color="#ff5252", linestyle="--", alpha=0.6, label="90% target")
axes1[0].legend()
for bar, val in zip(bars1, accuracies):
    axes1[0].text(bar.get_x() + bar.get_width()/2,
                  bar.get_height() + 1, f"{val:.1f}%",
                  ha="center", fontsize=9, color="white", fontweight="bold")

bars2 = axes1[1].bar(x, f1_scores, color=bar_colors,
                      edgecolor="white", linewidth=0.5)
axes1[1].set_title("F1 Score by Strategy", color="white")
axes1[1].set_xticks(x)
axes1[1].set_xticklabels(strategy_names, rotation=20, ha="right", fontsize=9)
axes1[1].set_ylabel("F1 Score %"); axes1[1].set_ylim(0, 110)
axes1[1].axhline(y=90, color="#ff5252", linestyle="--", alpha=0.6, label="90% target")
axes1[1].legend()
for bar, val in zip(bars2, f1_scores):
    axes1[1].text(bar.get_x() + bar.get_width()/2,
                  bar.get_height() + 1, f"{val:.1f}%",
                  ha="center", fontsize=9, color="white", fontweight="bold")

plt.tight_layout()
plt.savefig("data/fusion_strategy_comparison.png", dpi=150, bbox_inches="tight")
plt.show()
print("  ✓ Saved: data/fusion_strategy_comparison.png")

# Chart 2 — Best strategy confusion matrix
fig2, ax2 = plt.subplots(figsize=(7, 5))
sns.heatmap(cm, annot=True, fmt="d", cmap="Greens",
            xticklabels=["Predicted BAD", "Predicted GOOD"],
            yticklabels=["Actual BAD", "Actual GOOD"],
            ax=ax2, linewidths=1)
ax2.set_title(f"Fusion Confusion Matrix\n({best_name})",
              fontsize=12, fontweight="bold", color="white", pad=12)
ax2.set_ylabel("Actual Label"); ax2.set_xlabel("Predicted Label")
plt.tight_layout()
plt.savefig("data/fusion_confusion_matrix.png", dpi=150, bbox_inches="tight")
plt.show()
print("  ✓ Saved: data/fusion_confusion_matrix.png")

# Chart 3 — Confidence scatter plot (DT vs CNN)
fig3, ax3 = plt.subplots(figsize=(9, 7))
colors_scatter = ["#ff5252" if y == 0 else "#00e676" for y in y_test]
ax3.scatter(dt_probs, cnn_probs, c=colors_scatter, alpha=0.6, s=40, edgecolors="none")
ax3.axvline(x=0.5, color="#ffffff", linestyle="--", alpha=0.4, linewidth=1)
ax3.axhline(y=0.5, color="#ffffff", linestyle="--", alpha=0.4, linewidth=1)
ax3.set_xlabel("Decision Tree Confidence (good)", fontsize=11)
ax3.set_ylabel("CNN Confidence (good)", fontsize=11)
ax3.set_title("Model Confidence Scatter — DT vs CNN\n(green=good bean, red=bad bean)",
              fontsize=12, fontweight="bold", color="white")
ax3.set_xlim(-0.05, 1.05); ax3.set_ylim(-0.05, 1.05)
ax3.text(0.75, 0.75, "BOTH\nSay GOOD", ha="center", color="#00e676",
         fontsize=9, alpha=0.7)
ax3.text(0.25, 0.25, "BOTH\nSay BAD", ha="center", color="#ff5252",
         fontsize=9, alpha=0.7)
ax3.text(0.75, 0.25, "DT=Good\nCNN=Bad", ha="center", color="#ffab00",
         fontsize=9, alpha=0.7)
ax3.text(0.25, 0.75, "DT=Bad\nCNN=Good", ha="center", color="#ffab00",
         fontsize=9, alpha=0.7)
plt.tight_layout()
plt.savefig("data/fusion_confidence_scatter.png", dpi=150, bbox_inches="tight")
plt.show()
print("  ✓ Saved: data/fusion_confidence_scatter.png")


# ================================================================
# SECTION 8 — SAVE FUSION CONFIGURATION
# ================================================================
print("\n" + "="*55)
print("  SECTION 8 — SAVING FUSION CONFIGURATION")
print("="*55)

fusion_config = {
    "best_strategy"  : best_name,
    "dt_weight"      : DT_WEIGHT,
    "cnn_weight"     : CNN_WEIGHT,
    "threshold"      : 0.5,
    "performance": {
        "accuracy"   : round(best_acc,  4),
        "precision"  : round(best_prec, 4),
        "recall"     : round(best_rec,  4),
        "f1_score"   : round(best_f1,   4)
    },
    "all_strategies": {
        name: {
            "accuracy" : round(results[name]["accuracy"],  4),
            "f1"       : round(results[name]["f1"],        4)
        }
        for name in strategies.keys()
    },
    "models": {
        "decision_tree" : "models/decision_tree_model.pkl",
        "cnn_tflite"    : "models/cnn_model.tflite",
        "scaler"        : "models/scaler.pkl"
    }
}

os.makedirs("models", exist_ok=True)
with open("models/fusion_config.json", "w") as f:
    json.dump(fusion_config, f, indent=2)

print(f"\n  ✓ Saved: models/fusion_config.json")
print(f"\n  Config contents:")
print(json.dumps(fusion_config, indent=4))


# ================================================================
# SECTION 9 — SIMULATE REAL-TIME SORTING
# ================================================================
print("\n" + "="*55)
print("  SECTION 9 — REAL-TIME SORTING SIMULATION")
print("="*55)
print("""
  Simulating the Raspberry Pi sorting 10 beans in real time.
  This is exactly how the system will work on the hardware:
  1. Bean arrives on conveyor
  2. HX711 reads weight, TCS3200 reads R,G,B
  3. Camera captures image
  4. Both models run and fusion decides PASS or REJECT
  5. Servo gate triggered if REJECT
""")

# Simulate 10 beans: 5 good, 5 bad
test_beans = [
    {"weight": 0.31, "R": 140, "G": 93, "B": 59,  "actual": "good"},
    {"weight": 0.12, "R": 198, "G": 202, "B": 172, "actual": "bad"},
    {"weight": 0.33, "R": 135, "G": 89, "B": 55,  "actual": "good"},
    {"weight": 0.08, "R": 38,  "G": 32, "B": 25,  "actual": "bad"},
    {"weight": 0.30, "R": 142, "G": 95, "B": 61,  "actual": "good"},
    {"weight": 1.20, "R": 110, "G": 100, "B": 88,  "actual": "bad"},
    {"weight": 0.35, "R": 138, "G": 91, "B": 57,  "actual": "good"},
    {"weight": 0.17, "R": 62,  "G": 48, "B": 36,  "actual": "bad"},
    {"weight": 0.29, "R": 145, "G": 97, "B": 63,  "actual": "good"},
    {"weight": 0.19, "R": 205, "G": 208, "B": 178, "actual": "bad"},
]

print(f"  {'Bean':<6} {'Weight':>8} {'R':>5} {'G':>5} {'B':>5} "
      f"{'DT':>8} {'CNN':>8} {'Fusion':>10} {'Actual':>8} {'Result':>8}")
print(f"  {'─'*6} {'─'*8} {'─'*5} {'─'*5} {'─'*5} "
      f"{'─'*8} {'─'*8} {'─'*10} {'─'*8} {'─'*8}")

correct = 0
for i, bean in enumerate(test_beans):
    # Scale sensor values
    raw    = np.array([[bean["weight"], bean["R"], bean["G"], bean["B"]]])
    scaled = scaler.transform(raw)

    # DT prediction
    dt_prob   = predict_with_dt(scaled)[0][1]
    dt_label  = "GOOD" if dt_prob >= 0.5 else "BAD"

    # CNN prediction
    img       = generate_synthetic_image(scaled[0])
    cnn_prob  = predict_with_cnn(img)
    cnn_label = "GOOD" if cnn_prob >= 0.5 else "BAD"

    # Weighted fusion decision
    fusion_score = DT_WEIGHT * dt_prob + CNN_WEIGHT * cnn_prob
    fusion_label = "PASS ✓" if fusion_score >= 0.5 else "REJECT ✗"
    fusion_correct = (fusion_score >= 0.5) == (bean["actual"] == "good")
    if fusion_correct: correct += 1

    print(f"  Bean {i+1:<2} {bean['weight']:>7.2f}g {bean['R']:>5} "
          f"{bean['G']:>5} {bean['B']:>5} {dt_label:>8} {cnn_label:>8} "
          f"{fusion_label:>10} {bean['actual'].upper():>8} "
          f"{'✓' if fusion_correct else '✗':>8}")

print(f"\n  Simulation accuracy: {correct}/10 beans correctly sorted ({correct*10}%)")


# ================================================================
# SECTION 10 — FINAL SUMMARY
# ================================================================
print("\n" + "="*55)
print("  STEP 5 COMPLETE — MODEL FUSION SUMMARY")
print("="*55)
print(f"""
  FUSION PERFORMANCE (best strategy: {best_name}):
    Accuracy    : {best_acc*100:.2f}%
    Precision   : {best_prec*100:.2f}%
    Recall      : {best_rec*100:.2f}%
    F1 Score    : {best_f1*100:.2f}%

  FUSION LOGIC:
    Decision Tree weight : {DT_WEIGHT*100:.0f}%
    CNN weight           : {CNN_WEIGHT*100:.0f}%
    Decision threshold   : 0.5

  FILES SAVED:
    models/fusion_config.json
    data/fusion_strategy_comparison.png
    data/fusion_confusion_matrix.png
    data/fusion_confidence_scatter.png

  ALL MODEL FILES READY FOR DEPLOYMENT:
    models/decision_tree_model.pkl
    models/cnn_model.tflite
    models/scaler.pkl
    models/fusion_config.json

  READY FOR:
    Step 6 — Deploy to Raspberry Pi
    (copy models/ folder to Pi and run sorter_main.py)
""")
print("="*55)