# Quizzy Chess

## 🚀 About the Project

Quizzy Chess is a fullstack, real-time multiplayer chess platform with educational quizzes integrated into gameplay. Initially developed at the DevSprint Hackathon (Baghdad, Iraq, June 2025) where I served as the backend developer, I later rebuilt the entire frontend from scratch, making this a complete fullstack project under my ownership. This project represents my most comprehensive fullstack build to date, applying and strengthening my skills in Redis, Docker, WebSockets, fullstack development, Celery tasks, AI, MVP building, testing, and more.

When a player attempts to capture a high-value piece (queen, rook, bishop), they must correctly answer a subject-based quiz to complete the move. This unique mechanic blends cognitive engagement, subject learning, and strategic thinking through gamified education.

---

## 🏆 Hackathon & Personal Journey

- **Event:** DevSprint Hackathon, Baghdad, Iraq, June 2025
- **Role:** Backend developer (hackathon); fullstack developer (this project)
- **Highlights:**
  - During the hackathon, I was responsible for the backend architecture, real-time logic, and core game/quiz logic.
  - After the event, I rebuilt the frontend from scratch, integrating it tightly with the backend and adding modern UI/UX, new features, and improved architecture.
  - Applied and strengthened my skills in:
    - Redis (caching, pub/sub, broker)
    - Docker (multi-service orchestration)
    - Django Channels & WebSockets (real-time)
    - Celery (background tasks)
    - AI/LLM integration (quiz generation)
    - MVP design, testing, and rapid iteration
    - Fullstack architecture (Next.js, Django, PostgreSQL, Redis)
    - Production-ready DevOps (Docker Compose, Nginx, Vercel/Render)
  - Built a robust, demo-ready MVP with modern UI/UX and real-time features

---

## 🎯 Features

- Real-time multiplayer chess (1v1)
- Spectator mode
- JWT authentication & profiles
- Elo-based matchmaking
- Interactive chessboard (React + chess.js)
- Subject-based quizzes on key captures
- Stockfish-powered game analysis
- Live leaderboard & player stats
- Responsive, mobile-friendly UI
- API & WebSocket testing tools

---

## 🏗️ Architecture & Technologies

### Frontend

- **Framework:** Next.js (React 19)
- **Styling:** Tailwind CSS
- **State:** React Context
- **Chess Logic:** chess.js
- **API:** Axios (REST), native WebSocket
- **Key Components:** Chessboard, QuizModal, MatchmakingModal, AuthForm, Profile, Leaderboard, Analysis

### Backend

- **Framework:** Django 4.2
- **Real-time:** Django Channels, Daphne, Redis
- **Database:** PostgreSQL (Docker)
- **Task Queue:** Celery (Redis broker)
- **Chess Engine:** Stockfish (python-chess)
- **Quiz Generation:** AI-powered (LLM-based, with fallback to DB)
- **Authentication:** JWT (djangorestframework-simplejwt)
- **APIs:** REST (DRF), WebSocket

### DevOps

- **Dockerized:** Backend, Celery, Redis, Postgres, Nginx
- **Deployment:** Vercel (frontend), Railway/Render (backend)
- **Logging:** Centralized, error/info logs for all services

---

## 📋 Pages & Modules Overview

- **Landing Page:** Welcome, login/register, quick start, create/join game
- **Game Room:** Real-time chessboard, player info, move list, chat, resign/draw, quiz modal
- **Quiz Modal:** Pops up on key captures, subject-based, multiple-choice, timer, feedback
- **Matchmaking Modal:** Search progress, queue status, auto-redirect
- **Profile Page:** User stats, preferred subject, game history, analysis links
- **Leaderboard:** Top players, ratings, win rates, quiz accuracy
- **Analysis Page:** Large board, move navigation, per-move analysis, stats
- **Test Page:** API/WebSocket connectivity checks

---

## 🧩 Backend Modules

- `core/models.py`: Game, Move, QuizQuestion, GameAnalysis models
- `core/tasks.py`: Celery tasks for quiz generation, analysis, matchmaking cleanup
- `core/consumers.py`: WebSocket consumers for game and matchmaking
- `core/matchmaking.py`: Elo-based matchmaking logic
- `core/views.py`: REST API endpoints
- `users/models.py`: CustomUser with rating, stats, and profile fields

---

## 📦 Dependencies

### Backend

- Django, Django Channels, djangorestframework, Celery, Redis, Daphne, python-chess, Stockfish, JWT, etc.

### Frontend

- Next.js, React, Tailwind CSS, chess.js, axios, react-hook-form, zod, etc.

---

## 🏆 Achievements

- Real-time multiplayer chess with quiz integration
- Robust authentication and user management
- Elo-based matchmaking and leaderboard
- Game analysis with Stockfish
- Modern, responsive UI/UX
- Dockerized, production-ready stack
- AI-powered quiz generation with error handling and fallback

---

## 🟢 What's Working Well

- Smooth, real-time gameplay and quiz experience
- All major MVP features implemented and demo-ready
- Robust error handling for AI and WebSocket events
- Clean, modern UI with good accessibility and mobile support

---

## 🟡 Areas for Future Improvement

- More quiz subjects and question variety
- Enhanced spectator mode and chat
- Game replay and analytics
- Daily missions, tournaments, and friend invites
- More advanced anti-cheat and moderation tools

---

## 🧭 Summary

Quizzy Chess is a fully functional, modern, and educational chess platform that blends real-time play with subject-based quizzes. The project is demo-ready, robust, and extensible for future features.

---

## 🚦 Quickstart (Development)

### Prerequisites

- Docker & Docker Compose
- Node.js (for local frontend dev)

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd QuizzyChess
```

### 2. Start the stack (all services)

```bash
docker-compose up --build
```

- Backend: <http://localhost:8000>
- Frontend: <http://localhost:3000>

### 3. (Optional) Local frontend dev

```bash
cd frontend
npm install
npm run dev
```

---

## 📖 API & Docs

- See [`API-DOCS.md`](docs/API-DOCS.md) for full backend API documentation.
- See [`Project-Mission.md`](docs/Project-Mission.md) for vision, features, and architecture.

---

## 🤝 Contributing

Pull requests and issues are welcome! For major changes, please open an issue first to discuss what you would like to change.

---

## 📝 License

- This project is for educational and demo purposes (see Stockfish license for engine details).

---

## 🙏 Acknowledgements

- Stockfish (chess engine)
- DevSprint Hackathon organizers and mentors
- Open source community
