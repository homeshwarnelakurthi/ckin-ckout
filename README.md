# CK_IN&CK_OUT — Personal Time Tracking

A mobile-first time-tracking web app for **patel** (a hotel manager) to track
his own clock-in/clock-out and pay at a configurable **$0/hour**. Single
account, no employee management — just a big Clock In / Clock Out button,
a running history, and self-service corrections.

- **Backend:** Python · FastAPI · SQLAlchemy · SQLite (or Postgres) · JWT + bcrypt
- **Frontend:** React · TypeScript · Tailwind CSS · Vite

---

## Features

- Single login (simple username + password, bcrypt-hashed) with **failed-login rate limiting**.
- One large, state-aware **Clock In (green) / Clock Out (red)** button with a
  live shift timer.
- **You can never have two open shifts at once** — enforced at the API *and*
  by a partial unique index in the database.
- Shifts left open past a configurable threshold (default **14h**) are
  **auto-flagged** instead of silently mis-calculating pay.
- Today / This week / This month totals, a weekly hours bar chart, and a
  paginated shift history.
- Inline **corrections** (fix a forgotten clock-out, etc.) — every edit is
  written to an audit log and pay is recalculated automatically.
- One-click **CSV export** of your timesheet.
- All timestamps stored in **UTC**, rendered in your local timezone.

---

## Quick start (local dev)

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
#                              source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cp ../.env.example .env       # uses SQLite by default, no DB server needed
python -m app.seed            # creates a demo login with sample shifts
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to :8000
```

### Demo login (from the seed script)

| Username | Password |
| -------- | -------- |
| `123`    | `1234`   |

The seed also creates illustrative shifts: two shifts in one day, a shift
that crosses midnight, and a forgotten clock-out that's auto-flagged. Seed
data is for local dev only — see below for how the *live* deployment gets a
clean account with no fake shifts.

---

## Testing

```bash
cd backend
pytest -q
```

Covers the required calculation edge cases (multiple shifts per day, crossing
midnight, forgotten clock-out excluded from pay), the no-double-open-shift
rule, self-correction + audit log, CSV export, and the account bootstrap
logic. Runs on an in-process SQLite DB — no external DB needed.

Frontend typecheck + build:

```bash
cd frontend && npm run build
```

---

## Deploying so it works from your phone (Render, free)

This deploys a real, permanent URL you can open from any browser. Steps:

### 1. Push this project to GitHub

```bash
git init
git add -A
git commit -m "Initial commit"
```
Then create an empty repo at <https://github.com/new> (don't add a README —
this project already has one), and push:
```bash
git remote add origin https://github.com/<you>/<repo>.git
git branch -M main
git push -u origin main
```

### 2. Create a free Render account

Go to <https://render.com>, sign up (free, "Sign up with GitHub" is easiest),
and authorize it to access your new repo.

### 3. Deploy with the included Blueprint

This repo has a [`render.yaml`](render.yaml) that provisions everything —
a free Postgres database, the backend API, and the frontend — in one shot:

1. In the Render dashboard: **New +** → **Blueprint**.
2. Select your repo. Render reads `render.yaml` and shows 3 resources to create:
   `ckin-ckout-db`, `ckin-ckout-backend`, `ckin-ckout-frontend`.
3. Click **Apply**. First deploy takes a few minutes.

### 4. Connect the two services and set your real login

Once both services have URLs (e.g. `https://ckin-ckout-backend.onrender.com`
and `https://ckin-ckout-frontend.onrender.com`):

1. On **ckin-ckout-backend** → Environment, set:
   - `FRONTEND_ORIGIN` = your frontend's URL
   - `BOOTSTRAP_USERNAME` = whatever you want to log in with — plain numbers
     are fine, e.g. `123`
   - `BOOTSTRAP_PASSWORD` = a real password, e.g. `1234` (this creates your
     one account on next boot — after it's created, you can clear this
     variable's value if you want)
2. On **ckin-ckout-frontend** → Environment, set:
   - `VITE_API_BASE` = your backend's URL
3. Manually redeploy both (Render does this automatically on env var changes
   for the backend; the frontend needs a manual redeploy since `VITE_API_BASE`
   is baked in at build time).

Open the frontend URL on your phone and log in with the username/password from
step 4.1 — your account now has zero shifts, ready for real use.

**Forgot your password later?** Set `BOOTSTRAP_PASSWORD` to a new value, add
`FORCE_PASSWORD_RESET` = `true`, save (triggers a restart), log in, then set
`FORCE_PASSWORD_RESET` back to `false` so a future restart can't reset it again.

### Things to know about the free tier

- **The backend sleeps after 15 minutes idle.** The first clock-in after a
  gap can take ~30–50 seconds to wake up — normal, just wait.
- **The free Postgres database expires after 90 days** unless upgraded
  (~$7/mo). Render emails a warning before it happens. If you'd rather not
  pay, you can always spin up a fresh free database and re-bootstrap — you'll
  just lose shift history from before that point.
- No credit card is required to deploy this on the free tier.

---

## Environment variables

See [`.env.example`](.env.example). Key ones:

| Variable                          | Purpose                                             | Default                   |
| ---------------------------------- | ---------------------------------------------------- | -------------------------- |
| `DATABASE_URL`                    | SQLAlchemy connection string                        | local SQLite file          |
| `JWT_SECRET`                      | JWT signing key (**set a strong value in prod!**)   | `change-me-in-production`  |
| `BOOTSTRAP_USERNAME` / `_PASSWORD` | Creates your one real account on first boot         | unset (no bootstrap)       |
| `FORCE_PASSWORD_RESET`            | Overwrites the existing password on next boot        | `false`                    |
| `DEFAULT_HOURLY_RATE`             | Pay rate used for calculations                        | `10.00`                    |
| `OPEN_SHIFT_FLAG_THRESHOLD_HOURS` | Auto-flag shifts open longer than this                | `14`                       |
| `DISPLAY_TIMEZONE`                | Timezone for rendering (storage is always UTC)        | `America/New_York`         |
| `LOGIN_MAX_ATTEMPTS` / `_WINDOW_SECONDS` | Login rate limit                                | `5` / `300`                |
| `VITE_API_BASE` (frontend build)  | Backend URL baked into the SPA                        | empty (dev proxy)          |

---

## API reference

All non-auth endpoints require `Authorization: Bearer <jwt>`.

| Method | Endpoint                          | Purpose                          |
| ------ | ---------------------------------- | --------------------------------- |
| POST   | `/api/auth/login`                  | Authenticate, return JWT          |
| POST   | `/api/clock-in`                    | Open a time entry                 |
| POST   | `/api/clock-out`                   | Close entry, compute pay / flag   |
| GET    | `/api/timesheet/me?from=&to=`      | Your entries in a date range      |
| GET    | `/api/timesheet/me/summary`        | Today / week / month totals       |
| PATCH  | `/api/timesheet/me/entries/:id`    | Correct your own entry (audit-logged) |
| GET    | `/api/timesheet/me/export?format=csv` | CSV export                    |
| GET    | `/api/me`                          | Current user                      |
| GET    | `/api/meta`                        | Branding / config (public)        |

---

## Project structure

```
backend/
  app/
    main.py                # FastAPI app, meta/health/me routes, account bootstrap
    config.py               # env-driven settings (no hardcoded literals)
    database.py             # engine, session, portable GUID type
    models.py               # users, time_entries, entry_audit_log
    schemas.py               # Pydantic request/response models
    security.py              # bcrypt hashing, JWT, login rate limiter
    payroll_calculator.py    # isolated, unit-tested hours & pay logic
    timeutils.py             # local period boundaries -> UTC
    routers/                 # auth, clock, timesheet (incl. corrections + export)
    seed.py                  # local-dev-only demo account + sample shifts
  tests/                     # payroll edge cases + API tests
frontend/
  src/                       # React + TS app (auth, pages, components)
render.yaml                  # Render Blueprint: DB + backend + frontend
.github/workflows/ci.yml     # test + build on push/PR
```

---

## Notes

- **$10/hour** is implemented exactly as specified. Before using this for real
  payroll, confirm it clears the applicable local minimum wage — the rate
  lives in `DEFAULT_HOURLY_RATE` / the user's `hourly_rate` column, so
  changing it never requires a code edit.
- No overtime multiplier in v1 (flat rate). The calculator is structured so a
  rate tier or overtime rule could be added without a rewrite.
- The app also runs fine in Docker (`backend/Dockerfile`, `frontend/Dockerfile`)
  if you'd rather self-host on any container platform instead of Render.
