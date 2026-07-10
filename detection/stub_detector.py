import torch
import torch.nn as nn
import uuid
from datetime import datetime


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


def score_flow(feature_vector: list) -> dict:
    """
    Takes a 76-feature normalized vector
    Returns full scored alert JSON for Person C
    """
    model = Autoencoder(input_dim=76)
    model.load_state_dict(torch.load(
        "detection/autoencoder_v1.pt",
        map_location="cpu"
    ))
    model.eval()

    x = torch.tensor([feature_vector], dtype=torch.float32)
    score = model.anomaly_score(x).item()
    threshold = 0.5

    return {
        "flow_id": str(uuid.uuid4()),
        "timestamp": datetime.now(datetime.UTC).isoformat(),
        "anomaly_score": round(score, 6),
        "threshold": threshold,
        "is_anomaly": score > threshold,
        "model_version": "autoencoder-v1",
        "feature_vector": feature_vector,
        "top_features": []
    }


if __name__ == "__main__":
    fake_vector = [0.4] * 76
    result = score_flow(fake_vector)
    print("Alert output:", result)
