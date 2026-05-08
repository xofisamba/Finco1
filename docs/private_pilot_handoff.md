# FincoGPT — Private Pilot Handoff

**Version:** v1.7 Private Pilot
**URL:** https://app.finco.one
**Status:** LIVE (internal use only)

---

## Login

```
Username: admin
Password: [contact your FincoGPT administrator]
```

**Note:** This is a single-admin deployment. Credentials are set via the `FINCO_ADMIN_PASSWORD` (or `FINCO_ADMIN_PASSWORD_HASH`) environment variable on the server.

---

## Supported Workflows

### 1. Solar / Wind Project Run

1. Login at `https://app.finco.one`
2. Select **Solar Base** or **Wind Base** tab
3. Review default inputs (capacity, tariff, CAPEX, tenor, WACC, gearing)
4. Click **Run Model**
5. View KPIs: Project IRR, Equity IRR, LCOE, DSCR

### 2. Custom Inputs

Override defaults in the form before running:
- **Tariff override** — custom PPA price (EUR/MWh)
- **CAPEX override** — custom capital expenditure
- **Gearing** — debt/equity ratio
- **Tenor** — loan repayment period
- **WACC** — weighted average cost of capital

### 3. Scenario Comparison

Run the same project with two different configurations, then use the **Compare** button to see KPI differences side-by-side.

### 4. Save Run

After a successful run, click **Save Run** in the results panel. The run (inputs + KPIs) will be stored in SQLite and appear in the **History** panel.

### 5. Run History

The History panel (available on the index page after login) shows past runs with timestamps. Click a saved run to reload its KPIs.

### 6. Excel Download

The **Download Excel** button exports the current run as an `.xlsx` file containing input summary and KPI results.

### 7. Logout

Click **Logout** in the navigation bar to clear the session.

---

## Known Limitations

### Model Accuracy (Screening-Grade)
- Model outputs are **screening-grade only** — not audited financial advice
- For investment decisions, conduct a full financial model review

### TUHO Wind — CO2 Certificates Missing
- Y1 CO2 certificate revenue (~611 kEUR) is **not included** in the TUHO model
- This causes ~12.5% revenue understatement vs. reference Excel
- Equity IRR impact: approximately −2.99 pp (model: ~8.6% vs. reference: ~11.6%)
- Fix: add CO2 certificate revenue stream (declining ~10%/year with inflation)

### Oborovo Solar — OpEx Duplication
- Y1 OpEx is overstated by ~660 kEUR due to duplicate line items in B.01/B.02 aggregates
- Model: ~1,998 kEUR vs. reference: ~1,338 kEUR
- Fix: prevent sub-item values from being double-counted in aggregate OpEx lines

### Single-Admin Auth (auth-lite)
- Only one admin account is supported (no multi-user/role system)
- Credentials are stored in environment variables — not a user database
- For B2B pilot, consider adding proper user management

### Backup & Recovery
- Daily automatic backup at **02:15 server time** via cron
- Backup location: `/opt/finco1/backups/`
- Format: `finco_runs_YYYYMMDD_HHMMSS.db.xz` (XZ-compressed SQLite)
- Restoration: see `docs/ops_runbook.md`

---

## How to Report Issues

1. **SSH to VPS:** `ssh root@156.67.24.119` (credentials: contact admin)
2. **View logs:** `sudo journalctl -u finco-web -n 50`
3. **Check logs script:** `sudo -u finco /opt/finco1/deploy/scripts/check_logs.sh`
4. **Check app status:** `sudo systemctl status finco-web`
5. **Report:** Open an issue on GitHub with:
   - Steps to reproduce
   - Expected vs. actual behavior
   - Log excerpts (if relevant)

---

## Backup Schedule

```
Daily: 02:15 server time (via /etc/cron.d/finco-backup)
Location: /opt/finco1/backups/
Retention: 30 days (older backups auto-purged)
Log: /var/log/finco-backup.log
```

To run a manual backup:
```bash
sudo -u finco bash /opt/finco1/deploy/scripts/backup.sh
```

---

## Environment

| Variable | Value |
|----------|-------|
| `FINCO_DB_PATH` | `/opt/finco1/app/data/finco_runs.db` |
| `FINCO_SECRET_KEY` | *(set in /opt/finco1/.env)* |
| `FINCO_ADMIN_PASSWORD` | `[set on server]` |

---

## What NOT To Do

- **DO NOT** use for public/production financial decisions (model is screening-grade)
- **DO NOT** share admin credentials beyond the core team
- **DO NOT** install `psycopg2` or set `DATABASE_URL` — this is SQLite-only
- **DO NOT** run `pg_dump` or any PostgreSQL commands

---

## Next Steps (Future)

- Fix TUHO CO2 revenue (P0)
- Fix Oborovo debt-service bug (fixed in P0 sprint — DSCR 0.181→1.250, equity IRR 9.96%→10.16%)
- Fix TUHO Project IRR tax basis (fixed in P0 sprint — project IRR 10.46%→9.47%, now calibrated to reference)
- Fix remaining Oborovo calibration gap: merchant price curve vintage + depreciation convention (P1)
- Multi-user auth with role management
- Full audit-ready financial model
- Production deployment with proper monitoring/alerting