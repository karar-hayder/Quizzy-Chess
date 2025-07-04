# Quizzy Chess API Documentation

This document provides a comprehensive guide to the Quizzy Chess backend API. It's intended for frontend developers who need to interact with the server.

---

## Table of Contents

- [Quizzy Chess API Documentation](#quizzy-chess-api-documentation)
  - [Table of Contents](#table-of-contents)
  - [Base URL](#base-url)
  - [Authentication](#authentication)
  - [User Management API](#user-management-api)
    - [Register User](#register-user)
    - [Login / Obtain JWT](#login--obtain-jwt)
    - [Refresh JWT](#refresh-jwt)
    - [Get/Update User Profile](#getupdate-user-profile)
    - [Get Leaderboard](#get-leaderboard)
  - [Game Management API](#game-management-api)
    - [Create or Join Game](#create-or-join-game)
    - [Get Game Details](#get-game-details)
    - [Get Game Analysis](#get-game-analysis)
    - [Get a Quiz Question](#get-a-quiz-question)
    - [Submit a Quiz Answer](#submit-a-quiz-answer)
    - [Matchmaking Status](#matchmaking-status)
  - [WebSocket Events](#websocket-events)
    - [Client -\> Server Messages](#client---server-messages)
    - [Server -\> Client Messages](#server---client-messages)

---

## Base URL

All API endpoints are prefixed with `/api/`.

- **Local Development:** `http://127.0.0.1:8000/api/`

---

## Authentication

Most endpoints require authentication using JSON Web Tokens (JWT).

1. **Obtain Tokens:** Get an `access` and `refresh` token from the `/users/login/` endpoint.
2. **Send Token:** Include the `access` token in the `Authorization` header for all protected requests:
    `Authorization: Bearer <your_access_token>`
3. **Refresh Token:** When an `access` token expires, use the `/users/token/refresh/` endpoint with your `refresh` token to get a new `access` token.

---

## User Management API

Base Path: `/api/users/`

### Register User

- **Description:** Creates a new user account.
- **Endpoint:** `POST /api/users/register/`
- **Authentication:** None required.
- **Request Body:**

    ```json
    {
      "username": "newuser",
      "email": "user@example.com",
      "password": "strongpassword123"
    }
    ```

- **Success Response (201 CREATED):**

    ```json
    {
      "id": 2,
      "username": "newuser",
      "email": "user@example.com",
      "rating": 1200,
      "games_played": 0,
      "games_won": 0,
      "games_lost": 0,
      "games_drawn": 0,
      "quiz_correct": 0,
      "quiz_attempted": 0,
      "preferred_subject": ""
    }
    ```

### Login / Obtain JWT

- **Description:** Authenticates a user and returns JWT access and refresh tokens.
- **Endpoint:** `POST /api/users/login/`
- **Authentication:** None required.
- **Request Body:**

    ```json
    {
      "username": "newuser",
      "password": "strongpassword123"
    }
    ```

- **Success Response (200 OK):**

    ```json
    {
      "refresh": "eyJ...",
      "access": "eyJ..."
    }
    ```

### Refresh JWT

- **Description:** Provides a new access token if the refresh token is valid.
- **Endpoint:** `POST /api/users/token/refresh/`
- **Authentication:** None required.
- **Request Body:**

    ```json
    {
      "refresh": "eyJ..."
    }
    ```

- **Success Response (200 OK):**

    ```json
    {
      "access": "eyJ..."
    }
    ```

### Get/Update User Profile

- **Description:** Retrieves or updates the profile of the currently authenticated user.
- **Endpoint:** `GET /api/users/profile/` or `PUT/PATCH /api/users/profile/`
- **Authentication:** Required (Bearer Token).
- **GET Success Response (200 OK):**

    ```json
    {
      "id": 1,
      "username": "currentuser",
      "email": "current@example.com",
      "rating": 1250,
      // ... other user fields
    }
    ```

- **PUT/PATCH Request Body (Example):**

    ```json
    {
      "email": "new-email@example.com",
      "preferred_subject": "History"
    }
    ```

### Get Leaderboard

- **Description:** Retrieves the top 20 users, ordered by rating.
- **Endpoint:** `GET /api/users/leaderboard/`
- **Authentication:** None required.
- **Success Response (200 OK):**

    ```json
    [
      {
        "id": 5,
        "username": "player1",
        "rating": 1500
        // ... other user fields
      },
      {
        "id": 8,
        "username": "player2",
        "rating": 1480
        // ... other user fields
      }
    ]
    ```

---

## Game Management API

Base Path: `/api/core/`

### Create or Join Game

- **Description:** Creates a new game or joins an existing one. To create a game, send a POST request with no `code`. To join a game, send the `code` of the game you wish to join.
- **Endpoint:** `POST /api/core/game/`
- **Authentication:** Required (Bearer Token).
- **Request Body (Create Game):**

    ```json
    {
      "subjects": ["Math", "Science"],
      "is_vs_ai": false,           // Optional, default false
      "ai_difficulty": "easy"    // Optional, default "easy" (if is_vs_ai is true)
    }
    ```

- **Request Body (Join Game):**

    ```json
    {
      "code": "A5T7B"
    }
    ```

- **Success Response (200 OK / 201 CREATED):** The response includes the full game state and a `spectator` flag.

    ```json
    {
        "spectator": false,
        "id": 1,
        "code": "A5T7B",
        "player_white": { ... },
        "player_black": { ... },
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "status": "active", // "waiting", "active", "finished"
        "subjects": ["Math", "Science"],
        "winner": null,
        "is_vs_ai": false,
        "ai_difficulty": "easy",
        "created_at": "2023-10-27T10:00:00Z"
    }
    ```

### Get Game Details

- **Description:** Retrieves the current state of a specific game.
- **Endpoint:** `GET /api/core/game/<game_code>/`
- **Authentication:** Required (Bearer Token).
- **URL Parameters:**
  - `game_code` (string): The unique code of the game.
- **Success Response (200 OK):**

    ```json
    {
      "id": 1,
      "code": "A5T7B",
      // ... all other game fields
    }
    ```

### Get Game Analysis

- **Description:** Retrieves analysis for a completed game (if available).
- **Endpoint:** `GET /api/core/game/<game_code>/analysis/`
- **Authentication:** Required (Bearer Token).
- **Success Response (200 OK):**

    ```json
    {
      "overall": { ... },
      "per_move": [ ... ]
    }
    ```

- **202 Accepted:** If analysis is not yet available.

    ```json
    { "detail": "Analysis not available yet." }
    ```

### Get a Quiz Question

- **Description:** Fetches a random quiz question for a given subject.
- **Endpoint:** `GET /api/core/quiz/`
- **Authentication:** Required (Bearer Token).
- **Query Parameters:**
  - `subject` (string, optional, default: "Math"): The subject for the quiz question.
- **Success Response (200 OK):**

    ```json
    {
        "id": 5,
        "subject": "Math",
        "question_text": "What is 2 + 2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "correct_option": "B"
    }
    ```

### Submit a Quiz Answer

- **Description:** Submits a user's answer to a quiz question associated with a specific move. This is only used when a move has `quiz_required: true`.
- **Endpoint:** `POST /api/core/move/<move_id>/quiz/`
- **Authentication:** Required (Bearer Token).
- **URL Parameters:**
  - `move_id` (integer): The ID of the move that triggered the quiz.
- **Request Body:**

    ```json
    {
      "question_id": 5,
      "answer": "B" // The chosen option
    }
    ```

- **Success Response (200 OK):**

    ```json
    {
      "correct": true
    }
    ```

    If `correct` is `true`, the frontend should then expect a WebSocket message updating the game's FEN. If `false`, the move is voided.

### Matchmaking Status

- **Description:** Returns the current matchmaking queue status.
- **Endpoint:** `GET /api/core/matchmaking/status/`
- **Authentication:** Required (Bearer Token).
- **Success Response (200 OK):**

    ```json
    {
      "queue_length": 5,
      "active_searches": 3
    }
    ```

---

## WebSocket Events

- **Connection URL:** `/ws/game/<game_code>/`
- **Description:** Once connected, the client and server communicate through a series of typed messages. The client sends actions like `move` or `quiz_answer`, and the server broadcasts game state changes and events to all clients in the room.

### Client -> Server Messages

- **Make a Move:**

    ```json
    {
      "type": "move",
      "payload": {
        "from_square": "e2",
        "to_square": "e4",
        "piece": "P",
        "captured_piece": null,
        "move_number": 1
      }
    }
    ```

- **Answer a Quiz:**

    ```json
    {
      "type": "quiz_answer",
      "payload": {
        "answer": "A",
        "move_number": 5
      }
    }
    ```

- **Ping:** A simple keep-alive message.

    ```json
    {
      "type": "ping"
    }
    ```

### Server -> Client Messages

- **Move Processed:** Sent when a legal move (that doesn't require a quiz) is successfully made.

    ```json
    {
      "message": "move",
      "payload": {
        "from_square": "e2",
        "to_square": "e4",
        "piece": "P",
        "move_number": 1,
        "fen_after": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        "captured_piece": null,
        "uuid": "..."
      }
    }
    ```

- **Quiz Required:** Sent when a move triggers a quiz.

    ```json
    {
      "message": "quiz_required",
      "payload": {
          "subject": "Math",
          "question": "Dummy question for Math?",
          "choices": ["A", "B", "C", "D"],
          "correct": "A",
          "explanation": "This is a dummy explanation."
      }
    }
    ```

- **Invalid Move:** Sent to a client that attempts an illegal move.

    ```json
    {
      "message": "move_invalid",
      "payload": {
        "reason": "Illegal move"
      }
    }
    ```

- **Quiz Failed:** Sent to a client that answers a quiz incorrectly.

    ```json
    {
      "message": "quiz_failed",
      "payload": {
        "reason": "Quiz answer incorrect. Try another move."
      }
    }
    ```

- **Permission Denied:** Sent if a spectator tries to perform a player action.

    ```json
    {
      "message": "permission_denied",
      "payload": {
        "reason": "Spectators cannot make moves or answer quizzes."
      }
    }
    ```

- **Pong:** The server's response to a `ping`.

    ```json
    {
      "message": "pong"
    }
    ```
