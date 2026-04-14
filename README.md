# 📰 Daily News Intelligence

AI-powered news aggregation platform that automatically collects, summarises, and ranks daily headlines from **BBC, Reuters, The Hindu, ESPN, Times of India, and Moneycontrol** — with AI-curated Top 5, trending analytics, and email digests.

---

## 🏗️ Project Structure

```
DailyNews/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Environment variables
│   ├── database.py          # MongoDB (Motor async)
│   ├── models/schemas.py    # Pydantic models
│   ├── routes/              # API route handlers
│   │   ├── news.py          # GET /news
│   │   ├── top5.py          # GET /top5
│   │   ├── trends.py        # GET /trends
│   │   ├── subscription.py  # POST /subscribe, DELETE /unsubscribe
│   │   └── search.py        # GET /search
│   ├── services/
│   │   ├── scraper.py       # RSS feed scraper
│   │   ├── ai_processor.py  # OpenAI GPT-4o-mini
│   │   ├── curator.py       # Top 5 AI curation
│   │   ├── trends_service.py# Trend analytics
│   │   └── email_service.py # SMTP email digest
│   └── scheduler/
│       └── jobs.py          # APScheduler daily pipeline
└── frontend/
    └── src/
        ├── pages/           # Dashboard, NewsFeed, Trends, Subscribe
        ├── components/      # NewsCard, Top5Card, Navbar, Charts...
        ├── services/api.js  # Axios wrapper
        └── hooks/useNews.js # Infinite scroll hook
```

---

## ⚡ Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- MongoDB running locally (`mongod`)

---

### Backend Setup

```bash
cd backend

# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env with your OpenAI key, SMTP credentials, etc.

# 4. Start the API server
uvicorn main:app --reload --port 8000
```

➡️ API docs available at: **http://localhost:8000/docs**

---

### Frontend Setup

```bash
cd frontend

# Install dependencies (already done if you ran npm install)
npm install

# Start dev server
npm run dev
```

➡️ Open: **http://localhost:5173**

---

## 🔑 Environment Variables (backend/.env)

| Variable | Description | Default |
|---|---|---|
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017/dailynews` |
| `OPENAI_API_KEY` | OpenAI API key (leave blank for mock mode) | — |
| `SMTP_HOST` | SMTP server | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USER` | Gmail address | — |
| `SMTP_PASS` | Gmail App Password | — |
| `FROM_EMAIL` | Sender name + email | — |
| `FRONTEND_URL` | Frontend URL for CORS | `http://localhost:5173` |
| `SCHEDULER_HOUR` | Pipeline run hour (IST) | `7` |
| `SCHEDULER_MINUTE` | Pipeline run minute | `0` |

> **Mock Mode**: If `OPENAI_API_KEY` is blank, the app runs without AI — raw headlines are shown instead of summaries.

---

## 🚀 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/news` | Paginated articles (`?category=sports&page=1&limit=20`) |
| `GET` | `/news/{id}` | Single article by ID |
| `GET` | `/top5` | Today's AI Top 5 stories |
| `GET` | `/trends` | Category counts + trending keywords |
| `GET` | `/trends/history` | 7-day trend history |
| `GET` | `/search?q=term` | Full-text article search |
| `POST` | `/subscribe` | Subscribe email `{ email, name }` |
| `DELETE` | `/unsubscribe?email=` | Unsubscribe email |
| `POST` | `/trigger-pipeline` | Manually run full pipeline |

---

## 🤖 Running the Pipeline Manually

Click **"Run Pipeline"** in the navbar, or call:

```bash
curl -X POST http://localhost:8000/trigger-pipeline
```

This chains: **Scrape → AI Process → Curate Top 5 → Trends → Email Digest**

---

## ⏰ Scheduler

The pipeline runs automatically at **7:00 AM IST** every day via APScheduler (runs inside the FastAPI process). Change the time with `SCHEDULER_HOUR` / `SCHEDULER_MINUTE` in `.env`.

---

## 📧 Gmail SMTP Setup

1. Go to Google Account → Security → **2-Step Verification** (enable it)
2. Go to **App Passwords** → Generate a new one for "Mail"
3. Use that 16-character password as `SMTP_PASS` in `.env`

---

## 🌐 Deployment

### Backend → Render
1. Push `backend/` to a GitHub repo
2. Create a **Web Service** on Render, set build command: `pip install -r requirements.txt`
3. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add all env vars in Render dashboard

### Frontend → Vercel
1. Push `frontend/` to GitHub
2. Import project in Vercel
3. Set env var: `VITE_API_URL=https://your-render-backend.onrender.com`
4. Deploy

### Database → MongoDB Atlas
1. Create a free cluster at [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Get connection string, set as `MONGODB_URI` in backend env vars

---

## 📡 News Sources

| Source | Category |
|---|---|
| BBC News | General |
| BBC World | World |
| BBC Sport | Sports |
| Reuters | General / World / Business |
| The Hindu | India / World / Business |
| ESPN | Sports |
| Times of India | India / Business / Sports |
| Moneycontrol | Business / Markets |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI |
| Database | MongoDB (Motor async driver) |
| Scraping | feedparser + requests + BeautifulSoup |
| AI | OpenAI GPT-4o-mini |
| Scheduler | APScheduler |
| Email | Python smtplib (SMTP) |
| Frontend | React + Vite + Tailwind CSS |
| Charts | Recharts |
| Icons | Lucide React |
