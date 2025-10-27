# IIS 502.3 Bad Gateway (httpPlatform) – Troubleshooting for PodWeb

This guide helps you diagnose and fix 502.3 errors when hosting this Flask app behind IIS using httpPlatformHandler + Waitress.

## Quick checklist

- App pool identity has Modify rights on the site folder (write logs and DBs)
- Python venv exists and matches web.config path
- Secret key file exists: `secret_key.txt`
- GeoIP database present: `geoip/GeoLite2-City.mmdb` (optional)
- httpPlatformHandler is installed in IIS
- Process starts within 90s and binds to the port in `HTTP_PLATFORM_PORT`

## 1) Confirm venv and paths

- Verify this path exists on the server:
  - `C:\inetpub\podsinspace\.venv\Scripts\python.exe`
- If not, create the venv and install requirements:

```powershell
cd C:\inetpub\podsinspace
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2) Ensure write permissions for IIS

The app writes:
- Logs to `C:\inetpub\podsinspace\logs`
- SQLite DBs to `C:\inetpub\podsinspace\instance`

Grant Modify to the IIS group:

```powershell
icacls "C:\inetpub\podsinspace" /grant "IIS_IUSRS:(OI)(CI)M" /T
```

Restart IIS afterwards:

```powershell
iisreset
```

## 3) Check httpPlatform stdout logs

`web.config` is configured to capture process output:
- `C:\inetpub\podsinspace\logs\httpplatform-stdout*.log`

Open the newest file after a failed request to see Python errors at startup.

## 4) App logs

- Waitress log: `logs/waitress_app.log` (created by `waitress_app.py`)
- App log: `logs/main_app.log`

If these files don’t appear, it’s usually a permissions or early-import error.

## 5) Secret key and DB creation

- `secret_key.txt` must exist (run `generate_secret_key.py` locally if missing)
- The app creates SQLite DBs in `instance/`. If creation fails due to permissions, startup fails.

## 6) Health check

From the server, browse or curl:
- `http://localhost/podsinspace/health`

You should see `{ "status": "ok" }`.

If localhost works but the public URL doesn’t, check any external reverse proxy/firewall.

## 7) URL base path alignment

The app is mounted at `/podsinspace` (see `APPLICATION_ROOT`). Make sure your IIS site/app maps the site root to this folder so `/podsinspace/*` URLs reach the app.

## 8) Common root causes

- Wrong `processPath` or missing venv: 502.3 immediately
- No write access to `logs/` or `instance/`: import-time logging/DB init fails
- Missing `secret_key.txt`: startup exception
- Long dependency install on cold start: increase `startupTimeLimit` (now 90s)
- Not binding to `HTTP_PLATFORM_PORT`: ensure `waitress_app.py` reads the env var (it does)

## 9) Windows Event Viewer

If all else fails, check Application logs for httpPlatformHandler errors for more detail.

## 10) Optional: Manual run test

Run the app by hand (bypassing IIS) to spot Python-level errors quickly:

```powershell
cd C:\inetpub\podsinspace
.\.venv\Scripts\Activate.ps1
python waitress_app.py
# Expect: "Starting Waitress server on 127.0.0.1:<port>" and logs in logs/waitress_app.log
```

Then in another shell:

```powershell
curl http://127.0.0.1:8080/podsinspace/health
```

If this succeeds, the Python app is fine—focus on IIS/permissions.

---

If you keep seeing 502.3, share the most recent lines from `logs/httpplatform-stdout*.log` and `logs/waitress_app.log` and we can pinpoint the exact failure.
