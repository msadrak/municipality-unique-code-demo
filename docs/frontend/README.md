# Frontend Documentation

## Overview

The Municipality Portal frontend is a React/TypeScript application built with Vite.
Previously named `figma_export`, now renamed to `frontend`.

## Directory Structure

```
frontend/
├── src/
│   ├── App.tsx              # Main app with routing
│   ├── main.tsx             # Entry point
│   ├── index.css            # Global styles
│   ├── components/          # React components
│   │   ├── Login.tsx        # Login page
│   │   ├── UserPortal.tsx   # Main user portal
│   │   ├── AdminDashboard.tsx # Admin panel
│   │   ├── TransactionWizard.tsx # Transaction creation
│   │   ├── MyTransactionsList.tsx # User transactions
│   │   ├── wizard-steps/    # Wizard step components
│   │   ├── forms/           # Form components
│   │   └── ui/              # Reusable UI components
│   ├── services/            # API services
│   │   ├── api.ts           # Base API client
│   │   ├── auth.ts          # Auth service
│   │   ├── admin.ts         # Admin service
│   │   └── adapters.ts      # Data adapters
│   └── types/               # TypeScript types
├── package.json
└── vite.config.ts           # Vite config with proxy
```

## Running Development Server

```bash
cd frontend
npm install
npm run dev
```

App available at: `http://localhost:5173`

## Building for Production

```bash
npm run build
```

Output in `frontend/build/` directory.

## Key Components

### TransactionWizard
Multi-step wizard for creating transactions:
1. Activity Selection
2. Allowed Activities
3. Budget Selection
4. Financial Event & Beneficiary
5. Contract Details
6. Review & Submit

### AdminDashboard
4-level approval workflow interface with:
- Transaction filtering by status
- Approve/Reject actions
- Workflow history

### UserPortal
Main dashboard showing:
- Activity grid
- My Transactions list
- Quick actions
