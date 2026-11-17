# Deployment

## Recommended: one Docker service on Render (console + API, same origin)

1. Push the repository to GitHub (the root `.gitignore` keeps raw data out but ships `models/`,
   `deploy_snapshot/`, `data/processed/` and the small `outputs/` files the API needs).
2. In Render choose **New → Blueprint** and point it at the repo; `SafarSaathi_Project/render.yaml`
   creates the `safarsaathi` Docker web service. Health check: `/health`.
3. Open the service URL. The console is served at `/`; the API answers at both `/…` and `/api/…`.

Build locally instead: `docker build -t safarsaathi SafarSaathi_Project && docker run -p 8000:8000 safarsaathi`.

The image pins scikit-learn 1.9.1 / numpy 2.4.6 / pandas 2.3.3 / joblib 1.6.0 — the versions the
saved artifacts were trained with. Do not loosen these pins.

## Data on the server: the deployment snapshot

Raw datasets (≈ GBs) are never deployed. Routes that read them fall back to `deploy_snapshot/`,
a checksum-verified capture of the same adapter outputs made on a machine that has the data.
Every such response carries `data_origin: "BUILD_SNAPSHOT"` and the capture time; `GET /deployment/status`
lists what is live and what is snapshot.

Refresh it (required once for `/datasets` and `/satellite/metadata`, which need the full raw collection):

```powershell
cd SafarSaathi_Project
$env:PYTHONPATH = 'src'
python -m safarsaathi_ml.cli build-snapshot          # all sections
python -m safarsaathi_ml.cli build-snapshot --sections dataset_files   # just the inventory
```

`SAFARSAATHI_DATA_MODE` = `auto` (default: live files if present, else snapshot), `live` or `snapshot`.

## Alternative: console on Vercel, API on Render

- Vercel: root `SafarSaathi_Project/web`, framework Vite, env `VITE_SAFARSAATHI_API_URL=https://<render-service>.onrender.com`.
- Render: set `SAFARSAATHI_CORS_ORIGINS=https://<project>.vercel.app` (comma-separated, no `*`);
  optionally `SAFARSAATHI_CORS_ORIGIN_REGEX=https://<project>-.*\.vercel\.app` for preview deployments.
