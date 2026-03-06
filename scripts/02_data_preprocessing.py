"""
================================================================
COFFEE BEAN QUALITY SORTER — STEP 2: DATA PREPROCESSING
Uganda Christian University | Group Trailblazers
S23B23/056 | S23B23/010 | S23B23/046

HOW TO RUN:
  1. Make sure (coffee_env) is active in the terminal
  2. Press Ctrl+` to open the terminal in VS Code
  3. Run: python scripts/02_data_preprocessing.py
  4. Check the outputs printed and files saved
================================================================
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image, ImageDraw, ImageFilter
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib

warnings.filterwarnings("ignore")
plt.style.use("dark_background")

# ================================================================
# SECTION 1 — LOAD DATASET
# ================================================================
print("\n" + "="*55)
print("  SECTION 1 — LOADING DATASET")
print("="*55)

CSV_PATH = "data/sensor_readings/sensor_data.csv"

if not os.path.exists(CSV_PATH):
    print(f"\n⚠ sensor_data.csv not found at {CSV_PATH}")
    print("  Running generate_sample_data.py first...\n")

    # Auto-generate sample data if it doesn't exist yet
    np.random.seed(42)
    n = 400

    good = pd.DataFrame({
        "bean_id":  [f"bean_{i:04d}" for i in range(1, n+1)],
        "weight_g": np.random.normal(0.32, 0.03, n).clip(0.25, 0.42),
        "red":      np.random.normal(140, 15, n).clip(100, 180).astype(int),
        "green":    np.random.normal(95, 12, n).clip(65, 130).astype(int),
        "blue":     np.random.normal(60, 10, n).clip(35, 90).astype(int),
        "label":    "good"
    })

    n_each = n // 4
    black = pd.DataFrame({
        "bean_id":  [f"bean_{i:04d}" for i in range(n+1, n+n_each+1)],
        "weight_g": np.random.normal(0.30, 0.04, n_each),
        "red":      np.random.normal(40, 10, n_each).clip(15, 70).astype(int),
        "green":    np.random.normal(35, 8, n_each).clip(12, 60).astype(int),
        "blue":     np.random.normal(28, 7, n_each).clip(10, 50).astype(int),
        "label":    "bad"
    })
    immature = pd.DataFrame({
        "bean_id":  [f"bean_{i:04d}" for i in range(n+n_each+1, n+2*n_each+1)],
        "weight_g": np.random.normal(0.15, 0.04, n_each).clip(0.08, 0.22),
        "red":      np.random.normal(195, 15, n_each).clip(160, 230).astype(int),
        "green":    np.random.normal(200, 18, n_each).clip(165, 240).astype(int),
        "blue":     np.random.normal(170, 15, n_each).clip(140, 210).astype(int),
        "label":    "bad"
    })
    overripe = pd.DataFrame({
        "bean_id":  [f"bean_{i:04d}" for i in range(n+2*n_each+1, n+3*n_each+1)],
        "weight_g": np.random.normal(0.18, 0.03, n_each).clip(0.12, 0.24),
        "red":      np.random.normal(65, 12, n_each).clip(40, 95).astype(int),
        "green":    np.random.normal(50, 10, n_each).clip(28, 75).astype(int),
        "blue":     np.random.normal(38, 8, n_each).clip(20, 60).astype(int),
        "label":    "bad"
    })
    foreign = pd.DataFrame({
        "bean_id":  [f"bean_{i:04d}" for i in range(n+3*n_each+1, n+4*n_each+1)],
        "weight_g": np.random.uniform(0.6, 2.0, n_each),
        "red":      np.random.normal(100, 30, n_each).clip(30, 200).astype(int),
        "green":    np.random.normal(95, 28, n_each).clip(25, 190).astype(int),
        "blue":     np.random.normal(85, 25, n_each).clip(20, 180).astype(int),
        "label":    "bad"
    })

    df_gen = pd.concat([good, black, immature, overripe, foreign], ignore_index=True)
    df_gen = df_gen.sample(frac=1, random_state=42).reset_index(drop=True)
    df_gen["weight_g"] = df_gen["weight_g"].round(3)
    os.makedirs("data/sensor_readings", exist_ok=True)
    df_gen.to_csv(CSV_PATH, index=False)
    print(f"  ✓ Sample dataset created: {len(df_gen)} rows")

df = pd.read_csv(CSV_PATH)
print(f"\n  Dataset loaded: {df.shape[0]} rows × {df.shape[1]} columns")
print(f"  Columns : {list(df.columns)}")
print(f"  Labels  : {df['label'].value_counts().to_dict()}")
print(f"\n  First 5 rows:")
print(df.head().to_string(index=False))


# ================================================================
# SECTION 2 — EXPLORE & VISUALISE
# ================================================================
print("\n" + "="*55)
print("  SECTION 2 — EXPLORING & VISUALISING")
print("="*55)

print("\n  Basic statistics:")
print(df[["weight_g","red","green","blue"]].describe().round(2).to_string())

print(f"\n  Missing values: {df.isnull().sum().sum()} total")

# Chart 1 — Feature distributions by class
fig, axes = plt.subplots(2, 2, figsize=(14, 9))
fig.suptitle("Coffee Bean Sensor Data — Feature Distributions by Class",
             fontsize=15, fontweight="bold", color="white")

features = ["weight_g", "red", "green", "blue"]
colors   = {"good": "#00e676", "bad": "#ff5252"}

for ax, feat in zip(axes.flatten(), features):
    for label, grp in df.groupby("label"):
        ax.hist(grp[feat], bins=30, alpha=0.6, label=label, color=colors[label])
    ax.set_title(feat.upper(), color="white", fontweight="bold")
    ax.set_xlabel("Value"); ax.set_ylabel("Count")
    ax.legend()

plt.tight_layout()
os.makedirs("data", exist_ok=True)
plt.savefig("data/feature_distributions.png", dpi=150, bbox_inches="tight")
plt.show()
print("\n  ✓ Chart saved: data/feature_distributions.png")

# Chart 2 — Correlation heatmap
fig2, ax2 = plt.subplots(figsize=(7, 5))
sns.heatmap(df[["weight_g","red","green","blue"]].corr(),
            annot=True, fmt=".2f", cmap="RdYlGn", ax=ax2)
ax2.set_title("Feature Correlation Matrix", color="white", fontweight="bold")
plt.tight_layout()
plt.savefig("data/correlation_heatmap.png", dpi=150, bbox_inches="tight")
plt.show()
print("  ✓ Chart saved: data/correlation_heatmap.png")

# Chart 3 — Box plots
fig3, axes3 = plt.subplots(1, 4, figsize=(16, 5))
fig3.suptitle("Feature Box Plots by Class", fontsize=14, color="white")
for ax, feat in zip(axes3, features):
    data_good = df[df["label"] == "good"][feat]
    data_bad  = df[df["label"] == "bad"][feat]
    bp = ax.boxplot([data_bad, data_good], labels=["bad","good"],
                    patch_artist=True, notch=False)
    bp["boxes"][0].set_facecolor("#ff5252")
    bp["boxes"][1].set_facecolor("#00e676")
    ax.set_title(feat.upper(), color="white")
plt.tight_layout()
plt.savefig("data/boxplots.png", dpi=150, bbox_inches="tight")
plt.show()
print("  ✓ Chart saved: data/boxplots.png")


# ================================================================
# SECTION 3 — CLEAN & ENCODE
# ================================================================
print("\n" + "="*55)
print("  SECTION 3 — CLEANING & ENCODING LABELS")
print("="*55)

df_clean = df.drop(columns=["bean_id"]).copy()

before = len(df_clean)
df_clean = df_clean.drop_duplicates().dropna()
print(f"\n  Removed {before - len(df_clean)} duplicate/null rows")

# Remove outliers (1st–99th percentile)
numeric_cols = ["weight_g", "red", "green", "blue"]
Q1   = df_clean[numeric_cols].quantile(0.01)
Q3   = df_clean[numeric_cols].quantile(0.99)
mask = ((df_clean[numeric_cols] >= Q1) & (df_clean[numeric_cols] <= Q3)).all(axis=1)
df_clean = df_clean[mask]
print(f"  After outlier removal: {len(df_clean)} rows remaining")

# Encode labels: good=1, bad=0
df_clean["label"] = df_clean["label"].map({"good": 1, "bad": 0})
print(f"  Label encoding: good → 1, bad → 0")
print(f"  Final balance : {df_clean['label'].value_counts().to_dict()}")


# ================================================================
# SECTION 4 — NORMALISE FEATURES
# ================================================================
print("\n" + "="*55)
print("  SECTION 4 — NORMALISING FEATURES")
print("="*55)

X = df_clean[["weight_g", "red", "green", "blue"]].values
y = df_clean["label"].values

print(f"\n  Features shape : {X.shape}")
print(f"  Labels shape   : {y.shape}")
print(f"  Before scaling (sample): {X[0]}")

scaler  = StandardScaler()
X_scaled = scaler.fit_transform(X)
print(f"  After  scaling (sample): {X_scaled[0].round(4)}")

# Save scaler — Raspberry Pi needs this exact file at deployment
os.makedirs("models", exist_ok=True)
joblib.dump(scaler, "models/scaler.pkl")
print(f"\n  ✓ Scaler saved: models/scaler.pkl")


# ================================================================
# SECTION 5 — TRAIN / TEST SPLIT
# ================================================================
print("\n" + "="*55)
print("  SECTION 5 — TRAIN / TEST SPLIT (80/20)")
print("="*55)

X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y,
    test_size=0.2,
    random_state=42,
    stratify=y        # keeps 50/50 balance in both splits
)

print(f"\n  Training samples : {X_train.shape[0]}")
print(f"  Test samples     : {X_test.shape[0]}")
print(f"  Train balance    : good={sum(y_train==1)}, bad={sum(y_train==0)}")
print(f"  Test  balance    : good={sum(y_test==1)},  bad={sum(y_test==0)}")

# Save splits for Step 3
np.save("data/X_train.npy", X_train)
np.save("data/X_test.npy",  X_test)
np.save("data/y_train.npy", y_train)
np.save("data/y_test.npy",  y_test)
print(f"\n  ✓ Saved: data/X_train.npy  data/X_test.npy")
print(f"  ✓ Saved: data/y_train.npy  data/y_test.npy")


# ================================================================
# SECTION 6 — PREPARE IMAGE DATASET
# ================================================================
print("\n" + "="*55)
print("  SECTION 6 — PREPARING IMAGE DATASET")
print("="*55)

IMG_SIZE  = (224, 224)
N_EACH    = 100
GOOD_DIR  = "data/images/good"
BAD_DIR   = "data/images/bad"

def make_bean_image(label, index):
    """Generate a synthetic bean image for testing purposes."""
    img  = Image.new("RGB", IMG_SIZE, color=(30, 20, 10))
    draw = ImageDraw.Draw(img)
    cx, cy = 112, 112
    if label == "good":
        r = int(np.random.randint(110, 155))
        g = int(np.random.randint(70, 110))
        b = int(np.random.randint(40, 75))
        draw.ellipse([cx-55, cy-40, cx+55, cy+40], fill=(r, g, b))
        draw.line([cx, cy-35, cx, cy+35], fill=(r-30, g-20, b-15), width=2)
    else:
        d = index % 4
        if   d == 0: draw.ellipse([cx-55,cy-40,cx+55,cy+40], fill=(25,18,12))
        elif d == 1: draw.ellipse([cx-40,cy-30,cx+40,cy+30], fill=(210,205,175))
        elif d == 2:
            draw.ellipse([cx-50,cy-38,cx+50,cy+38], fill=(90,60,35))
            draw.line([cx-20,cy-30,cx+25,cy+30], fill=(20,10,5), width=3)
        else: draw.rectangle([cx-45,cy-35,cx+45,cy+35], fill=(130,125,120))
    return img.filter(ImageFilter.GaussianBlur(radius=1))

for label, folder in [("good", GOOD_DIR), ("bad", BAD_DIR)]:
    os.makedirs(folder, exist_ok=True)
    existing = len([f for f in os.listdir(folder) if f.endswith(".jpg")])
    if existing >= N_EACH:
        print(f"\n  {label}: {existing} images already exist — skipping")
        continue
    print(f"\n  Generating {N_EACH} {label} images...", end=" ")
    for i in range(N_EACH):
        make_bean_image(label, i).save(f"{folder}/bean_{i:04d}.jpg", quality=95)
    print(f"✓")

good_count = len([f for f in os.listdir(GOOD_DIR) if f.endswith(".jpg")])
bad_count  = len([f for f in os.listdir(BAD_DIR)  if f.endswith(".jpg")])
print(f"\n  Image counts — Good: {good_count} | Bad: {bad_count}")

# Verify images load correctly
print(f"\n  Verifying images load correctly...")
sample_img = Image.open(f"{GOOD_DIR}/bean_0000.jpg")
print(f"  Sample image size : {sample_img.size}")
print(f"  Sample image mode : {sample_img.mode}")
print(f"  ✓ Image pipeline verified")


# ================================================================
# SECTION 7 — FINAL SUMMARY
# ================================================================
print("\n" + "="*55)
print("  STEP 2 COMPLETE — PREPROCESSING SUMMARY")
print("="*55)
print(f"""
  SENSOR DATA:
    Training samples  : {X_train.shape[0]}
    Test samples      : {X_test.shape[0]}
    Features          : weight_g, red, green, blue
    Normalised        : Yes (StandardScaler)

  IMAGE DATA:
    Good images       : {good_count}
    Bad images        : {bad_count}
    Size              : 224 x 224 RGB

  FILES SAVED:
    models/scaler.pkl
    data/X_train.npy   data/X_test.npy
    data/y_train.npy   data/y_test.npy
    data/feature_distributions.png
    data/correlation_heatmap.png
    data/boxplots.png

  READY FOR:
    Step 3 — Decision Tree Model  (sensor data)
    Step 4 — CNN Image Model      (image data)
""")
print("="*55)