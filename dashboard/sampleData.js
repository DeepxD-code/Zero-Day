// PREVIEW DATA ONLY — DELETE ONCE REAL API IS WIRED UP BY TEAMMATE.
const sampleAlerts = [
  {
    "alert_id": "4fa85f64-5717-4562-b3fc-2c963f66afa1",
    "timestamp": "2026-07-05T14:22:04Z",
    "src_ip": "192.168.1.105",
    "dst_ip": "10.0.0.42",
    "anomaly_score": 0.924,
    "confidence": 0.98,
    "risk_score": 88,
    "attack_type_guess": "Mimicry Attack",
    "mitre_technique": "T1059.001",
    "explanation": [
      "Unusual DNS request rate: Source exhibited a 400% increase in sub-domain querying over the last 300 seconds, bypassing standard ratelimiting patterns.",
      "First-seen destination ASN: The destination IP maps to an ASN (AS13335) never before communicated with by this source within the last 90 days."
    ],
    "model_source": "gnn_temporal",
    "is_adversarial_test": true
  },
  {
    "alert_id": "4fa85f64-5717-4562-b3fc-2c963f66afa2",
    "timestamp": "2026-07-05T14:21:58Z",
    "src_ip": "172.16.254.1",
    "dst_ip": "10.0.0.88",
    "anomaly_score": 0.640,
    "confidence": 0.85,
    "risk_score": 45,
    "attack_type_guess": "SQL Injection",
    "mitre_technique": "T1190",
    "explanation": [
      "Request payloads drift heavily from typical syntax distribution, featuring high frequencies of control character anomalies."
    ],
    "model_source": "drift_monitor",
    "is_adversarial_test": false
  },
  {
    "alert_id": "4fa85f64-5717-4562-b3fc-2c963f66afa3",
    "timestamp": "2026-07-05T14:21:42Z",
    "src_ip": "203.0.113.44",
    "dst_ip": "10.12.0.5",
    "anomaly_score": 0.810,
    "confidence": 0.90,
    "risk_score": 72,
    "attack_type_guess": "Data Exfiltration",
    "mitre_technique": "T1048",
    "explanation": [
      "High volume TCP data transfer to external public IP detected over unusual ports."
    ],
    "model_source": "gnn_temporal",
    "is_adversarial_test": false
  },
  {
    "alert_id": "4fa85f64-5717-4562-b3fc-2c963f66afa4",
    "timestamp": "2026-07-05T14:20:15Z",
    "src_ip": "192.168.1.112",
    "dst_ip": "192.168.1.1",
    "anomaly_score": 0.312,
    "confidence": 0.95,
    "risk_score": 12,
    "attack_type_guess": "Port Scan",
    "mitre_technique": "T1046",
    "explanation": [
      "Multiple sequential connection requests to closed ports within a brief time window."
    ],
    "model_source": "drift_monitor",
    "is_adversarial_test": false
  },
  {
    "alert_id": "4fa85f64-5717-4562-b3fc-2c963f66afa5",
    "timestamp": "2026-07-05T14:19:00Z",
    "src_ip": "10.0.0.15",
    "dst_ip": "10.0.0.4",
    "anomaly_score": 0.942,
    "confidence": 0.99,
    "risk_score": 94,
    "attack_type_guess": "Mimicry Attack",
    "mitre_technique": "T1059.001",
    "explanation": [
      "Evasion patterns matching known model vulnerabilities detected."
    ],
    "model_source": "gnn_temporal",
    "is_adversarial_test": true
  }
];
