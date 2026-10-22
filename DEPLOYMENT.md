# SKYTRACE V1 — Deployment Record & V1.1 Roadmap

**Release:** V1 deployed prototype
**Deployment commit:** `4ec700e` — Add Render API deployment and Vercel proxy
**Record updated:** 2026-10-23
**Hosting target:** ₹0 using free tiers; provider limits and eligibility apply.

## 1. Live deployment

| Component | URL | Verification |
|---|---|---|
| Frontend | https://skytrace-gamma.vercel.app | Production deployment showed Ready; production screening proxy returned JSON |
| Python API | https://skytrace-api.onrender.com | Render service showed Live |
| Health endpoint | https://skytrace-api.onrender.com/health | Returned `{"service":"SKYTRACE","status":"ok"}` |
| Screening endpoint | https://skytrace-api.onrender.com/api/screening?top=5 | Returned screening JSON |
| Production screening proxy | https://skytrace-gamma.vercel.app/api/screening?top=5 | Returned screening JSON |
| Source repository | https://github.com/HeamakeshBajina/skytrace | GitHub repository |

The deployment files were committed in `4ec700e`. The deployment was tested through live API responses. Free-tier usage limits, cold starts, and account eligibility still apply; this record does not guarantee future costs will always be zero.

## 2. Architecture

```text
User
  |
  v
Next.js frontend (Vercel)
  |
  v
/api/screening — server-side Vercel proxy
  |  SKYTRACE_API_URL
  v
FastAPI backend (Render Free)
  |
  +--> Check TLE snapshot retrieval metadata
  +--> Refresh TLE data if retrieval age exceeds threshold
  +--> Run scripts/screen_approaches.py
          |
          v
      SGP4 orbital propagation
          |
          v
      Instantaneous pairwise state separations
          |
          v
      JSON results + data-quality flags
  |
  v
Vercel proxy response -> frontend
```

### Responsibilities

- **Next.js frontend:** public user interface, rooted in `web/`.
- **Vercel proxy:** forwards `/api/screening` requests to the backend URL stored in the server-side `SKYTRACE_API_URL` environment variable; clamps `top` to 1–200 and disables caching for the request.
- **FastAPI on Render:** exposes `/health` and `/api/screening`, checks recorded TLE retrieval age, attempts refresh when needed, and invokes the Python screening script.
- **SGP4 screening engine:** propagates states from TLEs, calculates instantaneous pairwise state separations, and emits results and data-quality flags.

## 3. Verification record

Checks completed during the deployment workflow:

- GitHub Actions test workflow passed.
- Python test suite: 71 tests passed.
- Frontend lint and production build passed.
- Deployment dependency installation and imports passed.
- Render `/health` responded successfully.
- Render `/api/screening?top=5` returned expected JSON.
- Vercel production `/api/screening?top=5` returned the screening JSON.

One observed screening response reported:

| Metric | Observed value |
|---|---:|
| Input objects | 17 |
| Pairs evaluated | 136 |
| Duplicate-state pairs | 16 |
| Pairs screened | 120 |
| Results returned | 5 |

These are observations from the tested response, not a guarantee that every future run will have the same counts.

## 4. Scientific scope and caveats

SKYTRACE V1 is an exploratory screening prototype. The returned distances are **instantaneous SGP4 state separations**, not verified closest-approach predictions.

- Duplicate-state flags mean matching numerical states; they are not collision alerts.
- Sampled minima are not guaranteed to be continuous-time minima.
- The prototype does not calculate collision probability or provide operational risk assessment.
- TLE retrieval age and orbital epoch age are different measurements.
- TLE age alone does not quantify orbital uncertainty.

In the tested response, the oldest orbital epoch was approximately 70.1 hours old, while the snapshot file had a separate recorded retrieval timestamp. Fresh retrieval does not, by itself, prove the orbital elements are accurate or current enough for a particular analysis.

## 5. V1.1 roadmap

### Priority 1 — Investigate duplicate-state flags

- [ ] Trace each catalog ID from the raw TLE file through parsing and propagation.
- [ ] Verify that names, catalog IDs, and the corresponding two TLE lines remain correctly paired.
- [ ] Compare the raw TLE records for each flagged pair.
- [ ] Check for accidental reuse of parsed records, cached states, or object references.
- [ ] Add tests that verify each catalog ID maps to its intended TLE record.
- [ ] Add regression tests for duplicate-state detection.
- [ ] Document the explanation for every investigated pair; do not simply suppress flags.

**Acceptance criteria:** Each flagged pair has an investigated explanation and automated tests cover any identified defect.

### Priority 2 — Make TLE freshness transparent

- [ ] Return and display the snapshot retrieval timestamp.
- [ ] Report retrieval age separately from each object's orbital epoch age.
- [ ] Preserve oldest/youngest orbital epoch age summaries.
- [ ] Report whether a refresh was attempted and whether it succeeded.
- [ ] Warn when orbital elements are old, even if the file was downloaded recently.
- [ ] Test missing, malformed, future-dated, and stale retrieval metadata.
- [ ] Test refresh failures and ensure stale data is not silently represented as fresh.

**Acceptance criteria:** API and frontend clearly distinguish retrieval time from orbital epoch age and do not imply that fresh retrieval proves orbital accuracy.

### Priority 3 — Communicate scientific limitations

- [ ] Label results as instantaneous state separations.
- [ ] Explain the limitations of sampled minima.
- [ ] State that collision probability and operational risk assessment are not performed.
- [ ] Explain that TLE age alone does not quantify orbital uncertainty.
- [ ] Avoid presenting prototype results as operational collision alerts.

### Priority 4 — Reliability and observability

- [ ] Add automated smoke tests for production `/health` and `/api/screening`.
- [ ] Verify malformed query parameters and backend failure responses.
- [ ] Record software version and data timestamps in diagnostics.
- [ ] Test Render Free cold starts and timeout behavior.
- [ ] Monitor provider usage to help maintain the ₹0 hosting target.
- [ ] Document a rollback procedure for broken deployments.

## 6. Release strategy

- **V1:** Deployed exploratory prototype; core deployment and screening endpoints verified.
- **V1.1:** Data-integrity investigation, clearer freshness reporting, scientific-scope communication, and stronger production checks.
- **V1.1 release gate:** Do not claim scientific validation is improved until duplicate-state causes have been investigated, relevant tests pass, and freshness reporting has been verified.

## 7. Portfolio summary

SKYTRACE is a deployed aerospace-oriented software prototype connecting a Next.js frontend to a Python/FastAPI backend and an SGP4 orbital screening engine. The system uses a server-side API proxy, environment-based backend configuration, automated tests, and explicit data-quality reporting.

The next engineering milestone focuses on validating input-data integrity, improving orbital-data freshness transparency, and responsibly communicating the limitations of preliminary orbital screening.

**Portfolio positioning:** Describe the implemented system, deployment architecture, testing, debugging, and planned validation work. Do not claim operational collision prediction or verified collision-avoidance capability.
