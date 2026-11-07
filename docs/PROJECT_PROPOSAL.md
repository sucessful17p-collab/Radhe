# Idea Submission — SignalWard

**Project title:** SignalWard — Confidence-Aware Home-Care Digital Twin  
**Track:** AI/ML · IoT Simulation · Software Product Development · Cloud/Edge Computing  
**Team:** Radhe

## Problem statement
Home-care data can be misleading when viewed as isolated numbers. A concerning reading may reflect a changing patient pattern, a noisy sensor, stale data, or a device/power problem. Simple threshold dashboards can confuse these cases, while caregiver observations and equipment status are often disconnected from the readings. During connectivity interruptions, even a useful alert may not reach the right person.

## Proposed solution
SignalWard is an edge-first home-care “digital twin” demo that maintains two separate views of the same care episode:

1. **Patient trajectory:** an explainable synthetic model compares readings with the configured demo baseline, recent direction, and caregiver-note context.
2. **Evidence confidence:** a separate gate checks sensor signal quality and reading freshness before displaying the patient-state score.

If the sensor evidence is weak or stale, SignalWard withholds the patient-state score and opens an **Evidence Check** alert. It does not turn a poor reading into a patient-risk conclusion. If the signal is reliable and multiple synthetic changes persist, it displays an illustrative 24–48 hour trend flag with the factors that contributed. Equipment/power issues are tracked as a separate care-context signal. Caregivers can acknowledge alerts, log visit activity, and add a fixed phrasebook note in English, Hindi, Spanish, or Tamil.

The dashboard also demonstrates a local offline queue and a backup-power scenario. All data is generated; no hardware or external service is needed.

## What makes it different
- **Separates patient risk from sensor trust:** weak evidence produces a measurement-quality workflow, not a high patient-risk score.
- **Shows uncertainty directly:** every current view includes signal quality, freshness, and confidence; weak evidence suppresses the score.
- **Lets judges inject a counterexample:** the “Noisy sensor” scenario creates an alarming-looking synthetic value with poor signal quality. Compare it with a clean, sustained multi-signal drift.
- **Keeps the human in the loop:** alerts show their evidence, remain acknowledgeable, and point to the clinician-approved care plan rather than prescribing treatment.
- **Continues during a simulated outage:** browser actions queue locally and sync after reconnection; equipment state can switch to backup power.

## Technology stack
- **Frontend:** HTML, CSS, vanilla JavaScript, SVG trend chart.
- **API and simulator:** Python standard-library HTTP server with JSON endpoints.
- **Persistence:** SQLite local database.
- **Risk model:** logistic regression fitted at startup on deterministic generated examples; an independent evidence-confidence gate uses simulated signal quality and freshness.
- **Resilience:** browser localStorage store-and-forward queue and mock backup-power telemetry.
- **Deployment:** localhost only; no third-party API or package installation.

## MVP workflow
1. Simulated sensors send vitals, equipment state, signal-quality percentage, freshness, and a source label.
2. The dashboard compares patient readings with a synthetic personal baseline and recent trend.
3. The evidence gate checks whether the packet is reliable enough to show a patient-state score.
4. A clean trend can create an explainable synthetic 24–48 hour escalation-pattern flag; a noisy packet creates an Evidence Check instead.
5. The caregiver reviews the evidence, adds a multilingual phrasebook note, acknowledges the alert, or logs a visit activity.
6. If connectivity is simulated as interrupted, actions queue locally and sync later.

## Expected outcome and evaluation
This prototype should demonstrate an end-to-end flow and a clear counterexample. Measure the system against its own scenario set:

- Noisy-sensor packets route to Evidence Check and withhold patient score.
- Clean stable packets do not create a patient-trend alert.
- Clean drift packets produce a reasoned synthetic trend flag.
- Device disconnection remains visible as an equipment context signal.
- Offline actions queue and sync after reconnect.
- Caregiver notes display the source phrase and fixed English equivalent.

These are software-behavior checks, not clinical-performance metrics or evidence of health benefit. The model is trained only on generated examples and is not clinically validated.

## Clinical safety and privacy
All profile, reading, note, and attendance records are synthetic. The model must not be used to diagnose, predict a real patient’s condition, or guide treatment. Signal quality cannot prove a sensor reading is correct; it only marks demo evidence as more or less trustworthy. For real care, follow the clinician-approved plan and qualified professionals; for urgent symptoms, contact local emergency services. The FDA notes pulse-oximeter readings can be inaccurate under some circumstances, and clinical decision support should support rather than replace clinician judgment. See the FDA’s [pulse oximeter overview](https://www.fda.gov/medical-devices/products-and-medical-procedures/pulse-oximeters) and the eCQI Resource Center’s [clinical decision support overview](https://ecqi.healthit.gov/cds/about).

