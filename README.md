# InvenTree Part Importer Web App

A Django REST API paired with a React SPA that lets you scan Mouser or Digi-Key labels and create matching parts inside
https://inventree.itrocas.com with only a few clicks. The backend normalizes supplier data and talks to InvenTree, while the
frontend focuses on a single streamlined import screen.

## Project structure

```
.
├── backend/        # Django project exposing /api/search/* and /api/import endpoints
├── frontend/       # React + Vite single-page app with barcode scanner UI
├── deploy/         # nginx reverse proxy used by the production image
├── docker-compose.yml
└── .env.example
```

## Backend responsibilities

- `/api/search/mouser/` and `/api/search/digikey/` accept a `part_number` and fetch data from the supplier APIs.
- `/api/import/` receives the edited payload and creates the part (plus supplier links/parameters) through the InvenTree REST
  API.
- Environment-driven configuration keeps secrets outside of the repo and mirrors the deployment in the existing Docker host.

Key modules live under `backend/api/services/`:

| File | Purpose |
| --- | --- |
| `mouser.py` | Calls Mouser Search by Part Number and normalizes fields |
| `digikey.py` | Handles Digi-Key OAuth2 client-credentials and ProductDetails fetch |
| `inventree.py` | Posts the finalized data into InvenTree, including supplier & parameter records |

## Frontend responsibilities

The SPA lives in `frontend/src` and renders a single workflow:

1. Choose a supplier (Mouser or Digi-Key) or scan a barcode using the built-in camera dialog powered by `@zxing/browser`.
2. Review/edit the fetched data – key info, category, parameters, pricing, and datasheet.
3. Submit to `/api/import/` to create the part in InvenTree.

Everything is optimized for keyboard/HID scanners: the input stays focused and pressing Enter triggers the lookup.

## Running locally

1. Copy the sample environment file and fill in your production secrets:

   ```bash
   cp .env.example .env
   # edit .env with Mouser API key, Digi-Key client credentials, and the InvenTree token
   ```

2. Install backend dependencies and run the Django checks:

   ```bash
   pip install -r backend/requirements.txt
   python backend/manage.py migrate  # creates the local sqlite DB used for admin/auth
   python backend/manage.py runserver
   ```

3. In another terminal install frontend deps and start Vite:

   ```bash
   npm install --prefix frontend
   npm run dev --prefix frontend
   ```

   The Vite dev server proxies `/api/*` to `localhost:8000`, so the SPA can talk to your local backend immediately.

4. For a Docker workflow (matching production) run:

   ```bash
   docker compose up --build
   ```

   This launches `backend` (Gunicorn) and `frontend` (nginx serving the built SPA) containers. nginx proxies `/api/` to the
   backend, mirroring the `import.inventree.itrocas.com` deployment model.

   Both the Django API and the nginx front-end ports are configurable so they do not clash with other services on your host.
   Override them in `.env` before running compose:

   ```bash
   BACKEND_HOST_PORT=8000
   FRONTEND_HOST_PORT=6000
   NGINX_PORT=6000
   ```

   With the example above, nginx listens on `:6000` inside the container and Docker publishes it at the same port on the host.

## Required environment variables

| Variable | Description |
| --- | --- |
| `DJANGO_SECRET_KEY` | Secret used by Django (generate a long random string) |
| `MOUSER_API_KEY` | Mouser Search API key |
| `DIGIKEY_CLIENT_ID` / `DIGIKEY_CLIENT_SECRET` | OAuth credentials for Digi-Key Product Information API v4 |
| `INVENTREE_BASE_URL` | Base URL for your InvenTree instance (e.g. `https://inventree.itrocas.com`) |
| `INVENTREE_TOKEN` | API token for the import bot user |
| `INVENTREE_MOUSER_COMPANY_ID` / `INVENTREE_DIGIKEY_COMPANY_ID` | Company IDs in InvenTree used when creating supplier parts |
| `DEFAULT_COUNTRY` / `DEFAULT_CURRENCY` | Locale hints used when normalizing price data (defaults: `PT` and `EUR`) |

## Notes & future enhancements

- Category lookup currently expects a `category_id` from the frontend. The backend already exposes a hook to auto-create or map
  categories in future iterations.
- The Digi-Key and Mouser modules surface helpful Python exceptions when credentials are missing, making it easy to spot
  misconfiguration in container logs.
- Batch import, richer parameter templating, and attachment uploads will be layered on after the happy-path experience is
  polished.
