'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useUser } from '@/context/UserContext';
import { gameAPI } from '@/utils/api';
import Chessboard from '@/components/Chessboard';
import QuizModal, { QuizResult } from '@/components/QuizModal';
import { AxiosError } from 'axios';

interface GamePlayer {
  id: number;
  username: string;
  rating: number;
}

interface GameState extends Record<string, unknown> {
  id: number;
  code: string;
  player_white: GamePlayer | null;
  player_black: GamePlayer | null;
  fen: string;
  status: string;
  subjects: string[];
  winner: GamePlayer | null;
  is_vs_ai: boolean;
  ai_difficulty: string;
  created_at: string;
  moves: unknown[];
  analysis_status: string;
  analysis: AnalysisResult | null;
}

interface QuizPayload extends Record<string, unknown> {
  question: string;
  choices: string[];
  move_number: number;
  subject: string;
  correct?: string;
  explanation?: string;
}

interface GameOverPayload extends Record<string, unknown> {
  reason: string;
  winner: string | null;
  elo_change?: unknown; // Can be more specific if needed
}

interface AnalysisResult {
  overall: {
    accuracy: number;
    blunders: number;
    inaccuracies: number;
    total_moves: number;
    best_moves: number;
  };
  per_move: Array<{
    move_number: number;
    played: string;
    best: string;
    evaluation: number;
    comment: string;
  }>;
}

// Type Guard Functions
function isPlayerJoinedPayload(payload: Record<string, unknown>): payload is { user: string; player: string } {
  return typeof payload.user === 'string' && typeof payload.player === 'string';
}

function isSpectatorPayload(payload: Record<string, unknown>): payload is { user: string } {
  return typeof payload.user === 'string';
}

function isDrawOfferPayload(payload: Record<string, unknown>): payload is { from: string } {
  return typeof payload.from === 'string';
}

function isGameStatePayload(payload: Record<string, unknown>): payload is GameState {
  return typeof payload.fen === 'string' && typeof payload.status === 'string' &&
         ('player_white' in payload || payload.player_white === null) &&
         ('player_black' in payload || payload.player_black === null);
}

function isMovePayload(payload: Record<string, unknown>): payload is { fen_after?: string, from_square: string, to_square: string, piece: string } {
  return typeof payload.from_square === 'string' && typeof payload.to_square === 'string' && typeof payload.piece === 'string';
}

function isQuizRequiredPayload(payload: Record<string, unknown>): payload is QuizPayload {
  return typeof payload.question === 'string' && Array.isArray(payload.choices) &&
         typeof payload.move_number === 'number' && typeof payload.subject === 'string';
}

function isQuizFailedPayload(payload: Record<string, unknown>): payload is { fen?: string, blocked_move?: string } {
  return ('fen' in payload || 'blocked_move' in payload);
}

function isGameOverPayload(payload: Record<string, unknown>): payload is GameOverPayload {
  return typeof payload.reason === 'string' && ('winner' in payload || payload.winner === null);
}

function isReasonPayload(payload: Record<string, unknown>): payload is { reason?: string } {
  return typeof payload.reason === 'string' || typeof payload.reason === 'undefined';
}


export default function GameRoomPage() {
  const { user, loading } = useUser();
  const router = useRouter();
  const params = useParams();
  const gameCode = typeof params.code === 'string' ? params.code : Array.isArray(params.code) ? params.code[0] : '';

  const [game, setGame] = useState<GameState | null>(null);
  const [fen, setFen] = useState('');
  const [isMyTurn, setIsMyTurn] = useState(false);
  const [lastMove, setLastMove] = useState<{ from: string; to: string } | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [quizModal, setQuizModal] = useState<{
    open: boolean;
    moveId: number;
    subject: string;
    questionId: number;
  } | null>(null);
  const [quizPayload, setQuizPayload] = useState<QuizPayload | null>(null);
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null);
  const [gameStatus, setGameStatus] = useState<string>('');
  const [info, setInfo] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [blockedMoves, setBlockedMoves] = useState<string[]>([]);
   
  const [error, setError] = useState<string | null>(null);
 
  const loadGame = useCallback(async () => {
    try {
      const gameData = await gameAPI.getGame(gameCode);
      setGame(gameData);
      setFen(gameData.fen);
      setIsMyTurn(user ? (gameData.player_white?.id === user.id && gameData.fen.includes(' w ')) || (gameData.player_black?.id === user.id && gameData.fen.includes(' b ')) : false);
      setGameStatus(gameData.status);
      setError(null);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(`Failed to load game: ${err.message}`);
      } else {
        setError('Failed to load game.');
      }
    }
  }, [gameCode, user]);

  // Handle WebSocket messages
   
  const handleWsMessage = useCallback((data: { type: string; payload?: Record<string, unknown> }) => {
    if (typeof data !== 'object' || data === null || !('type' in data)) {
      console.warn('Received non-object or malformed WS message:', data);
      return;
    }

    const messageType = data.type;
    const payload = data.payload;

    if (!payload || typeof payload !== 'object') {
      // For messages that don't have a payload or have a non-object payload
      switch (messageType) {
        case 'joined_as_black':
          setInfo('Successfully joined as black player');
          loadGame();
          break;
        case 'pong':
          break;
        default:
          console.warn('Unknown WS message (no valid payload):', data);
          break;
      }
      return;
    }

    switch (messageType) {
      case 'player_joined':
        if (isPlayerJoinedPayload(payload)) {
          setInfo(`${payload.user} joined as ${payload.player}`);
          loadGame();
        }
        break;
      case 'spectator_joined':
        if (isSpectatorPayload(payload)) {
          setInfo(`${payload.user} joined as spectator`);
        }
        break;
      case 'spectator_left':
        if (isSpectatorPayload(payload)) {
          setInfo(`${payload.user} left the game`);
        }
        break;
      case 'black_player_joined':
        if (isSpectatorPayload(payload)) { // using spectator payload as it has 'user'
          setInfo(`${payload.user} joined as black player`);
          loadGame();
        }
        break;
      case 'joined_as_black': // Handled above for no payload, but including here for consistency in switch
        setInfo('Successfully joined as black player');
        loadGame();
        break;
      case 'draw_offer':
        if (isDrawOfferPayload(payload)) {
          setInfo(`${payload.from} offered a draw`);
        }
        break;
      case 'game_update':
        if (isGameStatePayload(payload)) {
          setGame(payload);
          setFen(payload.fen);
          setGameStatus(payload.status);
        }
        break;
      case 'move':
        if (isMovePayload(payload)) {
          setFen(payload.fen_after || '');
          setLastMove({
            from: payload.from_square,
            to: payload.to_square,
          });
          setInfo(`${payload.piece.toUpperCase()} moved from ${payload.from_square} to ${payload.to_square}`);
        }
        if (quizModal) {
          setQuizResult({ correct: true });
          setTimeout(() => {
            setQuizModal(null);
            setQuizPayload(null);
            setQuizResult(null);
            setInfo('Correct! Move completed.');
          }, 2000);
        }
        break;
      case 'quiz_required':
        if (isQuizRequiredPayload(payload)) {
          setQuizPayload(payload);
          setQuizModal({
            open: true,
            moveId: payload.move_number,
            subject: payload.subject,
            questionId: payload.move_number || 0,
          });
        }
        setInfo('Quiz required to complete your move!');
        break;
      case 'quiz_failed':
        if (isQuizFailedPayload(payload)) {
          console.log('Quiz failed, reverting move with FEN:', payload.fen);
          setInfo('Quiz failed. Move cancelled.');
          setQuizModal(null);
          setQuizPayload(null);
          setQuizResult(null);
          if (payload.fen) {
            setFen(payload.fen || '');
            console.log('Board FEN updated to:', payload.fen);
          }
          if (payload.blocked_move) {
            console.log('Blocking move:', payload.blocked_move);
            setBlockedMoves((prev) => [...prev, payload.blocked_move || '']);
          }
        }
        break;
      case 'game_over':
        if (isGameOverPayload(payload)) {
          setGameStatus('finished');
          setInfo(`Game over! Winner: ${payload.winner}`);
        }
        break;
      case 'move_invalid':
        if (isReasonPayload(payload)) {
          setError(payload.reason || 'Invalid move.');
        }
        break;
      case 'permission_denied':
        if (isReasonPayload(payload)) {
          setError(payload.reason || 'Permission denied.');
        }
        break;
      case 'pong': // Handled above for no payload, but including here for consistency in switch
        break;
      default:
        console.warn('Unknown WS message:', data);
    }
  }, [quizModal, loadGame, user]);

  // Load game state on mount
  useEffect(() => {
    if (!user && !loading) {
      router.push('/');
      return;
    }
    if (gameCode) {
      loadGame();
    }
    // eslint-disable-next-line
  }, [gameCode, user, loading, loadGame]);

  // WebSocket connection
  useEffect(() => {
    if (!gameCode || !user) return;

    const token = localStorage.getItem('access_token');
    if (!token) {
      setError('Authentication required');
      return;
    }

    const wsUrl = `ws://127.0.0.1:8000/ws/game/${gameCode}/?token=${token}`;
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('WebSocket connected');
      setError(null);
      // Store global reference for quiz modal
      (window as unknown as { gameWebSocket: WebSocket | null }).gameWebSocket = websocket;
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message received:', data);
        handleWsMessage(data);
      } catch (err: unknown) {
        console.error('WebSocket message error:', err);
      }
    };

    websocket.onerror = () => {
      console.warn('WebSocket connection error occurred');
      setError('WebSocket connection error');
    };

    websocket.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      // Remove global WebSocket reference
      (window as unknown as { gameWebSocket: WebSocket | null }).gameWebSocket = null;
      
      // Only show error if it wasn't a normal closure
      if (event.code !== 1000) {
        setError('WebSocket connection lost. Please refresh the page.');
      }
    };

    setWs(websocket);

    return () => {
      websocket.close();
      (window as unknown as { gameWebSocket: WebSocket | null }).gameWebSocket = null;
    };
  }, [gameCode, user, handleWsMessage]);

  // Handle move from Chessboard
  const handleMove = (from: string, to: string, piece: string, captured?: string, promotion?: string) => {
    if (game?.status !== 'active') {
      setError('Game is not active.');
      return;
    }

    if (blockedMoves.includes(`${from}${to}`)) {
      setError('You cannot repeat this move after failing the quiz.');
      return;
    }
    const moveStr = `${from}${to}`;
    console.log('Attempting move:', moveStr, 'Blocked:', blockedMoves);
    if (blockedMoves.includes(moveStr)) {
      setError('You cannot repeat this move this round after failing the quiz.');
      return;
    }
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(
      JSON.stringify({
        type: 'move',
        payload: {
          from_square: from,
          to_square: to,
          piece: piece.toUpperCase(),
          captured_piece: captured || null,
          move_number: game?.moves?.length ? (game.moves.length as number) + 1 : 1,
          ...(promotion ? { promotion } : {}),
        },
      })
    );
  };

  // Handle quiz answer
  const handleQuizAnswer = (correct: boolean) => {
    setQuizModal(null);
    setQuizPayload(null);
    if (correct) {
      setInfo('Correct! Move completed.');
    } else {
      setInfo('Incorrect. Move cancelled.');
    }
  };

  // Handle game analysis
  const handleAnalyzeGame = async () => {
    if (!gameCode) return;
    
    setAnalyzing(true);
    setError(null);
    try {
      const analysisData = await gameAPI.getGameAnalysis(gameCode);
      setAnalysis(analysisData);
      setInfo('Game analysis completed!');
    } catch (err: unknown) {
      if (err instanceof AxiosError && err.response?.status === 202) {
        setError('Analysis is being generated. Please try again in a few minutes.');
      } else if (err instanceof Error) {
        setError(`Failed to analyze game: ${err.message}`);
      } else {
        setError('Failed to analyze game.');
      }
    } finally {
      setAnalyzing(false);
    }
  };

  // Determine if it's the user's turn
  useEffect(() => {
    if (!game || !user) return;
    
    // Determine color
    let myColor: 'white' | 'black' | null = null;
    if (game.player_white?.id === user.id) myColor = 'white';
    if (game.player_black?.id === user.id) myColor = 'black';
    
    // For AI games, if user is not assigned a color yet, they will be white
    if (game.is_vs_ai && !myColor) {
      myColor = 'white';
    }
    
    // Determine turn from FEN
    if (fen) {
      const turn = fen.split(' ')[1] === 'w' ? 'white' : 'black';
      setIsMyTurn(myColor === turn);
    }
  }, [game, user, fen, handleWsMessage]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  // Determine player colors and AI info
  const isAIGame = game?.is_vs_ai || false;
  const aiDifficulty = game?.ai_difficulty || 'easy';
  const myColor = game?.player_white?.id === user.id ? 'white' : 
                  game?.player_black?.id === user.id ? 'black' : 
                  isAIGame ? 'white' : null;

  return (
    <div className="min-h-screen bg-offWhite">
      {/* Header */}
      <header className="bg-deepCharcoal shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <span className="text-2xl font-bold text-softWhite">Quizzy Chess</span>
              <span className="ml-2 text-sm text-slateGray">Game Room</span>
              {isAIGame && (
                <span className="ml-2 px-2 py-1 bg-matteGold text-matteGold text-xs rounded-full">vs AI ({aiDifficulty})</span>
              )}
            </div>
            <div className="flex space-x-4">
              <span className="text-sm text-slateGray">Game Code: <span className="font-mono">{gameCode}</span></span>
              <button onClick={() => router.push('/')} className="text-sm text-softWhite hover:text-softWhite">Home</button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12 flex flex-col md:flex-row gap-8">
        {/* Chessboard */}
        <div className="flex-1 flex flex-col items-center">
          <Chessboard
            fen={fen}
            onMove={handleMove}
            lastMove={lastMove || undefined}
            isMyTurn={isMyTurn}
            disabled={!isMyTurn || gameStatus === 'finished'}
            blockedMoves={blockedMoves}
          />
          <div className="mt-4 text-center">
            {isMyTurn ? (
              <span className="text-emeraldHint font-semibold">Your turn</span>
            ) : isAIGame ? (
              <span className="text-matteGold font-semibold">AI is thinking...</span>
            ) : (
              <span className="text-slateGray">Waiting for opponent...</span>
            )}
          </div>
        </div>

        {/* Game Info Panel */}
        <div className="w-full md:w-80 bg-deepCharcoal rounded-lg shadow-md p-6 flex flex-col gap-4">
          <h2 className="text-lg font-semibold text-softWhite mb-2">Players</h2>
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-deepCharcoal border border-slateGray"></span>
              <span className="font-bold text-softWhite">{game?.player_white?.username || (isAIGame && myColor === 'white' ? user.username : 'Waiting...')}</span>
              <span className="text-xs text-slateGray">(White)</span>
              <span className="ml-auto text-xs text-slateGray">{game?.player_white?.rating || (isAIGame && myColor === 'white' ? user.rating : '')}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-black"></span>
              <span className="font-bold text-softWhite">{game?.player_black?.username || (isAIGame && myColor === 'black' ? user.username : isAIGame ? `AI (${aiDifficulty})` : 'Waiting...')}</span>
              <span className="text-xs text-slateGray">(Black)</span>
              <span className="ml-auto text-xs text-slateGray">{game?.player_black?.rating || (isAIGame ? 'AI' : '')}</span>
            </div>
          </div>
          
          {isAIGame && (
            <div className="mt-2 p-3 bg-matteGold rounded-md">
              <div className="text-sm text-matteGold">
                <div className="font-medium mb-1">AI Opponent</div>
                <div>Difficulty: {aiDifficulty.charAt(0).toUpperCase() + aiDifficulty.slice(1)}</div>
                <div>You are playing as: {myColor ? myColor.charAt(0).toUpperCase() + myColor.slice(1) : 'Unknown'}</div>
              </div>
            </div>
          )}
          
          <div className="mt-4">
            <h3 className="text-sm font-medium text-slateGray mb-1">Status</h3>
            <div className="text-sm text-softWhite">
              {gameStatus === 'active' && 'Game in progress'}
              {gameStatus === 'waiting' && 'Waiting for opponent...'}
              {gameStatus === 'finished' && 'Game finished'}
            </div>
            <div className="text-sm text-softWhite">Game Fen: {fen}</div>
          </div>
          <div className="mt-4">
            <h3 className="text-sm font-medium text-slateGray mb-1">Subjects</h3>
            <div className="flex flex-wrap gap-2">
              {game?.subjects?.map((s) => (
                <span key={s} className="bg-softWhite text-softWhite px-2 py-1 rounded text-xs">{s}</span>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          {gameStatus === 'active' && (
            <div className="mt-6 flex flex-col gap-2">
              <button
                onClick={() => {
                  if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: 'resign', payload: {} }));
                  }
                }}
                className="w-full bg-red-600 text-softWhite py-2 px-4 rounded-md hover:bg-red-700 transition-colors"
              >
                Resign
              </button>
              {!isAIGame && (
                <button
                  onClick={() => {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                      ws.send(JSON.stringify({ type: 'draw_offer', payload: {} }));
                    }
                  }}
                  className="w-full bg-matteGold text-softWhite py-2 px-4 rounded-md hover:bg-matteGold transition-colors"
                >
                  Offer Draw
                </button>
              )}
            </div>
          )}

          {/* Analysis Button - Show when game is finished */}
          {gameStatus === 'finished' && (
            <div className="mt-6 flex flex-col gap-2">
              {analysis ? (
                <button
                  onClick={() => router.push(`/analysis/${gameCode}`)}
                  className="w-full bg-emeraldHint text-softWhite py-2 px-4 rounded-md hover:bg-emeraldHint shadow-lg transition-colors font-semibold text-lg border-2 border-emeraldHint"
                >
                  View Full Analysis
                </button>
              ) : (
                <button
                  onClick={handleAnalyzeGame}
                  disabled={analyzing}
                  className="w-full bg-softWhite text-softWhite py-2 px-4 rounded-md hover:bg-softWhite disabled:bg-slateGray shadow-lg transition-colors font-semibold text-lg border-2 border-softWhite"
                >
                  {analyzing ? 'Analyzing...' : 'Analyze Game'}
                </button>
              )}
            </div>
          )}

          {info && (
            <div className="mt-4 bg-softWhite border border-slateGray rounded-md p-2 text-softWhite text-xs">{info}</div>
          )}
          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-md p-2 text-red-700 text-xs">{error}</div>
          )}
        </div>
      </main>

      {/* Quiz Modal */}
      {quizModal && quizPayload && (
        <QuizModal
          isOpen={!!quizModal?.open}
          onClose={() => setQuizModal(null)}
          onAnswer={handleQuizAnswer}
          moveId={quizModal?.moveId || 0}
          subject={quizModal?.subject || ''}
          questionId={quizModal?.questionId || 0}
          quizData={{
            question: quizPayload.question,
            choices: quizPayload.choices,
            correct: quizPayload.correct || '',
            explanation: quizPayload.explanation || '',
          }}
          quizResult={quizResult}
        />
      )}
    </div>
  );
} 