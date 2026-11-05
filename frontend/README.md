# TriAgent UI

React + Vite frontend for the three TriAgent services. One build is served by
all three FastAPI apps:

- **Mail** — support email agent (Part 1)
- **Lens** — scrape & summarize (Part 2)
- **Docs** — grounded document chat (Part 3)

```bash
npm install
npm run build      # writes frontend/dist, served by each FastAPI app
npm run dev        # proxies /api to part1 on :8000
```
