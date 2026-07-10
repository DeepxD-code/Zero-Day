# stub_detector.py
# Week 2 — now uses real autoencoder model

import torch
import torch.nn as nn
import uuid
from datetime import datetime


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


def score_flow(feature_vector: list) -> dict:
    """
    Takes a 76-feature normalized vector.
    Returns full scored alert matching scored_alert.json schema.
    """
    model = Autoencoder(input_dim=76)
    model.load_state_dict(torch.load(
        "detection/autoencoder_v1.pt",
        map_location="cpu",
        weights_only=True
    ))
    model.eval()

    x = torch.tensor([feature_vector], dtype=torch.float32)
    score = model.anomaly_score(x).item()
    threshold = 0.5

    return {
        "alert_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "src_ip": "0.0.0.0",
        "dst_ip": "0.0.0.0",
        "anomaly_score": round(score, 6),
        "confidence": round(1 - score, 6),
        "risk_score": int(score * 100),
        "attack_type_guess": "unknown",
        "mitre_technique": "unknown",
        "explanation": [],
        "model_source": "autoencoder-v1",
        "is_adversarial_test": False,
        "feature_vector": feature_vector,
        "top_features": []
    }


if __name__ == "__main__":
    fake_vector = [0.4] * 76
    result = score_flow(fake_vector)
    print("Alert output:")
    for key, value in result.items():
        if key == "feature_vector":
            print(f"  feature_vector: [76 values, first 3: {value[:3]}]")
        else:
            print(f"  {key}: {value}")