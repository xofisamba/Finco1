# Deployment Smoke Test Checklist

**Date:** 2026-05-07
**Target:** `app.finco.one` — Contabo private deployment
**Purpose:** Verify HTMX internal demo is working correctly after deployment or restart

---

## Pre-Flight

### Quick external smoke (no auth required)

```bash
# Public health check — proves domain/SSL/nginx/app stack is up
# Does NOT prove model routes are functional
curl -s https://app.finco.one/public-health
# Expected: {"status":"ok","app":"fincogpt","mode":"internal-demo"}

# Authenticated internal health (requires Basic Auth)
curl -s -u admin:YOUR_PASSWORD https://app.finco.one/health
# Expected: {"status":"ok"}
```

---

### Service checks

```bash
# Check service is running
systemctl status finco-web

# Check logs
journalctl -u finco-web --since "5 minutes ago" | tail -20

# Check Nginx is proxying
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health
# Expected: 200
```

---

## Smoke Tests

Run each test with `curl` or browser. Record result.

### 1. GET /

```bash
curl -s -o /dev/null -w "%{http_code}" https://app.finco.one/
```
**Expected:** HTTP 200  
**Pass:** ☐ | **Fail:** ☐

### 2. POST /run — Solar Base

```bash
curl -s -X POST \
  -d "project_type=Solar&scenario=Base" \
  https://app.finco.one/run | grep -c "Project IRR"
```
**Expected:** ≥ 1 occurrence of "Project IRR"  
**Pass:** ☐ | **Fail:** ☐

### 3. POST /run — Wind Base

```bash
curl -s -X POST \
  -d "project_type=Wind&scenario=Base" \
  https://app.finco.one/run | grep -c "IRR"
```
**Expected:** ≥ 1 occurrence  
**Pass:** ☐ | **Fail:** ☐

### 4. Custom tariff changes KPIs

```bash
LOW=$(curl -s -X POST -d "project_type=Solar&scenario=Base&tariff_eur_mwh=60" \
  https://app.finco.one/run | grep -o "Total Revenue[^<]*<[^>]*>[0-9,]*" | grep -o "[0-9,]*" | head -1)
HIGH=$(curl -s -X POST -d "project_type=Solar&scenario=Base&tariff_eur_mwh=150" \
  https://app.finco.one/run | grep -o "Total Revenue[^<]*<[^>]*>[0-9,]*" | grep -o "[0-9,]*" | head -1)
echo "Low: $LOW, High: $HIGH"
[ "$LOW" != "$HIGH" ] && echo "PASS" || echo "FAIL"
```
**Expected:** Different revenue for different tariff  
**Pass:** ☐ | **Fail:** ☐

### 5. Custom CAPEX changes KPIs

```bash
IRR_LOW=$(curl -s -X POST -d "project_type=Solar&scenario=Base&total_capex_keur=40000" \
  https://app.finco.one/run | grep -o "Project IRR[^<]*<[^>]*>[0-9.]*%" | grep -o "[0-9.]*%")
IRR_HIGH=$(curl -s -X POST -d "project_type=Solar&scenario=Base&total_capex_keur=80000" \
  https://app.finco.one/run | grep -o "Project IRR[^<]*<[^>]*>[0-9.]*%" | grep -o "[0-9.]*%")
echo "Low CAPEX IRR: $IRR_LOW, High CAPEX IRR: $IRR_HIGH"
```
**Expected:** Lower CAPEX → higher IRR  
**Pass:** ☐ | **Fail:** ☐

### 6. Compare scenarios

```bash
curl -s -X POST -d "project_type=Solar" \
  https://app.finco.one/compare | grep -c "Base"
```
**Expected:** "Base" appears in comparison table  
**Pass:** ☐ | **Fail:** ☐

### 7. Invalid gearing returns friendly error

```bash
curl -s -X POST -d "project_type=Solar&scenario=Base&gearing_pct=150" \
  https://app.finco.one/validate | grep -i "gearing\|must be"
```
**Expected:** Error message mentions "gearing" or "must be"  
**Pass:** ☐ | **Fail:** ☐

### 8. Download Excel — GET

```bash
curl -s -I "https://app.finco.one/download?project_type=Solar&scenario=Base" \
  | grep -i "content-type"
```
**Expected:** `application/vnd.openxmlformats`  
**Pass:** ☐ | **Fail:** ☐

### 9. Download Excel — POST with custom inputs

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST \
  -d "project_type=Solar&scenario=Base&tariff_eur_mwh=90&total_capex_keur=55000" \
  https://app.finco.one/download
```
**Expected:** HTTP 200 with xlsx content-type  
**Pass:** ☐ | **Fail:** ☐

### 10. HTTPS lock works

Open `https://app.finco.one/` in browser — verify:
- 🔒 Lock icon in address bar
- Certificate valid (not expired)
- No "Your connection is not private" warning

**Pass:** ☐ | **Fail:** ☐

### 11. Basic auth works (if enabled)

```bash
curl -s -o /dev/null -w "%{http_code}" \
  --user admin:PASSWORD \
  https://app.finco.one/
```
**Expected:** 200 (auth passes)  
Without credentials: 401

**Pass:** ☐ | **Fail:** ☐ (N/A if not enabled)

### 12. Static assets load

```bash
curl -s -o /dev/null -w "%{http_code}" https://app.finco.one/static/styles.css
```
**Expected:** HTTP 200  
**Pass:** ☐ | **Fail:** ☐

### 13. No traceback exposure

```bash
curl -s -X POST -d "project_type=Banana&scenario=Base" \
  https://app.finco.one/validate | grep -c "Traceback\|AttributeError"
```
**Expected:** 0 occurrences  
**Pass:** ☐ | **Fail:** ☐

### 14. Restart survives reboot

```bash
# Simulate restart
sudo systemctl restart finco-web
sleep 3
curl -s -o /dev/null -w "%{http_code}" https://app.finco.one/health
```
**Expected:** 200 after restart  
**Pass:** ☐ | **Fail:** ☐

---

## Results Summary

| Test | Pass | Fail | Notes |
|------|------|------|-------|
| 1. GET / | ☐ | ☐ | |
| 2. POST /run Solar | ☐ | ☐ | |
| 3. POST /run Wind | ☐ | ☐ | |
| 4. Custom tariff | ☐ | ☐ | |
| 5. Custom CAPEX | ☐ | ☐ | |
| 6. Compare | ☐ | ☐ | |
| 7. Invalid gearing | ☐ | ☐ | |
| 8. Download GET | ☐ | ☐ | |
| 9. Download POST | ☐ | ☐ | |
| 10. HTTPS lock | ☐ | ☐ | |
| 11. Basic auth | ☐ | ☐ | |
| 12. Static assets | ☐ | ☐ | |
| 13. No traceback | ☐ | ☐ | |
| 14. Restart survives | ☐ | ☐ | |

**Total:** ___/14 passed

---

## If Any Test Fails

1. Check `journalctl -u finco-web -n 50` for errors
2. Check Nginx error log: `/var/log/nginx/error.log`
3. Verify Python dependencies: `pip list | grep -E "fastapi|uvicorn|jinja2|gunicorn"`
4. Run model locally: `python3 main_web.py` (should start on port 8765)
5. Check SSL certificate: `certbot certificates`

---

## Contact

If all 14 tests pass → deployment is healthy.
If any test fails → investigate before exposing to users.