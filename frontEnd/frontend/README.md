# NBA Betting Markets Frontend

This is a Next.js frontend application for displaying NBA betting markets from the smart contracts backend.

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Backend API running (default at http://localhost:3002)

### Installation

1. Install dependencies:

```bash
npm install
# or
yarn install
```

2. Run the development server:

```bash
npm run dev
# or
yarn dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser to see the application.

## Features

- View all betting markets
- Display market details including:
  - Teams playing
  - Game time
  - Odds for each team
  - Market status (ready for betting, in progress, ended)
  - Game outcome (when available)

## Backend Connection

The application connects to the backend API (by default at `http://localhost:3002`) to fetch market data. Make sure the backend server is running before using this frontend.

To change the API URL, modify the `API_URL` constant in `app/page.tsx`.

## Project Structure

- `app/page.tsx` - Main page component that fetches and displays markets
- `app/layout.tsx` - Root layout with global styles and header
- `components/MarketsList.tsx` - Component to list all markets
- `components/MarketCard.tsx` - Component to display individual market details

## Future Enhancements

Future versions will add more functionality such as:
- Creating new markets
- Placing bets
- Updating odds
- Viewing transaction history

## Technology Stack

This project is built with:
- [Next.js](https://nextjs.org) - React framework for building web applications
- [TypeScript](https://www.typescriptlang.org/) - Type-safe JavaScript
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework
