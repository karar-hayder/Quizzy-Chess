# Elo-Based Matchmaking System

## Overview

The matchmaking system provides intelligent player pairing based on Elo ratings and win/loss ratios, ensuring fair and competitive games.

## Features

### ✅ Core Functionality

- **Elo-based matching**: Players are matched based on their rating (1200 default)
- **Win/loss ratio consideration**: Accounts for player performance history
- **Dynamic tolerance**: Search criteria relax over time to find matches faster
- **Real-time WebSocket communication**: Instant matchmaking updates
- **Automatic cleanup**: Expired searches are removed automatically
- **Queue management**: Redis-based queue with active search tracking

### ✅ Advanced Features

- **Wait time bonus**: Players who have been waiting longer get priority
- **Progressive search expansion**: Search criteria become more relaxed over time
- **User stats display**: Shows rating, win rate, and game history
- **Search cancellation**: Players can cancel their search at any time
- **Connection health monitoring**: Ping/pong for WebSocket connection health

## Architecture

### Backend Components

#### 1. MatchmakingService (`backend/core/matchmaking.py`)

```python
class MatchmakingService:
    - add_player_to_queue(user_id, user_data)
    - remove_player_from_queue(user_id, search_id)
    - find_match(player_data)
    - create_match(player1_data, player2_data)
    - cleanup_expired_searches()
    - get_queue_status()
```

#### 2. MatchmakingConsumer (`backend/core/matchmaking_consumer.py`)

```python
class MatchmakingConsumer:
    - connect() / disconnect()
    - handle_find_game(payload)
    - handle_cancel_search()
    - try_find_match(user_data)
    - schedule_match_retry(user_data)
```

#### 3. Celery Tasks (`backend/core/tasks.py`)

```python
@shared_task(queue="maintenance")
def cleanup_expired_matchmaking_searches():
    # Runs every 2 minutes to clean up expired searches
```

### Frontend Components

#### 1. MatchmakingModal (`frontend/src/components/MatchmakingModal.vue`)

- User stats display
- Search progress with visual feedback
- Real-time status updates
- Game found notification
- Error handling

#### 2. Home View Integration

- "Find Opponent" button in game options
- Modal integration for seamless UX

## Matching Algorithm

### Score Calculation

The system calculates a match quality score (lower is better):

```python
def _calculate_match_score(self, player1, player2):
    # Elo difference component
    elo_diff = abs(player1["elo"] - player2["elo"])
    elo_score = (elo_diff / self.elo_tolerance) ** 2
    
    # Win/loss ratio difference component
    ratio_diff = abs(player1["win_ratio"] - player2["win_ratio"])
    ratio_score = (ratio_diff / self.ratio_tolerance) ** 2
    
    # Wait time bonus (prefer players who have been waiting longer)
    wait_time1 = time.time() - player1["timestamp"]
    wait_time2 = time.time() - player2["timestamp"]
    wait_bonus = -min(wait_time1, wait_time2) / 10
    
    return elo_score + ratio_score + wait_bonus
```

### Dynamic Tolerance

Search criteria become more relaxed over time:

```python
def _is_acceptable_match(self, player1, player2):
    # Elo tolerance increases with wait time
    wait_time = time.time() - min(player1["timestamp"], player2["timestamp"])
    dynamic_elo_tolerance = self.elo_tolerance + (wait_time / 10) * 50
    
    elo_diff = abs(player1["elo"] - player2["elo"])
    if elo_diff > dynamic_elo_tolerance:
        return False
    
    # Win/loss ratio tolerance
    ratio_diff = abs(player1["win_ratio"] - player2["win_ratio"])
    if ratio_diff > self.ratio_tolerance:
        return False
    
    return True
```

## Configuration

### Default Settings

```python
class MatchmakingService:
    max_wait_time = 60  # seconds
    elo_tolerance = 200  # base Elo difference tolerance
    ratio_tolerance = 0.3  # win/loss ratio tolerance
```

### Celery Beat Schedule

```python
app.conf.beat_schedule = {
    'cleanup-expired-matchmaking-searches': {
        'task': 'core.tasks.cleanup_expired_matchmaking_searches',
        'schedule': crontab(minute='*/2'),  # Every 2 minutes
    },
}
```

## API Endpoints

### GET /api/core/matchmaking/status/

Returns current queue status:

```json
{
  "queue_length": 5,
  "active_searches": 3
}
```

## WebSocket Message Types

### Client → Server

```json
{
  "type": "find_game",
  "payload": {}
}

{
  "type": "cancel_search",
  "payload": {}
}

{
  "type": "ping",
  "payload": {}
}
```

### Server → Client

```json
{
  "type": "search_started",
  "payload": {
    "message": "Searching for opponent...",
    "search_id": "user_id_timestamp"
  }
}

{
  "type": "search_cancelled",
  "payload": {
    "message": "Search cancelled"
  }
}

{
  "type": "game_found",
  "payload": {
    "game": { ...full game fields... },
    "message": "Opponent found! Game starting..."
  }
}

{
  "type": "error",
  "payload": {
    "reason": "Error description"
  }
}

{
  "type": "pong",
  "payload": {}
}
```

## Matching Algorithm

- Elo-based, win/loss ratio, dynamic tolerance (tolerance increases with wait time)
- Queue managed in Redis
- Automatic cleanup of expired searches
- Game creation and notification via WebSocket
- Each search has a unique `search_id` (`user_id_timestamp`)
- Error handling: descriptive error messages for all failure cases

## Usage Flow

### 1. User Initiates Search

1. User clicks "Find Opponent" on home page
2. Frontend loads user stats (rating, win rate, etc.)
3. WebSocket connection established to `/ws/matchmaking/`
4. `find_game` message sent to server

### 2. Server Processing

1. User added to Redis matchmaking queue
2. Server attempts immediate match with existing players
3. If no match found, schedules retry every 5 seconds
4. Search criteria become more relaxed over time

### 3. Match Found

1. Game created between matched players
2. Both players notified via WebSocket
3. Players redirected to game page
4. Search removed from queue

### 4. Search Cancellation

1. User clicks "Cancel Search"
2. `cancel_search` message sent to server
3. User removed from queue
4. Modal resets to initial state

## Error Handling

### Common Scenarios

- **Authentication required**: User not logged in
- **Connection error**: WebSocket connection failed
- **Queue full**: Too many active searches
- **User not found**: User data missing from database
- **Game creation failed**: Database error during game creation

### Recovery Mechanisms

- Automatic retry for failed connections
- Graceful degradation for missing user data
- Timeout handling (60-second max search time)
- Automatic cleanup of expired searches

## Performance Considerations

### Redis Usage

- Queue stored as Redis list for O(1) operations
- Active searches tracked in Redis set
- Automatic expiration for cleanup

### Scalability

- Stateless design allows horizontal scaling
- Redis-based queue supports multiple server instances
- WebSocket connections are independent per user

### Monitoring

- Queue length monitoring via API endpoint
- Search duration tracking
- Error logging for debugging
- Performance metrics for match quality

## Future Enhancements

### Potential Improvements

- **AI opponent fallback**: Match with AI if no human opponent found
- **Tournament mode**: Special matchmaking for tournaments
- **Friend matching**: Allow friends to queue together
- **Time control preferences**: Match based on preferred game speed
- **Geographic matching**: Consider player location for better ping
- **Skill-based leagues**: Separate queues for different skill tiers

### Advanced Features

- **Machine learning**: Use ML to improve match quality
- **Behavioral analysis**: Consider playing style in matching
- **Reputation system**: Factor in player behavior ratings
- **Dynamic difficulty**: Adjust AI strength based on player performance
