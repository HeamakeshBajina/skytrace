# SKYTRACE V1 — User Guide

Welcome to SKYTRACE! This guide explains how to use the dashboard in simple language.

## 1. What is SKYTRACE?

SKYTRACE is an experimental aerospace engineering project. It uses satellite orbital data to estimate object positions and compare the distances between pairs of objects.

It is a learning and research prototype, not an operational collision-warning system.

## 2. How to use the dashboard

1. Open https://skytrace-gamma.vercel.app/
2. Wait for the dashboard to load.
3. Read the summary cards to see how many objects and pairs were evaluated.
4. Review the closest-approach results table.
5. Search by object name or catalog ID.
6. Change the sorting order to inspect results.
7. Select Run screening to request a new screening response.

The current dashboard requests instantaneous screening: it compares calculated positions at one timestamp.

## 3. Understand the terms

- **TLE:** Two-Line Element data. Two lines of orbital information used to estimate a satellite's motion.
- **SGP4:** The mathematical model used to propagate satellite positions from TLE data.
- **Separation (km):** The calculated distance between two objects' positions, in kilometres.
- **Catalog ID:** An identifier used to distinguish an object.
- **UTC:** Coordinated Universal Time, a shared time standard.
- **Fresh TLE:** A TLE epoch within SKYTRACE's six-hour reporting threshold.
- **Stale TLE:** A TLE epoch older than that threshold. This is a warning to review the data, not proof that it is unusable.
- **Future epoch:** An epoch later than the screening reference time; it should be reviewed.
- **Duplicate state:** Two records produced matching numerical states. This is a data-quality flag, not a collision alert.

A file's download time and the epoch inside its TLE records are different. A recently downloaded file can contain older orbital data.

## 4. Understand the results

- **Objects loaded:** Objects included in the screening input.
- **Pairs evaluated:** Object pairs examined by the calculation.
- **Closest separation:** The smallest separation among the results returned. It does not automatically mean a collision will occur.
- **Screening time:** The time associated with the calculation.
- **Data quality flags:** Warnings that should be reviewed before interpreting the results.

## 5. Troubleshooting

### Screening could not be loaded / HTTP 503

1. Wait briefly and try again.
2. Check https://skytrace-api.onrender.com/health
3. If health is OK but screening fails, the data-refresh or screening path may still be unavailable.
4. Do not assume an old result is current when a new result cannot be loaded.

The free backend may sleep while idle, so its first request can take longer.

### Many records are stale

This means their TLE epochs are older than six hours. It is a data-quality warning, not evidence that a collision is happening.

### Two objects appear extremely close

Review the TLE ages, timestamps, and data-quality flags. Separation alone is not a collision prediction.

## 6. Important limitations

- Instantaneous screening compares positions at one time.
- Sampled-window calculations check discrete timestamps and can miss a closer approach between samples.
- TLE age alone does not measure orbital uncertainty.
- SKYTRACE does not calculate collision probability.
- SKYTRACE is not a validated operational collision-warning or collision-avoidance system.

Do not use SKYTRACE as the sole basis for real spacecraft operations or collision-avoidance decisions.

## Links

- [SKYTRACE dashboard](https://skytrace-gamma.vercel.app/)
- [Backend health](https://skytrace-api.onrender.com/health)
- [GitHub repository](https://github.com/HeamakeshBajina/skytrace)
- [Deployment documentation](../DEPLOYMENT.md)
