## Frontend architecture

### Tech stack

- **React 18/19** with functional components and hooks.
- **Vite** dev server & build tool.
- **Context**-based auth state.
- **Custom API client** (`frontend/src/api/client.js`) to centralize HTTP logic.

The frontend is intentionally kept small and focused on the user flows required for the assessment: authentication, creator discovery & tracking, campaign management, and analytics/leaderboards.

### High-level structure

- `frontend/src/App.jsx`
  - Root component that:
    - Sets up global layout (header, navigation, main content).
    - Wraps the app in `AuthProvider` so child components can access auth state.
    - Renders the main views:
      - Creator Dashboard / Leaderboard.
      - Channel Discovery.
      - Campaigns.
  - Also mounts Vercel Analytics / Speed Insights if deployed there.

- `frontend/src/context/AuthContext.jsx`
  - Owns authentication state (JWT access token + user info).
  - Responsibilities:
    - On initial load, reads the token from `localStorage` (via the API client).
    - Handles `signup`, `login`, and `logout` by calling backend `/api/auth/signup`, `/api/auth/login`, `/api/auth/me`.
    - Exposes `user`, `isAuthenticated`, and auth actions via React context.
    - Registers an `onUnauthorized` callback with the API client so a 401 response will clear state and prompt the user to sign in again.

- `frontend/src/api/client.js`
  - Single source of truth for talking to the backend.
  - Base URL:
    - Determined from `import.meta.env.VITE_API_URL` (without trailing slash), defaulting to `http://localhost:8000` for local dev.
  - Handles:
    - Attaching the `Authorization: Bearer <token>` header when a user is logged in.
    - Normalizing error handling:
      - Network failures → “Unable to connect to the server. Please check if the backend is running.”
      - 401 → invokes `_onUnauthorized` and throws a “Session expired…” error.
      - Non-JSON or error responses → throws meaningful messages based on the backend payload.
  - Exposes high-level API functions used throughout the app:
    - Analytics: `getSummary`, `getTopCreators`, `getTopContent`.
    - Creators: `getCreators`, `getQuota`, `getLastRun`, `getRun`.
    - Ingestion: `triggerSync`, `getChannels`, `resolveChannel`, `searchChannels`, `getCategories`, `getTrending`, `trackChannel`, `untrackChannels`.
    - Campaigns: `getCampaigns`, `createCampaign`, `getCampaign`, `updateCampaign`, `deleteCampaign`, `addCreatorToCampaign`, `removeCreatorFromCampaign`.
    - Admin: `resetDatabase`.

- `frontend/src/components/CreatorLeaderboard.jsx`
  - Main dashboard view focused on **creator-level performance**.
  - Responsibilities:
    - Fetches top creators and associated metrics via the analytics endpoints.
    - Supports filters like time window (e.g. last N days) and sorting by key metrics (views, engagement).
    - Displays:
      - Key KPIs at the top (e.g. total creators, average engagement).
      - A table or list view with creators and their metrics.
    - Allows untracking creators:
      - Calls `api.untrackChannels()` and then shows the backend’s message (including how many campaigns they were removed from).

- `frontend/src/components/ChannelDiscovery.jsx`
  - Focused on **discovering and tracking new creators**.
  - Responsibilities:
    - Provides a search box to:
      - Resolve a handle/URL/keyword to a specific channel (`resolveChannel`).
      - Or search by keyword (`searchChannels`).
    - Uses quota endpoints to show the user when YouTube API quota is being consumed / is low.
    - Allows the user to start tracking a channel (via `trackChannel`), then updates the UI to show it as tracked.
    - When paired with the dashboard, this gives a full “discover → track → analyze” loop.

- `frontend/src/components/Campaign*` (if present)
  - Components around the campaigns feature:
    - Listing campaigns, viewing a single campaign’s members, and adding/removing creators.
  - They call:
    - `api.getCampaigns`, `api.createCampaign`, `api.getCampaign`, `api.addCreatorToCampaign`, `api.removeCreatorFromCampaign`, `api.deleteCampaign`.

### State and data flow

1. **Authentication**
   - `AuthProvider` wraps `App`.
   - Auth state is driven exclusively through the **backend** (no mocked client-side auth):
     - On signup/login:
       - Frontend sends credentials to `/api/auth/signup` or `/api/auth/login`.
       - Receives a JWT token, which is stored in memory and in `localStorage`.
     - On page refresh:
       - The token is read from `localStorage` and used to call `/api/auth/me` to rebuild `user` state.

2. **API usage**
   - All components use the exported `api` object from `client.js`.
   - This ensures:
     - Consistent base URL handling.
     - Consistent error messages.
     - Centralized authorization header management.

3. **Rendering flow**
   - High-level layout (header/nav) and route-level views (dashboard, discovery, campaigns) live in `App.jsx`.
   - Each feature component:
     - Fetches its own data in a `useEffect` hook or in response to user actions.
     - Maintains local UI state (filters, loading/error states) with React hooks.

### Adding new views or endpoints

To add a new feature or view:

1. **Add an API helper**
   - Extend `api` in `client.js` with a new function for the backend route.
   - Keep this thin (URL + method + JSON body); reuse the shared `request()` helper.

2. **Create a component or route in `App.jsx`**
   - Add a new view component under `frontend/src/components/`.
   - Wire it into `App.jsx` either as:
     - A conditional view (tab / section), or
     - A route if you introduce React Router later.

3. **Use context where needed**
   - If the new feature needs auth details, consume `AuthContext` (e.g. to show current email or enforce auth).

This setup keeps frontend logic small, explicit, and easy to follow for reviewers and future contributors.

