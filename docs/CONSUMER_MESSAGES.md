# WebSocket Consumer Message Documentation

## Overview

The `GameConsumer` class handles all WebSocket communication for the chess game. All messages follow a strict format with `type` and `payload` fields.

## Message Format

All messages follow this structure:

```json
{
  "type": "message_type",
  "payload": {
    // message-specific data
  }
}
```

## Message Types

### Player Management

#### `player_joined`

Sent when any player joins the game.

```json
{
  "type": "player_joined",
  "payload": {
    "user": "username",
    "player": "white" | "black"
  }
}
```

#### `spectator_joined`

Sent when a spectator joins the game.

```json
{
  "type": "spectator_joined",
  "payload": {
    "user": "username"
  }
}
```

#### `spectator_left`

Sent when a spectator leaves the game.

```json
{
  "type": "spectator_left",
  "payload": {
    "user": "username"
  }
}
```

#### `black_player_joined`

Sent when someone joins as the black player.

```json
{
  "type": "black_player_joined",
  "payload": {
    "user": "username",
    "game_code": "game_code"
  }
}
```

#### `joined_as_black`

Success message sent to the user who successfully joined as black.

```json
{
  "type": "joined_as_black",
  "payload": {
    "message": "Successfully joined as black player",
    "game_code": "game_code"
  }
}
```

### Game State

#### `game_update`

Sent when game state changes (player joins, moves made, etc.).

```json
{
  "type": "game_update",
  "payload": {
    "id": 123,
    "code": "game_code",
    "status": "active" | "ended",
    "result": "white_win_by_checkmate" | "black_win_by_checkmate" | "draw" | null,
    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "player_white": {
      "id": 1,
      "username": "player1",
      "rating": 1200
    },
    "player_black": {
      "id": 2,
      "username": "player2",
      "rating": 1200
    },
    "subject": "math",
    "is_vs_ai": false,
    "ai_difficulty": "easy" | "medium" | "hard",
    "score": 0.5,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

### Game Moves

#### `move`

Sent when a move is made.

```json
{
  "type": "move",
  "payload": {
    "from_square": "e2",
    "to_square": "e4",
    "piece": "p",
    "move_number": 1,
    "fen_after": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
    "captured_piece": null,
    "uuid": "move-uuid",
    "score": 0.2
  }
}
```

### Quiz System

#### `quiz_required`

Sent when a player attempts to capture a valuable piece (queen, rook, bishop).

```json
{
  "type": "quiz_required",
  "payload": {
    "question": "What is 2 + 2?",
    "choices": ["A: 3", "B: 4", "C: 5", "D: 6"],
    "move_number": 5,
    "subject": "math"
  }
}
```

#### `quiz_failed`

Sent when a quiz answer is incorrect or times out.

```json
{
  "type": "quiz_failed",
  "payload": {
    "reason": "Quiz answer incorrect. Try another move."
  }
}
```

### Game Actions

#### `draw_offer`

Sent when a player offers a draw.

```json
{
  "type": "draw_offer",
  "payload": {
    "from": "white" | "black"
  }
}
```

#### `game_over`

Sent when the game ends (checkmate, draw, resignation).

```json
{
  "type": "game_over",
  "payload": {
    "reason": "checkmate" | "draw" | "resignation" | "draw_agreed",
    "winner": "white" | "black" | null,
    "elo_change": {
      "white": {"old": 1200, "new": 1216},
      "black": {"old": 1200, "new": 1184}
    }
  }
}
```

### Error Messages

#### `error`

Sent when an error occurs.

```json
{
  "type": "error",
  "payload": {
    "reason": "Error description"
  }
}
```

#### `permission_denied`

Sent when a user tries to perform an action they're not allowed to.

```json
{
  "type": "permission_denied",
  "payload": {
    "reason": "Only players can make moves."
  }
}
```

#### `move_invalid`

Sent when an invalid move is attempted.

```json
{
  "type": "move_invalid",
  "payload": {
    "reason": "Illegal move" | "It's not your turn."
  }
}
```

### System Messages

#### `pong`

Response to ping messages.

```json
{
  "type": "pong",
  "payload": {}
}
```

## Frontend Handling

The frontend (`gameCode.vue`) should handle all these message types in the WebSocket `onmessage` handler:

```javascript
ws.value.onmessage = event => {
  try {
    const data = JSON.parse(event.data)
    console.log('WebSocket message received:', data)

    // Handle different message types
    switch (data.type) {
      case 'player_joined':
        handlePlayerJoined(data.payload)
        break
      case 'spectator_joined':
        handleSpectatorJoined(data.payload)
        break
      case 'spectator_left':
        handleSpectatorLeft(data.payload)
        break
      case 'black_player_joined':
        handleBlackPlayerJoined(data.payload)
        break
      case 'joined_as_black':
        handleJoinedAsBlack(data.payload)
        break
      case 'game_update':
        handleGameUpdate(data.payload)
        break
      case 'move':
        handleMove(data.payload)
        break
      case 'quiz_required':
        handleQuizRequired(data.payload)
        break
      case 'quiz_failed':
        handleQuizFailed(data.payload)
        break
      case 'draw_offer':
        handleDrawOffer(data.payload)
        break
      case 'game_over':
        handleGameOver(data.payload)
        break
      case 'error':
        handleError(data.payload)
        break
      case 'permission_denied':
        handlePermissionDenied(data.payload)
        break
      case 'move_invalid':
        handleMoveInvalid(data.payload)
        break
      case 'pong':
        handlePong(data.payload)
        break
      default:
        console.warn('Unknown message type:', data.type)
    }
  } catch (err) {
    console.error('WebSocket message error:', err)
  }
}
```

## Implementation Notes

1. **Strict Format**: All messages must use the `type`/`payload` format for consistency
2. **Game Updates**: When a player joins as black, a `game_update` message is sent to all players with the latest game state
3. **Error Handling**: All errors are sent with descriptive reasons
4. **State Synchronization**: The frontend should update its local state based on `game_update` messages
5. **Quiz System**: Quiz questions are sent when valuable pieces are captured, and moves are only applied after correct answers

## Matchmaking WebSocket Messages

### Client → Server

- `find_game`: Start matchmaking
- `cancel_search`: Cancel matchmaking search
- `ping`: Keep-alive

### Server → Client

- `search_started`: `{ message, search_id }`
- `search_cancelled`: `{ message }`
- `game_found`: `{ game: { ...game fields... }, message }`
- `error`: `{ reason }`
- `pong`: `{}`

## Game WebSocket Messages

### Client → Server

- `move`: `{ from_square, to_square, piece, captured_piece, move_number }`
- `quiz_answer`: `{ answer, move_number }`
- `resign`: `{}`
- `draw_offer`: `{}`
- `draw_accept`: `{}`
- `ping`: `{}`

### Server → Client

- `move`: `{ from_square, to_square, piece, move_number, fen_after, captured_piece, uuid, score }`
- `quiz_required`: `{ question, choices, move_number, subject }`
- `quiz_failed`: `{ reason }`
- `game_update`: `{ ...full game state... }`
- `game_over`: `{ reason, winner, elo_change }`
- `draw_offer`: `{ from }`
- `permission_denied`: `{ reason }`
- `move_invalid`: `{ reason }`
- `pong`: `{}`
- `player_joined`, `spectator_joined`, `spectator_left`, `black_player_joined`, `joined_as_black`: `{ ... }`
