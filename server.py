"""SignalWard local full-stack demo. Python 3 standard library only; all records are synthetic."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json, os, sqlite3, random, time
from urllib.parse import urlparse
from risk_model import train_synthetic_model, make_features, predict

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "signalward.sqlite3"
DB.parent.mkdir(exist_ok=True)
MODEL = train_synthetic_model()
BASELINE = {"pulse": 72, "spo2": 97, "respiratory_rate": 17, "temperature_c": 36.7, "systolic": 120, "diastolic": 78}
SCENARIOS = {
    "stable": ({"pulse": 73, "spo2": 97, "respiratory_rate": 17, "temperature_c": 36.8, "systolic": 121, "diastolic": 79}, {"name": "Mock oxygen concentrator", "connection": "Connected", "power": "Main", "battery_pct": 100}, {"signal_quality_pct": 98, "age_seconds": 4, "sensor": "Demo pulse/SpO₂"}),
    "watch": ({"pulse": 91, "spo2": 94, "respiratory_rate": 22, "temperature_c": 37.3, "systolic": 130, "diastolic": 84}, {"name": "Mock oxygen concentrator", "connection": "Connected", "power": "Main", "battery_pct": 96}, {"signal_quality_pct": 96, "age_seconds": 5, "sensor": "Demo pulse/SpO₂"}),
    "artifact": ({"pulse": 111, "spo2": 87, "respiratory_rate": 24, "temperature_c": 37.1, "systolic": 128, "diastolic": 82}, {"name": "Mock oxygen concentrator", "connection": "Connected", "power": "Main", "battery_pct": 92}, {"signal_quality_pct": 24, "age_seconds": 8, "sensor": "Demo pulse/SpO₂ · noisy contact"}),
    "escalation": ({"pulse": 118, "spo2": 89, "respiratory_rate": 30, "temperature_c": 38.2, "systolic": 150, "diastolic": 92}, {"name": "Mock oxygen concentrator", "connection": "Disconnected", "power": "Backup", "battery_pct": 38}, {"signal_quality_pct": 97, "age_seconds": 4, "sensor": "Demo pulse/SpO₂"}),
    "backup": ({"pulse": 76, "spo2": 96, "respiratory_rate": 18, "temperature_c": 36.9, "systolic": 122, "diastolic": 80}, {"name": "Mock oxygen concentrator", "connection": "Connected", "power": "Backup", "battery_pct": 82}, {"signal_quality_pct": 94, "age_seconds": 11, "sensor": "Demo pulse/SpO₂"}),
}
DEVICE_CATALOG = {
    "pulse_oximeter": {"name": "Pulse oximeter", "metrics": [("oxygen_saturation", "%", 97, 91), ("pulse", "bpm", 72, 103)]},
    "blood_pressure_cuff": {"name": "Blood-pressure cuff", "metrics": [("systolic_pressure", "mmHg", 120, 148), ("diastolic_pressure", "mmHg", 78, 92), ("pulse", "bpm", 72, 96)]},
    "thermometer": {"name": "Digital thermometer", "metrics": [("body_temperature", "°C", 36.7, 38.1)]},
    "smart_scale": {"name": "Connected scale", "metrics": [("body_weight", "kg", 68.4, 70.2)]},
    "glucose_meter": {"name": "Glucose meter", "metrics": [("blood_glucose", "mg/dL", 98, 164)]},
}
LAST_VISION_EVENT_AT = 0.0
NOTES = {
    "en": {"tired": ("Seems more tired than usual", "Seems more tired than usual"), "comfortable": ("Rested and comfortable", "Rested and comfortable"), "breathing": ("Breathing seems harder than usual", "Breathing seems harder than usual")},
    "hi": {"tired": ("आज सामान्य से अधिक थकान लग रही है", "Seems more tired than usual"), "comfortable": ("आराम में और सहज लग रहे हैं", "Rested and comfortable"), "breathing": ("साँस लेने में सामान्य से अधिक कठिनाई लग रही है", "Breathing seems harder than usual")},
    "es": {"tired": ("Parece más cansado de lo habitual", "Seems more tired than usual"), "comfortable": ("Descansado y cómodo", "Rested and comfortable"), "breathing": ("Parece respirar con más dificultad", "Breathing seems harder than usual")},
    "ta": {"tired": ("வழக்கத்தை விட அதிக சோர்வாகத் தெரிகிறார்", "Seems more tired than usual"), "comfortable": ("ஓய்வாகவும் வசதியாகவும் உள்ளார்", "Rested and comfortable"), "breathing": ("வழக்கத்தை விட சுவாசம் கடினமாகத் தெரிகிறது", "Breathing seems harder than usual")},
}


def simulate_device_packet(body):
    device_type = str(body.get("device_type", ""))
    mode = str(body.get("mode", "baseline"))
    spec = DEVICE_CATALOG.get(device_type)
    if not spec: raise ValueError("Choose a supported simulated device from the catalog.")
    if mode not in ("baseline", "variation"): raise ValueError("Mode must be baseline or variation.")
    variation = mode == "variation"
    measurements = [{"code": code, "value": varied if variation else base, "unit": unit}
                    for code, unit, base, varied in spec["metrics"]]
    now = time.time()
    return {"api_version": "signalward-device-demo-v1", "device": {"type": device_type, "display_name": spec["name"], "device_id": f"SIM-{device_type.upper()}-001", "connection": "simulated"},
            "observed_at": now, "measurements": measurements,
            "quality": {"status": "synthetic", "mode": mode}, "simulation_only": True,
            "clinical_interpretation": None, "note": "No real device is connected; sample values are fictional."}


def accept_vision_event(body):
    """Store an alert from local pose analysis. Accept event metadata only, never images or landmarks."""
    global LAST_VISION_EVENT_AT
    if any(key in body for key in ("image", "frame", "video", "landmarks", "image_data", "jpeg", "base64")):
        raise ValueError("This endpoint accepts event metadata only; image/video data is not accepted.")
    if body.get("event_type") != "possible_floor_level_transition":
        raise ValueError("Unsupported event type.")
    try:
        confidence = float(body.get("pose_visibility"))
        duration = float(body.get("duration_seconds"))
    except (TypeError, ValueError):
        raise ValueError("Provide numeric pose_visibility and duration_seconds.")
    if not 0.75 <= confidence <= 1 or not 1.5 <= duration <= 30:
        raise ValueError("Event does not meet the demo confidence/duration gate.")
    zone = str(body.get("zone", "camera-zone-1"))
    if not 1 <= len(zone) <= 40 or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in zone):
        raise ValueError("Zone must be a short generic label using letters, numbers, hyphens, or underscores.")
    reasons = ["Possible floor-level posture transition from on-device pose landmarks", f"Local demo confidence {round(confidence * 100)}% · sustained {round(duration, 1)} seconds", f"Zone: {zone}", "Caregiver confirmation required; this is not a fall diagnosis"]
    now = time.time()
    if now - LAST_VISION_EVENT_AT < 15:
        raise ValueError("A recent possible-event alert was just sent; wait briefly before another demo alert.")
    with connect() as db:
        cur = db.execute("INSERT INTO alerts(at,level,score,reasons,state,kind) VALUES(?,?,?,?, 'Open', ?)",
                         (now, "medium", confidence, json.dumps(reasons), "vision_possible_event"))
        alert_id = cur.lastrowid
    LAST_VISION_EVENT_AT = now
    return {"ok": True, "alert_id": alert_id, "event_type": "possible_floor_level_transition",
            "pose_visibility": confidence, "message": "Possible-event alert added for caregiver review.",
            "image_received": False, "state": state()}


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def initialize():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS readings(id INTEGER PRIMARY KEY, at REAL NOT NULL, scenario TEXT NOT NULL, vitals TEXT NOT NULL, equipment TEXT NOT NULL, telemetry TEXT NOT NULL DEFAULT '{}', risk TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'simulator');
        CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY, at REAL NOT NULL, caregiver TEXT NOT NULL, language TEXT NOT NULL, original TEXT NOT NULL, english TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY, at REAL NOT NULL, level TEXT NOT NULL, score REAL NOT NULL, reasons TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'Open', acknowledged_by TEXT, kind TEXT NOT NULL DEFAULT 'patient_trend');
        CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY, at REAL NOT NULL, caregiver TEXT NOT NULL, action TEXT NOT NULL, activity TEXT NOT NULL);
        """)
        count = db.execute("SELECT count(*) FROM readings").fetchone()[0]
        reading_columns = {row[1] for row in db.execute("PRAGMA table_info(readings)")}
        if "telemetry" not in reading_columns:
            db.execute("ALTER TABLE readings ADD COLUMN telemetry TEXT NOT NULL DEFAULT '{}' ")
        alert_columns = {row[1] for row in db.execute("PRAGMA table_info(alerts)")}
        if "kind" not in alert_columns:
            db.execute("ALTER TABLE alerts ADD COLUMN kind TEXT NOT NULL DEFAULT 'patient_trend'")
        count = db.execute("SELECT count(*) FROM readings").fetchone()[0]
        if not count:
            vitals, equipment, telemetry = SCENARIOS["stable"]
            risk = make_risk(vitals, equipment, telemetry, None, "")
            store_reading(db, "stable", vitals, equipment, telemetry, risk, "initial synthetic seed")


def make_risk(vitals, equipment, telemetry, previous, note):
    features = make_features(vitals, BASELINE, previous, note)
    return predict(MODEL, features, telemetry, equipment)


def scenario_evaluation(body):
    """Score user-entered synthetic values; do not persist them."""
    fields = {"pulse": (35, 220), "spo2": (50, 100), "respiratory_rate": (5, 70),
              "temperature_c": (30, 43), "systolic": (50, 260), "diastolic": (25, 160)}
    vitals = {}
    for key, (low, high) in fields.items():
        try: value = float(body.get(key))
        except (TypeError, ValueError): raise ValueError(f"Enter a number for {key}.")
        if not low <= value <= high: raise ValueError(f"{key} must be between {low} and {high} for this demo.")
        vitals[key] = value
    telemetry = {"signal_quality_pct": max(0, min(100, float(body.get("signal_quality_pct", 95)))),
                 "age_seconds": max(0, min(3600, float(body.get("age_seconds", 5)))), "sensor": "Scenario Lab synthetic input"}
    equipment = {"connection": "Connected", "battery_pct": 100}
    note = str(body.get("note", ""))[:500]
    risk = make_risk(vitals, equipment, telemetry, None, note)
    if risk["classification"] == "evidence_check":
        next_move = "Evidence check: verify the simulated reading and source quality before interpreting it."
    elif risk["level"] == "high":
        next_move = "Human review prompt: route to the designated caregiver and follow the documented demo care plan."
    elif risk["level"] == "medium":
        next_move = "Context review: check the simulated note and trend, then follow the documented demo care plan."
    else:
        next_move = "Continue routine demo observation; no care decision is implied."
    return {"risk": risk, "next_move": next_move, "simulation_only": True, "persisted": False}


def vision_prediction(body):
    """Classify geometric features from generated canvas frames; never accept image bytes."""
    try:
        aspect = float(body.get("aspect", 0.5))
        floor = float(body.get("floor_proximity", 0.0))
        motion = float(body.get("motion", 0.0))
        quality = float(body.get("frame_quality", 1.0))
    except (TypeError, ValueError): raise ValueError("Vision features must be numeric.")
    if not (0.1 <= aspect <= 3 and 0 <= floor <= 1 and 0 <= motion <= 1 and 0 <= quality <= 1):
        raise ValueError("Vision features are outside the supported demo range.")
    # Transparent, hand-weighted classifier over synthetic geometric features; not a clinical model.
    score = min(0.99, max(0.01, 0.08 + 0.48 * floor + 0.38 * motion + 0.14 * max(0, aspect - 1.0)))
    confidence = round((0.5 + abs(score - 0.5)) * quality, 2)
    if quality < 0.35 or confidence < 0.58:
        label, next_move = "withheld_low_quality", "Visual check: generated frame quality is too low to label this pattern."
    elif score >= 0.65:
        label, next_move = "floor_level_transition_pattern", "Human review prompt: check the generated scene and follow the documented demo workflow."
    else:
        label, next_move = "upright_or_seated_pattern", "Continue demo observation; no event is inferred."
    return {"label": label, "confidence": confidence, "pattern_score": round(score, 2),
            "reason": f"Generated geometry: floor proximity {floor:.2f}, motion {motion:.2f}, frame quality {quality:.2f}.",
            "next_move": next_move, "simulation_only": True, "image_received": False}


def agent_review(body):
    """Independent deterministic reviewer for simulator output; no external AI service or storage."""
    reviewed = scenario_evaluation(body)
    risk = reviewed["risk"]
    checks = ["Input values passed simulator bounds validation", "Risk tier recomputed server-side from synthetic inputs"]
    claimed = str(body.get("claimed_level", "")).lower()
    consistent = not claimed or claimed == risk["level"]
    if not consistent:
        checks.append(f"Submitted tier ({claimed}) differs from recomputed tier ({risk['level']})")
    if risk["classification"] == "evidence_check":
        checks.append("Evidence gate is active; patient-pattern score should remain withheld")
    else:
        checks.append("Evidence gate passed for demo scoring only; confidence is not clinical reliability")
    return {"agent": "SignalWard Review Agent", "review_mode": "deterministic policy cross-check",
            "status": "CHECK" if not consistent or risk["classification"] == "evidence_check" else "REVIEWED",
            "consistent": consistent, "checks": checks,
            "summary": "The agent recomputed this fictional scenario and checked evidence-gate handling.",
            "risk_level": risk["level"], "classification": risk["classification"],
            "evidence_confidence_pct": risk["evidence"]["confidence_pct"],
            "workflow_prompt": reviewed["next_move"], "simulation_only": True, "persisted": False}


def store_reading(db, scenario, vitals, equipment, telemetry, risk, source="simulator"):
    now = time.time()
    cur = db.execute("INSERT INTO readings(at,scenario,vitals,equipment,telemetry,risk,source) VALUES(?,?,?,?,?,?,?)", (now, scenario, json.dumps(vitals), json.dumps(equipment), json.dumps(telemetry), json.dumps(risk), source))
    should_alert = risk["level"] in ("medium", "high", "uncertain", "device")
    if should_alert:
        score = float(risk.get("probability") or 0.0)
        alert_reasons = list(dict.fromkeys(risk["reasons"] + risk.get("equipment_flags", [])))
        db.execute("INSERT INTO alerts(at,level,score,reasons,state,kind) VALUES(?,?,?,?, 'Open', ?)", (now, risk["level"], score, json.dumps(alert_reasons), risk["classification"]))
    return cur.lastrowid


def as_reading(row):
    vitals = json.loads(row["vitals"])
    equipment = json.loads(row["equipment"])
    telemetry = json.loads(row["telemetry"] or "{}")
    if not telemetry:
        telemetry = {"signal_quality_pct": 95, "age_seconds": 4, "sensor": "Migrated synthetic fixture"}
    risk = json.loads(row["risk"])
    if "classification" not in risk:
        risk = make_risk(vitals, equipment, telemetry, None, "")
    return {"id": row["id"], "at": row["at"], "scenario": row["scenario"], "vitals": vitals, "equipment": equipment, "telemetry": telemetry, "risk": risk, "source": row["source"]}


def state():
    with connect() as db:
        readings = [as_reading(r) for r in db.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 24")]
        notes = [dict(r) for r in db.execute("SELECT id,at,caregiver,language,original,english FROM notes ORDER BY id DESC LIMIT 8")]
        alerts = [dict(r) for r in db.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 12")]
        for a in alerts: a["reasons"] = json.loads(a["reasons"])
        attendance = [dict(r) for r in db.execute("SELECT * FROM attendance ORDER BY id DESC LIMIT 8")]
        active = db.execute("SELECT count(*) FROM alerts WHERE state='Open'").fetchone()[0]
    return {"patient": {"alias": "Patient A", "type": "Synthetic demo profile", "baseline": BASELINE}, "readings": readings, "latest": readings[0], "notes": notes, "alerts": alerts, "open_alert_count": active, "attendance": attendance, "model": {"kind": "Synthetic-data logistic regression", "training_rows": MODEL["training_rows"], "label": MODEL["label"], "warning": "Illustrative only; not clinically validated or for care decisions."}, "server_time": time.time()}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(ROOT), **kwargs)
    def log_message(self, fmt, *args): pass
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)
    def read_json(self):
        size = min(int(self.headers.get("Content-Length", "0")), 100000)
        return json.loads(self.rfile.read(size) or b"{}")
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/devices/catalog":
            return self.send_json({"api_version": "signalward-device-demo-v1", "simulation_only": True,
                                   "devices": [{"type": key, "display_name": value["name"], "measurements": [code for code, _, _, _ in value["metrics"]]} for key, value in DEVICE_CATALOG.items()]})
        if path == "/api/state": return self.send_json(state())
        if path == "/api/health": return self.send_json({"ok": True, "mode": "synthetic-demo", "persistence": "sqlite"})
        return super().do_GET()
    def do_POST(self):
        path = urlparse(self.path).path
        try: body = self.read_json()
        except Exception: return self.send_json({"error": "Invalid JSON"}, 400)
        if path == "/api/devices/simulate":
            try: return self.send_json(simulate_device_packet(body))
            except (ValueError, TypeError) as exc: return self.send_json({"error": str(exc)}, 400)
        if path == "/api/vision/events":
            try: return self.send_json(accept_vision_event(body), 201)
            except (ValueError, TypeError) as exc: return self.send_json({"error": str(exc)}, 400)
        if path == "/api/simulator/evaluate":
            try: return self.send_json(scenario_evaluation(body))
            except (ValueError, TypeError) as exc: return self.send_json({"error": str(exc)}, 400)
        if path == "/api/agent/review":
            try: return self.send_json(agent_review(body))
            except (ValueError, TypeError) as exc: return self.send_json({"error": str(exc)}, 400)
        if path == "/api/vision/predict":
            try: return self.send_json(vision_prediction(body))
            except (ValueError, TypeError) as exc: return self.send_json({"error": str(exc)}, 400)
        if path == "/api/simulate":
            scenario = body.get("scenario", "stable")
            if scenario not in SCENARIOS: return self.send_json({"error": "Choose stable, watch, noisy-sensor, escalation, or backup."}, 400)
            vitals, equipment, telemetry = SCENARIOS[scenario]
            # Small deterministic-looking jitter keeps demo readings realistic without implying a real sensor.
            jitter = random.randint(-1, 1)
            vitals = dict(vitals); vitals["pulse"] += jitter; vitals["systolic"] += jitter
            note = body.get("english_note", "")[:500]
            with connect() as db:
                prevrow = db.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 1").fetchone()
                previous = as_reading(prevrow) if prevrow else None
                risk = make_risk(vitals, equipment, telemetry, previous, note)
                store_reading(db, scenario, vitals, equipment, telemetry, risk, body.get("source", "simulator"))
            return self.send_json({"ok": True, "risk": risk, "state": state()})
        if path == "/api/notes":
            lang, phrase = body.get("language", "en"), body.get("phrase", "comfortable")
            item = NOTES.get(lang, NOTES["en"]).get(phrase)
            if not item: return self.send_json({"error": "Choose a demo phrase from the phrasebook."}, 400)
            original, english = item
            caregiver = str(body.get("caregiver", "Caregiver Demo"))[:80]
            with connect() as db:
                db.execute("INSERT INTO notes(at,caregiver,language,original,english) VALUES(?,?,?,?,?)", (time.time(), caregiver, lang, original, english))
            return self.send_json({"ok": True, "original": original, "english": english, "state": state()})
        if path == "/api/attendance":
            action = body.get("action", "check-in")
            activity = str(body.get("activity", "Care visit check-in"))[:120]
            caregiver = str(body.get("caregiver", "Caregiver Demo"))[:80]
            if str(body.get("code", "")) != "2468": return self.send_json({"error": "Demo shift code did not match."}, 403)
            with connect() as db:
                db.execute("INSERT INTO attendance(at,caregiver,action,activity) VALUES(?,?,?,?)", (time.time(), caregiver, action, activity))
            return self.send_json({"ok": True, "state": state()})
        if path.startswith("/api/alerts/") and path.endswith("/ack"):
            try: alert_id = int(path.split("/")[3])
            except Exception: return self.send_json({"error": "Invalid alert id."}, 400)
            with connect() as db:
                cur = db.execute("UPDATE alerts SET state='Acknowledged', acknowledged_by=? WHERE id=? AND state='Open'", (str(body.get("caregiver", "Caregiver Demo"))[:80], alert_id))
                if cur.rowcount == 0: return self.send_json({"error": "Alert is already acknowledged or missing."}, 404)
            return self.send_json({"ok": True, "state": state()})
        return self.send_json({"error": "Not found"}, 404)

if __name__ == "__main__":
    initialize()
    # Stay local by default; hosted platforms provide PORT and require a public interface.
    host = os.environ.get("HOST", "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    port = int(os.environ.get("PORT", "8765"))
    print(f"SignalWard demo at http://{host}:{port} (synthetic data only; Ctrl+C to stop)")
    ThreadingHTTPServer((host, port), Handler).serve_forever()

