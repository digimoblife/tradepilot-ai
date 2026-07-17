# TradePilot AI — Frontend

Next.js frontend for the TradePilot AI trading analysis workspace.

## Prerequisites

- Node.js LTS (v20+)
- npm

## Project Structure

```
frontend/
├── package.json
├── next.config.ts
├── tsconfig.json
├── eslint.config.mjs
├── src/
│   ├── app/
│   │   ├── globals.css     — Tailwind CSS entry
│   │   ├── layout.tsx      — Root App Router layout
│   │   └── page.tsx        — Foundation homepage
│   └── lib/
│       └── env.ts          — Public environment configuration
└── public/
```

## Setup

```bash
cd frontend
npm install
```

## Commands

```bash
# Development server
npm run dev

# Lint
npm run lint

# Type check
npm run typecheck

# Production build
npm run build

# Production start
npm run start
```

## Current Scope

This task (TP-0004) configures only the frontend foundation:

- Next.js with TypeScript, App Router, and Tailwind CSS
- Root layout with Indonesian language declaration
- Foundation homepage with Indonesian copy
- Public API base URL configuration
- Linting and type checking tooling
- Production build pipeline

## Deferred Functionality

The following are **not yet implemented**:

- Authentication and login page
- Trade session creation and listing
- Session detail pages with evidence, analysis, and position
- Evidence upload UI
- AI analysis rendering
- Lifecycle action controls (open, close, partial exit, etc.)
- API client and integration
- Canonical state display
- Dashboard navigation and sidebar
- Responsive production layout
- Docker configuration
