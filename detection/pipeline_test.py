import torch
import torch.nn as nn
import pandas as pd 
import numpy as np
from sklearn.preprocessing import MinMaxScaler

import sys
csv_path =sys.argv[1] if len(sys.argv) > 1 else "D:\Test OD\Zero-Day\training_data\dataset_10k_normal.csv"

print(f"loading Saharsh  dataset from {csv_path}")
df=pd.read_csv(csv_path)
df.columns=df.columns.str.strip()

df=df.drop(columns=['Label', 'Flow ID', 'Source IP' ,'Destination IP' , 'Timestamp' ], errors='ignore')
df=df.replace([float('inf'), float('-inf')], float('nan'))
df=df.dropna(axis=1)

print(f"Loaded {len(df)} Flows,{df.shape[1]} Features")

#-- Checking if features number matches expectations--#

if df.shape[1] != 76:
    print(f"Warning: Expected 76 features, but got {df.shape[1]} features. Please check the dataset.")
    print ("Saharsh dataset Pass your dataset through CICFlowMeter to get 76 features. The dataset you provided has different number of features.")
else:
    print("Dataset has 76 features, proceeding with normalization and scoring.")

#-- Normalizing the dataset --#
scaler = MinMaxScaler()
data=scaler.fit_transform(df)
X=torch.tensor(data, dtype=torch.float32)

#-- Loading my Trained Autoencoder --#

class Autoencoder(nn.Module):
    def __init__(self, input_dim=76):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 8)
        )
        self.decoder = nn.Sequential(
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, input_dim),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))

    def anomaly_score(self, x):
        with torch.no_grad():
            recon = self.forward(x)
            return torch.mean((recon - x) ** 2, dim=1)


model=Autoencoder(input_dim=df.shape[1])
model.load_state_dict(torch.load("detection/autoencoder_v1.pt", map_location="cpu"))
model.eval()

#-- Score all flows --#

scores=model.anomaly_score(X).numpy()
threshold=0.5

flagged =(scores>threshold).sum()
print(f"\n Results on Saharsh dataset:")
print(f"\n Total Flows: {len(scores)}")
print(f"\n Mean scores: {scores.mean():.6f}")
print(f"\n Max scores: {scores.max():.6f}")
print(f"\n Min scores: {scores.min():.6f}")
print(f"\n Flagged Anomalies: {flagged} (100*{flagged/len(scores):.1f}%)")
print("\n  Pipeline test complete — A's data flows into model correctly.")
