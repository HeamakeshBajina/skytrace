# SKYTRACE Web Dashboard

The SKYTRACE web application provides a dashboard for exploratory satellite close-approach screening.

## Requirements

- Node.js and npm
- Python and the dependencies required by the SKYTRACE backend

## Installation

From the `web` directory, install the frontend dependencies:

```powershell
npm ci
```

## Development

Start the development server:

```powershell
npm run dev
```

Open the local URL printed by Next.js, usually `http://localhost:3000`.

## Quality checks

Run the frontend linter and production build:

```powershell
npm run lint
npm run build
```

## Application structure

- `src/app/page.tsx` - dashboard interface
- `src/app/layout.tsx` - application layout and metadata
- `src/app/api/screening/route.ts` - screening API route
- `public/` — static assets

Refer to the repository's root README and methodology documentation for backend setup and screening details.

## Scientific limitations

SKYTRACE is an exploratory screening tool, not an operational collision-warning system. A screened close approach does not establish that a collision will occur. Interpret results in accordance with the project's documented methodology and limitations.
