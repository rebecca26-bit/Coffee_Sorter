import pandas as pd
import numpy as np

# ── Load real data ────────────────────────────────────────────
real = pd.read_csv('data/sensor_readings/sensor_data.csv')
print(f"Real data: {len(real)} rows")
print(real['label'].value_counts())

# ── Generate synthetic data ───────────────────────────────────
np.random.seed(42)
n = 400

good = pd.DataFrame({
    'weight_g': np.random.normal(0.32, 0.03, n).clip(0.25, 0.42),
    'red'     : np.random.normal(140, 15, n).clip(100, 180).astype(int),
    'green'   : np.random.normal(95, 12, n).clip(65, 130).astype(int),
    'blue'    : np.random.normal(60, 10, n).clip(35, 90).astype(int),
    'label'   : 'good'
})

bad = pd.DataFrame({
    'weight_g': np.random.normal(0.18, 0.05, n).clip(0.08, 0.35),
    'red'     : np.random.normal(80, 30, n).clip(20, 200).astype(int),
    'green'   : np.random.normal(90, 35, n).clip(20, 210).astype(int),
    'blue'    : np.random.normal(75, 28, n).clip(15, 190).astype(int),
    'label'   : 'bad'
})

synthetic = pd.concat([good, bad], ignore_index=True)
synthetic['weight_g'] = synthetic['weight_g'].round(3)
print(f"\nSynthetic data: {len(synthetic)} rows")

# ── Combine real + synthetic ──────────────────────────────────
# Drop weight from real data since it's all 0.0
real_no_weight = real[['red', 'green', 'blue', 'label']].copy()
real_no_weight['weight_g'] = np.nan

# Use real colour values but synthetic weight for real rows
# (weight will be filled with synthetic averages per class)
good_avg_weight = synthetic[synthetic['label']=='good']['weight_g'].mean()
bad_avg_weight  = synthetic[synthetic['label']=='bad']['weight_g'].mean()

real_no_weight.loc[real_no_weight['label']=='good', 'weight_g'] = good_avg_weight
real_no_weight.loc[real_no_weight['label']=='bad',  'weight_g'] = bad_avg_weight

# Combine
combined = pd.concat([synthetic, real_no_weight], ignore_index=True)
combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)
combined.insert(0, 'bean_id', ['bean_{:04d}'.format(i+1) for i in range(len(combined))])

print(f"\nCombined data: {len(combined)} rows")
print(combined['label'].value_counts())

# Save
combined.to_csv('data/sensor_readings/sensor_data.csv', index=False)
print('\n✓ Saved to data/sensor_readings/sensor_data.csv')
print(f"  Good: {sum(combined['label']=='good')}")
print(f"  Bad : {sum(combined['label']=='bad')}")
