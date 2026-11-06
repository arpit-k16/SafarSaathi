# Render deployment

The production ASGI application is `safarsaathi_ml.asgi:app`. It is a thin FastAPI adapter over the existing SafarSaathi route and inference functions; it does not train models or provide mock predictions.

Configure the Render service as follows:

- Root Directory: `SafarSaathi_Project`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn safarsaathi_ml.asgi:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`
- Python: `3.12.8`

Set `SAFARSAATHI_CORS_ORIGINS` to the exact comma-separated Vercel production and preview origins, for example `https://your-project.vercel.app`. Do not use `*` in production. Set `VITE_SAFARSAATHI_API_URL` in Vercel to the public HTTPS URL of this Render service, then rebuild the frontend.

Saved model artifacts under `models/` are deployed with the service. Raw datasets and generated research data remain excluded; routes which genuinely require unavailable raw data return a clear `503` rather than fabricated output.
