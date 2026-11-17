# SafarSaathi

**AI-Powered Tourism Intelligence & Resilience Platform** for Uttarakhand and India: a destination-level
decision-support system that links visitor demand with capacity, climate, flood and cyclone evidence.

**Predict → simulate → optimise → explain → support human action.**

- Tourism demand forecasts with held-out error and explanations
- A digital twin of 28 Uttarakhand destinations with a transparent Destination Stress Index and what-if scenarios
- Hotspot clustering and anomaly detection (checked against the 2013 disaster and COVID)
- Risk-aware routing on the OpenStreetMap road network, with simulated road closures
- Flood segmentation on Sentinel-1 radar, a cyclone-count forecaster and review sentiment
- GA / PSO optimisers, including an intervention planner checked against the exhaustive optimum
- Six saved models released as **v1.0** through an evidence-based release gate

## Quick start

Windows: double-click **`START_SAFARSAATHI.bat`**, then open <http://localhost:8000>.

Anywhere else:

```bash
cd SafarSaathi_Project
python -m pip install -r requirements.txt
python run_safarsaathi.py
```

Full documentation, model results, data sources and limitations:
**[SafarSaathi_Project/README.md](SafarSaathi_Project/README.md)**.

An AIML team project at Bennett University.
