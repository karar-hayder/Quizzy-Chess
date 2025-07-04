# 📌 Project Title

## Quizzy Chess: Think Before You Take

---

## 🎯 Project Mission

Quizzy Chess is a full-stack, real-time multiplayer chess platform that integrates educational quizzes into gameplay. When a player attempts to capture a high-value piece (queen, rook, bishop), they must correctly answer a subject-based question to complete the move. The project aims to foster cognitive engagement, subject learning, and strategic thinking through gamified education.

---

## 🚩 Current Status (as of June 2025)

### ✅ Core Features Implemented

- **Real-time multiplayer chess (1v1):**  
  - Players can create or join games via unique codes.
  - Moves are synchronized live using WebSockets (Django Channels).
  - Spectator mode is supported.

- **Authentication:**  
  - JWT-based login, registration, and profile management.
  - User stats, preferred subject, and game history are tracked.

- **Matchmaking:**  
  - Elo-based matchmaking system with dynamic tolerance and wait-time bonus.
  - Real-time status updates and queue management via WebSocket.

- **Chess Gameplay:**  
  - Interactive chessboard (React + chess.js) with move validation.
  - Real-time move updates, resign/draw offers, and player info panels.

- **Quiz Integration:**  
  - Capture of valuable pieces triggers a quiz modal.
  - Quizzes are subject-based (Math, Science, Sports) and fetched from backend (LLM or DB).
  - Correct answers allow the move; incorrect answers block or void the move.

- **Game Analysis:**  
  - After each game, a detailed analysis is generated (accuracy, blunders, best moves, per-move breakdown).
  - Analysis is displayed in a dedicated page with a large board, move list, and stats.

- **Leaderboard:**  
  - Live leaderboard ranks players by Elo rating.
  - Displays player stats, win rate, quiz accuracy, and preferred subject.

- **Profile Page:**  
  - Shows user stats, game history, quiz accuracy, and links to analysis for each game.

- **UI/UX:**  
  - Modern, responsive design using Tailwind CSS.
  - All modals, tables, and pages are mobile-friendly and visually polished.

- **Testing & Demo:**  
  - Dedicated test page for API connectivity.
  - Demo HTML for quiz modal experience.

---

## 🏗️ Architecture & Technologies Used

### **Frontend**

- **Framework:** Next.js (React 19)
- **Styling:** Tailwind CSS (CDN and PostCSS)
- **State Management:** React Context for user/auth
- **Chess Logic:** chess.js (with @types)
- **API:** Axios for REST, native WebSocket for real-time
- **Components:**  
  - Chessboard (custom, using chess.js)
  - QuizModal (multiple-choice, timer, subject)
  - MatchmakingModal (real-time status, queue)
  - AuthForm (login/register)
  - Profile, Leaderboard, Analysis, GameRoom pages

### **Backend**

- **Framework:** Django 4.2
- **Real-time:** Django Channels 4.2, Daphne, Redis (as broker and cache)
- **Database:** PostgreSQL (via Docker)
- **Task Queue:** Celery 5.4 (with Redis)
- **Chess Engine:** Stockfish (for analysis, via python-chess)
- **Quiz Generation:**  
  - LLM-based (with robust JSON extraction/repair)
  - Fallback to DB-stored questions (Django model)
- **Authentication:** JWT (djangorestframework-simplejwt)
- **APIs:**  
  - REST (DRF) for user, game, quiz, leaderboard
  - WebSocket for game and matchmaking events

### **DevOps**

- **Dockerized:** Backend, Celery, Redis, Postgres, Nginx
- **Deployment:** Ready for Vercel (frontend) and Railway/Render (backend)
- **Logging:** Centralized, with error and info logs for all services

---

## 📋 Features & Pages Overview

- **Landing Page:**  
  - Welcome, login/register, quick start, and game creation/joining.

- **Game Room:**  
  - Real-time chessboard, player info, move list, chat, resign/draw, quiz modal.

- **Quiz Modal:**  
  - Pops up on key captures, subject-based, multiple-choice, timer, feedback.

- **Matchmaking Modal:**  
  - Shows search progress, queue status, and redirects to game on match.

- **Profile Page:**  
  - User stats, preferred subject, game history, per-game analysis links.

- **Leaderboard:**  
  - Top players, ratings, win rates, quiz accuracy.

- **Analysis Page:**  
  - Large board, move navigation, per-move analysis, overall stats.

- **Test Page:**  
  - For API and WebSocket connectivity checks.

---

## 🧩 Backend Modules

- **core/models.py:** Game, Move, QuizQuestion, GameAnalysis models.
- **core/tasks.py:** Celery tasks for quiz generation, analysis, matchmaking cleanup.
- **core/consumers.py:** WebSocket consumers for game and matchmaking.
- **core/matchmaking.py:** Elo-based matchmaking logic.
- **core/views.py:** REST API endpoints for all core features.
- **users/models.py:** CustomUser with rating, stats, and profile fields.

---

## 📦 Dependencies

### **Backend (requirements.txt)**

- Django, Django Channels, djangorestframework, Celery, Redis, Daphne, python-chess, Stockfish, JWT, and more.

### **Frontend (package.json)**

- Next.js, React, Tailwind CSS, chess.js, axios, react-hook-form, zod, and related types.

---

## 🏆 Achievements

- ✅ Real-time multiplayer chess with quiz integration
- ✅ Robust authentication and user management
- ✅ Elo-based matchmaking and leaderboard
- ✅ Game analysis with Stockfish and per-move breakdown
- ✅ Modern, responsive UI/UX
- ✅ Dockerized, production-ready stack
- ✅ LLM quiz generation with error handling and fallback

---

## 🟢 What's Working Well

- Smooth, real-time gameplay and quiz experience
- All major MVP features implemented and demo-ready
- Robust error handling for LLM and WebSocket events
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
