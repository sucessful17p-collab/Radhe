"""Synthetic trajectory model with a separate sensor-evidence confidence gate.

This model is a systems demo, not a clinical model or a patient forecast.
"""
import math
import random

FEATURES = ["pulse_delta", "spo2_drop", "resp_delta", "temp_delta", "bp_delta", "note_concern", "trend"]
TEACHER = [-2.25, 1.05, 1.9, 0.75, 0.58, 0.72, 1.25, 0.72]


def sigmoid(x):
    x = max(-30.0, min(30.0, x))
    return 1.0 / (1.0 + math.exp(-x))


def train_synthetic_model(seed=41, rows=2400, epochs=90):
    rng = random.Random(seed)
    data = []
    for _ in range(rows):
        x = [rng.random() * 1.35 for _ in range(5)]
        x += [rng.choice([0.0, 1.0]), rng.random()]
        target_logit = TEACHER[0] + sum(w * v for w, v in zip(TEACHER[1:], x))
        data.append((x, 1.0 if target_logit >= 0 else 0.0))
    weights = [0.0] * (len(FEATURES) + 1)
    learning_rate = 0.34
    for _ in range(epochs):
        grad = [0.0] * len(weights)
        for x, y in data:
            pred = sigmoid(weights[0] + sum(w * v for w, v in zip(weights[1:], x)))
            error = pred - y
            grad[0] += error
            for j, value in enumerate(x, start=1):
                grad[j] += error * value
        for j in range(len(weights)):
            weights[j] -= learning_rate * grad[j] / rows
    return {"intercept": weights[0], "weights": dict(zip(FEATURES, weights[1:])), "training_rows": rows, "seed": seed, "label": "synthetic_escalation_pattern_24_48h"}


def make_features(vitals, baseline, previous, english_note=""):
    clamp = lambda value: max(0.0, min(1.8, float(value)))
    pulse_delta = clamp(abs(vitals["pulse"] - baseline["pulse"]) / 35.0)
    spo2_drop = clamp(max(0.0, baseline["spo2"] - vitals["spo2"]) / 8.0)
    resp_delta = clamp(max(0.0, vitals["respiratory_rate"] - baseline["respiratory_rate"]) / 12.0)
    temp_delta = clamp(max(0.0, vitals["temperature_c"] - baseline["temperature_c"]) / 2.0)
    bp_delta = clamp(abs(vitals["systolic"] - baseline["systolic"]) / 30.0)
    note_words = ("more tired", "breathless", "breathing harder", "new concern", "less responsive", "worse than", "unusually weak")
    note_concern = 1.0 if any(term in (english_note or "").lower() for term in note_words) else 0.0
    trend = 0.0
    if previous:
        old = previous["vitals"]
        drift = max(0, vitals["pulse"] - old["pulse"]) / 25 + max(0, old["spo2"] - vitals["spo2"]) / 8 + max(0, vitals["respiratory_rate"] - old["respiratory_rate"]) / 10
        trend = clamp(drift / 2.0)
    return dict(zip(FEATURES, [pulse_delta, spo2_drop, resp_delta, temp_delta, bp_delta, note_concern, trend]))


def assess_evidence(telemetry):
    quality = max(0.0, min(100.0, float(telemetry.get("signal_quality_pct", 0))))
    age = max(0.0, float(telemetry.get("age_seconds", 9999)))
    freshness = max(0.0, min(1.0, 1.0 - age / 300.0))
    confidence = round(quality * freshness)
    if confidence < 55:
        label = "low"
    elif confidence < 80:
        label = "moderate"
    else:
        label = "high"
    return {"confidence_pct": confidence, "label": label, "signal_quality_pct": round(quality), "age_seconds": round(age), "reliable_for_demo_score": confidence >= 55}


def predict(model, features, telemetry, equipment):
    weights = model["weights"]
    logit = model["intercept"] + sum(weights[k] * features[k] for k in FEATURES)
    probability = sigmoid(logit)
    patient_level = "high" if probability >= 0.72 else "medium" if probability >= 0.40 else "low"
    evidence = assess_evidence(telemetry)
    equipment_flags = []
    if equipment.get("connection") != "Connected":
        equipment_flags.append("mock equipment connection is interrupted")
    if equipment.get("battery_pct", 100) < 25:
        equipment_flags.append("simulated backup battery is low")

    labels = {
        "pulse_delta": "pulse differs from the configured demo baseline",
        "spo2_drop": "oxygen reading differs from the configured demo baseline",
        "resp_delta": "breathing-rate reading differs from the configured demo baseline",
        "temp_delta": "temperature reading differs from the configured demo baseline",
        "bp_delta": "blood-pressure reading differs from the configured demo baseline",
        "note_concern": "caregiver note includes a demo concern phrase",
        "trend": "recent readings show a changing pattern",
    }
    contributions = sorted(((weights[k] * features[k], labels[k]) for k in FEATURES if features[k] > 0), reverse=True)
    patient_reasons = [label for value, label in contributions if value > 0.12][:3]
    if not patient_reasons:
        patient_reasons = ["synthetic readings are close to the configured demo baseline"]

    if not evidence["reliable_for_demo_score"]:
        classification = "evidence_check"
        level = "uncertain"
        reasons = ["sensor signal quality or freshness is too low to show a patient-state score"]
    elif patient_level in ("medium", "high"):
        classification = "patient_trend"
        level = patient_level
        reasons = patient_reasons
    elif equipment_flags:
        classification = "equipment"
        level = "device"
        reasons = equipment_flags[:]
    else:
        classification = "patient_trend"
        level = "low"
        reasons = patient_reasons

    if evidence["reliable_for_demo_score"] and patient_level in ("medium", "high") and equipment_flags:
        reasons = patient_reasons + equipment_flags
        classification = "combined_review"

    return {
        "probability": round(probability, 3) if evidence["reliable_for_demo_score"] else None,
        "level": level,
        "classification": classification,
        "evidence": evidence,
        "equipment_flags": equipment_flags,
        "reasons": reasons,
        "patient_factors": patient_reasons,
        "window": "Synthetic 24–48 hour escalation pattern" if level in ("medium", "high") else "No elevated synthetic pattern shown",
        "model_label": model["label"],
        "model_note": "Toy logistic regression trained only on generated patterns; not clinically validated.",
    }
