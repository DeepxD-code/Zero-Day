import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

# ── Load A's CSV ──
import sys
csv_path = sys.argv[1] if len(sys.argv) > 1 else "D:\Test OD\Zero-Day\training_data\dataset_10k_normal.csv"

print(f"Loading A's data from: {csv_path}")
df = pd.read_csv(csv_path)
df.columns = df.columns.str.strip()

# Drop non-numeric columns same as training
df = df.drop(columns=['Label', 'Flow ID', 'Source IP', 'Destination IP',
                       'Timestamp'], errors='ignore')
df = df.replace([float('inf'), float('-inf')], float('nan'))
df = df.dropna(axis=1)

print(f"  Loaded {len(df)} flows, {df.shape[1]} features")

# ── Check feature count matches ──
if df.shape[1] != 76:
    print(f"  WARNING: Expected 76 features, got {df.shape[1]}")
    print("  Tell A to regenerate with CICFlowMeter on CICIDS2017 settings")
else:
    print("  Feature count matches. Good.")

# ── Normalize ──
scaler = MinMaxScaler()
data = scaler.fit_transform(df)
X = torch.tensor(data, dtype=torch.float32)

# ── Load your trained model ──
class Autoencoder(nn.Module):
    def __init__(self, input_dim=76):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 8)
        )
        self.decoder = nn.Sequential(
            nn.Linear(8, 32),
            nn.ReLU(),
            nn.Linear(32, input_dim),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))

    def anomaly_score(self, x):
        with torch.no_grad():
            recon = self.forward(x)
            return torch.mean((recon - x) ** 2, dim=1)

model = Autoencoder(input_dim=df.shape[1])
model.load_state_dict(torch.load("detection/autoencoder_v1.pt", map_location="cpu"))
model.eval()

# ── Score all flows ──
scores = model.anomaly_score(X).numpy()
threshold = 0.5

flagged = (scores > threshold).sum()
print(f"\n  Results on A's data:")
print(f"  Total flows    : {len(scores)}")
print(f"  Mean score     : {scores.mean():.6f}")
print(f"  Max score      : {scores.max():.6f}")
print(f"  Min score      : {scores.min():.6f}")
print(f"  Flagged        : {flagged} ({100*flagged/len(scores):.1f}%)")
print("\n  Pipeline test complete — A's data flows into model correctly.")