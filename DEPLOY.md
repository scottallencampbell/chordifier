# Deploying Chordifier

Chordifier runs on **Azure Container Apps** (consumption plan, scale-to-zero) —
free for portfolio-level traffic under the always-free monthly grant
(180k vCPU-seconds, 360k GiB-seconds, 2M requests).

- **Live URL:** https://chordifier.pro (custom domain; default URL
  https://chordifier-prod-web.mangobush-1c047d72.eastus2.azurecontainerapps.io)
- **DNS:** chordifier.pro is at Porkbun — apex A record → 20.80.209.150
  (environment static IP) + TXT `asuid` → domain verification ID. TLS is a
  free auto-renewing Azure managed certificate.
- **Subscription:** Pico (info@bypico.com)
- **Resources:** resource group `chordifier-rg` (eastus2) → environment
  `chordifier-env` (logging disabled) → app `chordifier-prod-web`
  (0.5 vCPU / 1 GiB, min 0 / max 1 replicas)

The image is defined by the `Dockerfile` (gunicorn on `$PORT`, deps from
`requirements-prod.txt`). `requirements.txt` is the old local dev environment
and is not used by the image.

## Shipping an update

1. Push to `master`. The `build-image.yml` GitHub Action builds the image and
   pushes `ghcr.io/scottallencampbell/chordifier:latest` + `:<sha>` to GitHub
   Container Registry (free for public images).
2. Point the app at the new build:

   ```sh
   az containerapp update -n chordifier-prod-web -g chordifier-rg \
     --image ghcr.io/scottallencampbell/chordifier:<sha>
   ```

   Use the commit sha tag rather than `latest` so each deploy is a distinct,
   revertible revision.

## Notes

- The ghcr.io package must stay **public** so Container Apps can pull it
  anonymously when scaling up from zero (package settings on GitHub →
  Change visibility).
- First request after idle has a cold start (~10 s boot, and the first
  /analyze pays ~20 s of numba JIT). Fine for a portfolio.
- Keep `--max-instances 1` / max replicas 1 — caps worst-case cost.
- 1 GiB memory is required; 512 MiB OOMs on full-length songs.
- Don't recreate an Azure Container Registry (`az containerapp up --source`
  does this silently) — Basic tier costs ~$5/mo; ghcr.io is the free path.

## Local run

```sh
PORT=5000 ./venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 300 app:app
```

## Smoke test

```sh
APP=https://chordifier-prod-web.mangobush-1c047d72.eastus2.azurecontainerapps.io
curl $APP/health
curl -X POST -F "file=@uploads/let-it-be.wav" $APP/analyze
```
