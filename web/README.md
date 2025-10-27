Esports frontend demo

This is a minimal React + Vite frontend that connects to the demo backend in this repository.

How to run (locally):

1. Start the Python backend (FastAPI) in the repository root:

```powershell
pip install -r requirements.txt
uvicorn src.fastapi_app:app --reload
```

2. In a separate shell, start the frontend:

```powershell
cd web
npm install
npm run dev
```

3. Open the dev URL shown by Vite (usually http://127.0.0.1:5173) and click a match to open the match page. The page will try to connect to `ws://127.0.0.1:8000/ws/matches/{id}` for live updates.

Notes:
- The frontend expects the backend at 127.0.0.1:8000. If you run the backend on a different host/port, update the fetch / websocket URLs in `web/src/App.jsx` and `web/src/components/MatchPage.jsx`.
- This is intentionally minimal and meant as a starting point. Next steps: proxy setup, CORS, prettier UI, and a seeded demo producer to push updates into the backend store.
