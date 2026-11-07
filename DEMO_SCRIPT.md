# SignalWard — three-minute demo script

**Runtime:** about 3 minutes  
**Setup:** Run `python server.py`, open `http://127.0.0.1:8765`, keep the safety banner visible, use synthetic scenarios only. Demo caregiver code: `2468`.

## 0:00–0:20 — The idea

**On screen:** SignalWard dashboard and simulation-only banner.

**Say:** “SignalWard is a hardware-free home-care digital twin demo. Its main design choice is to separate patient-state patterns from evidence quality. A poor sensor signal should not become a confident patient-risk alert.”

## 0:20–0:45 — Sensor to platform

**Action:** Click **Stable**. Point to vitals, mock equipment state, signal quality, and the trend chart.

**Say:** “The simulator sends vitals, device state, signal quality, and freshness to a local Python API. The dashboard keeps a synthetic baseline and shows where each reading came from.”

## 0:45–1:15 — The counterexample: noisy sensor

**Action:** Click **Noisy sensor**. Point to the unusual synthetic reading, low signal confidence, withheld patient score, and Evidence Check alert.

**Say:** “This value looks concerning, but the simulated sensor quality is poor. SignalWard withholds the patient-state score and raises an Evidence Check instead. It does not treat bad evidence as proof of patient deterioration. A real system would use verified device signals and clinician-approved workflows.”

## 1:15–1:45 — Reliable trend + caregiver context

**Action:** Click **Stable**, then **Watch**. Add “More tired than usual” in Hindi or Spanish. Point to the original phrase, English equivalent, confidence, and model reasons.

**Say:** “Now the signal quality is high and several synthetic readings drift together. The toy logistic model shows an illustrative 24-to-48-hour escalation-pattern label and its contributing factors. The caregiver phrase adds context. This is generated data and not a clinical forecast.”

## 1:45–2:10 — Alert and equipment state

**Action:** Click **Escalation**, show the combined patient/device review, acknowledge the alert, and log an equipment check with code `2468`.

**Say:** “The system keeps equipment state visible alongside the patient trend, then records a caregiver acknowledgement. It never prescribes treatment; the care team follows the approved care plan.”

## 2:10–2:35 — Connectivity and power

**Action:** Toggle **Online** to simulated offline, click **Power backup**, then reconnect and sync the queued event.

**Say:** “During simulated connectivity loss, browser actions queue locally and sync after reconnect. The equipment panel shows the backup-power state. The server itself is still running on this laptop, so this demonstrates store-and-forward behavior rather than a powered-off host.”

## 2:35–3:00 — Close

**On screen:** Point to the model disclaimer, then show the technical documentation.

**Say:** “The project demonstrates sensor simulation, confidence-aware risk, caregiver context, alert response, and resilience. Every number and model label is synthetic. A real deployment would require device validation, clinical governance, privacy and security controls, and prospective evaluation before any care use.”

## Recording checklist

- Capture the full 16:9 dashboard at readable zoom.
- Keep the simulation-only disclaimer visible.
- Use the Noisy Sensor counterexample; it is the clearest innovation moment.
- Do not enter real health information.
- Record the local app walkthrough; this script is narration, not a pre-recorded video.
