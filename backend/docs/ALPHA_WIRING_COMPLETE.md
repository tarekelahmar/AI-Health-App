# Alpha Wiring Sprint - Complete ✅

## What Was Built

### Frontend: 5 Critical Pages

1. **Login Page** (`/login`)
   - Simple user ID entry for alpha
   - Stores user_id in localStorage
   - Redirects to `/consent` after login

2. **Consent Page** (`/consent`)
   - Mandatory consent before accessing app
   - Explains what the app is/is not
   - Requires all checkboxes checked
   - Redirects to `/connect` after consent

3. **Provider Connect Page** (`/connect`)
   - Shows WHOOP as available
   - "Connect WHOOP" button
   - Redirects to WHOOP OAuth
   - After callback, redirects to `/insights`

4. **Insights Feed Page** (`/insights`) - **Core Page**
   - Home screen
   - Calls `/api/v1/insights/feed`
   - Shows "We don't have enough data yet" if empty
   - Has hidden "Run Loop" button for alpha (manual trigger)
   - Link to Narratives page

5. **Narratives Page** (`/narratives`)
   - Combined Narratives + Inbox with tabs
   - Calls `/api/v1/narratives/daily` and `/api/v1/inbox`
   - Plain rendering, no dramatization

### Backend: Manual Loop Trigger

- **Endpoint**: `POST /api/v1/insights/run`
- Already exists and works
- Called by the "Run Loop" button in Insights Feed page
- Runs the full insight generation loop for the current user

### Infrastructure

- **Unified API Client**: `frontend/src/api/client.ts`
  - Single source of truth for API base URL
  - Handles auth mode (public/private)
  - Adds user_id to requests in public mode
  - Handles 401 errors

- **Auth Context**: `frontend/src/contexts/AuthContext.tsx`
  - Simple context for user_id
  - Stores in localStorage
  - For alpha: uses user_id query param (AUTH_MODE=public)

- **Environment Config**: `frontend/.env`
  - `VITE_API_BASE_URL=http://localhost:8000`
  - `VITE_AUTH_MODE=public`

## Flow

1. User visits `/login` → enters user ID
2. Redirects to `/consent` → checks all boxes
3. Redirects to `/connect` → clicks "Connect WHOOP"
4. Redirects to WHOOP OAuth → user authorizes
5. WHOOP callback → redirects to `/insights`
6. User sees insights feed (or "not enough data" message)
7. User can click "Run Loop" button to manually trigger analysis
8. User can navigate to `/narratives` to see daily narrative and inbox

## Testing Checklist

Run through this exact flow:

1. ✅ Visit `http://localhost:5173` (or your alpha URL)
2. ✅ Create account (enter user ID)
3. ✅ Consent (check all boxes)
4. ✅ Connect WHOOP (OAuth flow)
5. ✅ Wait for data (or manually sync)
6. ✅ Read outputs (insights, narratives)

Ask yourself:
- Did I ever wonder "what is this doing?"
- Did anything feel implied but not stated?
- Did "no insight yet" feel honest or broken?

## Next Steps

1. **Set alpha URL**: Update `FRONTEND_URL` in backend `.env` if deploying
2. **Test the flow**: Run through the 5 pages as a human
3. **Document findings**: Write down what feels unclear or confusing
4. **Don't add features yet**: Focus on interpretation, not capability

## Files Created/Modified

### Frontend
- `frontend/.env` - Environment config
- `frontend/src/contexts/AuthContext.tsx` - Auth context
- `frontend/src/api/client.ts` - Unified API client
- `frontend/src/pages/LoginPage.tsx` - Login page
- `frontend/src/pages/ConsentPage.tsx` - Consent page
- `frontend/src/pages/ConnectPage.tsx` - Provider connect page
- `frontend/src/pages/InsightsFeedPage.tsx` - Core insights page
- `frontend/src/pages/NarrativesPage.tsx` - Narratives + Inbox
- `frontend/src/pages/OAuthCallback.tsx` - OAuth callback handler
- `frontend/src/main.tsx` - Updated routing
- `frontend/src/api/*.ts` - Updated to use unified client

### Backend
- `backend/app/api/v1/providers_whoop.py` - Updated callback to redirect to frontend

## Notes

- All API calls now use the unified `apiClient` from `frontend/src/api/client.ts`
- The "Run Loop" button is intentionally hidden/small for alpha - it's an admin tool
- OAuth callback redirects to `/insights` after successful WHOOP connection
- No user_id is exposed client-side except in localStorage (alpha only)

