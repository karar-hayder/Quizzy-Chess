'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { gameAPI } from '../../../utils/api';
import Chessboard from '../../../components/Chessboard';
import { AxiosError } from 'axios';

interface GamePlayer {
  id: number;
  username: string;
  rating: number;
}

interface GameState {
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

export default function AnalysisPage() {
  const params = useParams();
  const gameCode = params.gameCode as string;
  
  const [game, setGame] = useState<GameState | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentMoveIndex, setCurrentMoveIndex] = useState(-1); // -1 = starting position
  const [currentFen, setCurrentFen] = useState<string>('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');

  useEffect(() => {
    async function loadGameAndAnalysis() {
      if (!gameCode) return;
      
      setLoading(true);
      try {
        // Load game data
        const gameData = await gameAPI.getGame(gameCode);
        setGame(gameData);
        
        // Load analysis data
        try {
          const analysisData = await gameAPI.getGameAnalysis(gameCode);
          setAnalysis(analysisData);
        } catch (err: unknown) {
          if (err instanceof AxiosError && err.response?.status === 202) {
            setError('Analysis is being generated. Please try again in a few minutes.');
          } else {
            setError('Failed to load game analysis.');
          }
          if (err instanceof Error) {
            console.error('Analysis error:', err.message);
          } else {
            console.error('Analysis error:', err);
          }
        }
      } catch (err: unknown) {
        setError('Failed to load game.');
        if (err instanceof Error) {
          console.error('Game load error:', err.message);
        } else {
          console.error('Game load error:', err);
        }
      } finally {
        setLoading(false);
      }
    }
    
    loadGameAndAnalysis();
  }, [gameCode]);

  const goToMove = (moveIndex: number) => {
    setCurrentMoveIndex(moveIndex);
    
    if (moveIndex === -1) {
      // Starting position
      setCurrentFen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    } else if (game && game.moves && game.moves[moveIndex]) {
      // Use the FEN from the move
      const move = game.moves[moveIndex] as { fen_after?: string };
      if (move && typeof move === 'object' && 'fen_after' in move && move.fen_after) {
        setCurrentFen(move.fen_after);
      }
    }
  };

  const goToPreviousMove = () => {
    if (currentMoveIndex > -1) {
      goToMove(currentMoveIndex - 1);
    }
  };

  const goToNextMove = () => {
    if (analysis && currentMoveIndex < analysis.per_move.length - 1) {
      goToMove(currentMoveIndex + 1);
    }
  };

  const goToFirstMove = () => {
    goToMove(-1);
  };

  const goToLastMove = () => {
    if (analysis) {
      goToMove(analysis.per_move.length - 1);
    }
  };

  // Helper to group moves by move number (white/black)
  const groupedMoves = analysis ? (() => {
    const groups: Array<{
      moveNumber: number;
      white?: typeof analysis.per_move[0];
      black?: typeof analysis.per_move[0];
    }> = [];
    for (let i = 0; i < analysis.per_move.length; i += 2) {
      groups.push({
        moveNumber: analysis.per_move[i].move_number,
        white: analysis.per_move[i],
        black: analysis.per_move[i + 1],
      });
    }
    return groups;
  })() : [];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error || !game) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-purple-50">
        <div className="max-w-4xl mx-auto px-4 py-12">
          <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">Analysis Error</h1>
            <p className="text-red-600 mb-6">{error || 'Game not found'}</p>
            <Link href="/profile" className="text-indigo-600 hover:text-indigo-500">
              ← Back to Profile
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-purple-50">
        <div className="max-w-4xl mx-auto px-4 py-12">
          <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">Analysis Not Available</h1>
            <p className="text-gray-600 mb-6">Game analysis is not available for this game.</p>
            <Link href="/profile" className="text-indigo-600 hover:text-indigo-500">
              ← Back to Profile
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-offWhite">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <Link href="/" className="text-2xl font-bold text-indigo-600">
                Quizzy Chess
              </Link>
              <span className="ml-2 text-sm text-gray-500">Game Analysis</span>
            </div>
            <div className="flex space-x-4">
              <Link href="/profile" className="text-sm text-indigo-600 hover:text-indigo-500">Profile</Link>
              <Link href="/" className="text-sm text-indigo-600 hover:text-indigo-500">Home</Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Compact Game Details Bar */}
        <div className="bg-white rounded-xl shadow flex flex-wrap items-center justify-between px-4 py-2 mb-8 gap-4 text-sm">
          <div className="flex items-center gap-4">
            <span className="font-semibold text-gray-900">White:</span>
            <span className="text-gray-800">{game.player_white?.username || 'AI'}</span>
            <span className="font-semibold text-gray-900">Black:</span>
            <span className="text-gray-800">{game.player_black?.username || 'AI'}</span>
            <span className="font-semibold text-gray-900">Result:</span>
            <span className="text-gray-800">{game.winner ? `${game.winner.username} won` : 'Draw'}</span>
            <span className="font-semibold text-gray-900">Date:</span>
            <span className="text-gray-800">{new Date(game.created_at).toLocaleDateString()}</span>
          </div>
          <span className="text-indigo-600 font-bold text-lg">Game Analysis</span>
        </div>
        {/* Main Two-Column Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-16">
          {/* Left: Board and Move List */}
          <div className="flex flex-col items-center">
            <div className="bg-white rounded-2xl shadow-xl w-full flex flex-col items-center mb-8">
              <h2 className="text-lg font-semibold text-gray-800 mb-4 text-center">Board Position</h2>
              <div className="flex justify-center w-full my-10">
                <div className="mx-auto w-full flex justify-center">
                  <div className="w-full sm:w-96 md:w-[480px] lg:w-[560px] xl:w-[640px] mx-auto">
                    <Chessboard
                      fen={currentFen}
                      onMove={() => {}} // Disabled for analysis view
                      disabled={true}
                      isMyTurn={false}
                    />
                  </div>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-2xl shadow-xl w-full flex flex-col items-center">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Move List</h2>
              <div className="max-h-[600px] overflow-y-auto w-full">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-indigo-50">
                      <th className="py-2 px-2 text-left text-gray-900 font-semibold w-12">#</th>
                      <th className="py-2 px-2 text-left text-gray-900 font-semibold">White</th>
                      <th className="py-2 px-2 text-left text-gray-900 font-semibold">Eval</th>
                      <th className="py-2 px-2 text-left text-gray-900 font-semibold">Black</th>
                      <th className="py-2 px-2 text-left text-gray-900 font-semibold">Eval</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Starting position row */}
                    <tr className={currentMoveIndex === -1 ? 'bg-indigo-100' : ''}>
                      <td className="py-1 px-2 text-gray-900 font-mono text-xs">0</td>
                      <td colSpan={4}>
                        <button
                          className="w-full text-left px-2 py-1 rounded hover:bg-indigo-50"
                          onClick={() => goToMove(-1)}
                        >
                          Starting Position
                        </button>
                      </td>
                    </tr>
                    {groupedMoves.map((group, idx) => (
                      <tr key={idx} className="border-b last:border-0">
                        <td className="py-1 px-2 text-gray-900 font-mono text-xs align-top">{group.moveNumber}</td>
                        {/* White move */}
                        <td className="py-1 px-2 align-top">
                          {group.white ? (
                            <button
                              className={`w-full text-left px-2 py-1 rounded transition-colors ${
                                currentMoveIndex === idx * 2 ? 'bg-indigo-100 font-bold text-indigo-900' : 'hover:bg-indigo-50'
                              }`}
                              onClick={() => goToMove(idx * 2)}
                            >
                              <span className="font-mono text-gray-900">{group.white.played}</span>
                              {group.white.comment !== 'OK' && (
                                <span className={`ml-2 px-2 py-1 rounded text-xs font-medium ${
                                  group.white.comment === 'Best' ? 'bg-green-100 text-green-900' :
                                  group.white.comment === 'Blunder' ? 'bg-red-100 text-red-900' :
                                  group.white.comment === 'Inaccuracy' ? 'bg-yellow-100 text-yellow-900' :
                                  'bg-gray-100 text-gray-900'
                                }`}>
                                  {group.white.comment}
                                </span>
                              )}
                            </button>
                          ) : null}
                        </td>
                        {/* White eval */}
                        <td className="py-1 px-2 align-top">
                          {group.white && (
                            <span className={`font-semibold ${
                              group.white.evaluation > 0 ? 'text-green-900' : 
                              group.white.evaluation < 0 ? 'text-red-900' : 'text-gray-900'
                            }`}>
                              {(group.white.evaluation / 100).toFixed(1)}
                            </span>
                          )}
                        </td>
                        {/* Black move */}
                        <td className="py-1 px-2 align-top">
                          {group.black ? (
                            <button
                              className={`w-full text-left px-2 py-1 rounded transition-colors ${
                                currentMoveIndex === idx * 2 + 1 ? 'bg-indigo-100 font-bold text-indigo-900' : 'hover:bg-indigo-50'
                              }`}
                              onClick={() => goToMove(idx * 2 + 1)}
                            >
                              <span className="font-mono text-gray-900">{group.black.played}</span>
                              {group.black.comment !== 'OK' && (
                                <span className={`ml-2 px-2 py-1 rounded text-xs font-medium ${
                                  group.black.comment === 'Best' ? 'bg-green-100 text-green-900' :
                                  group.black.comment === 'Blunder' ? 'bg-red-100 text-red-900' :
                                  group.black.comment === 'Inaccuracy' ? 'bg-yellow-100 text-yellow-900' :
                                  'bg-gray-100 text-gray-900'
                                }`}>
                                  {group.black.comment}
                                </span>
                              )}
                            </button>
                          ) : null}
                        </td>
                        {/* Black eval */}
                        <td className="py-1 px-2 align-top">
                          {group.black && (
                            <span className={`font-semibold ${
                              group.black.evaluation > 0 ? 'text-green-900' : 
                              group.black.evaluation < 0 ? 'text-red-900' : 'text-gray-900'
                            }`}>
                              {(group.black.evaluation / 100).toFixed(1)}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          {/* Right: Navigation, Current Position, Overall Performance */}
          <div className="flex flex-col items-center gap-8">
            <div className="bg-white rounded-2xl shadow-xl p-6 w-full flex flex-col items-center">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Navigation</h2>
              <div className="flex flex-wrap gap-2 mb-2">
                <button onClick={goToFirstMove} className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-sm">⏮ First</button>
                <button onClick={goToPreviousMove} disabled={currentMoveIndex <= -1} className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 disabled:opacity-50 text-sm">⏪ Previous</button>
                <button onClick={goToNextMove} disabled={currentMoveIndex >= analysis.per_move.length - 1} className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 disabled:opacity-50 text-sm">⏩ Next</button>
                <button onClick={goToLastMove} className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-sm">⏭ Last</button>
              </div>
              <div className="text-sm text-gray-800">Move {currentMoveIndex + 1} of {analysis.per_move.length}</div>
            </div>
            <div className="bg-white rounded-2xl shadow-xl p-6 w-full flex flex-col items-center">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Current Position</h2>
              <div className="text-sm text-gray-800">
                {currentMoveIndex === -1 ? (
                  <div>Starting position</div>
                ) : currentMoveIndex < analysis.per_move.length ? (
                  <div>
                    <div className="mb-2">
                      <strong>Move {analysis.per_move[currentMoveIndex].move_number}:</strong>
                    </div>
                    <div className="space-y-1">
                      <div>Played: <span className="font-mono text-gray-900">{analysis.per_move[currentMoveIndex].played}</span></div>
                      <div>Best: <span className="font-mono text-gray-900">{analysis.per_move[currentMoveIndex].best || '-'}</span></div>
                      <div>Evaluation: 
                        <span className={`font-semibold ml-1 ${
                          analysis.per_move[currentMoveIndex].evaluation > 0 ? 'text-green-900' : 
                          analysis.per_move[currentMoveIndex].evaluation < 0 ? 'text-red-900' : 'text-gray-900'
                        }`}>
                          {(analysis.per_move[currentMoveIndex].evaluation / 100).toFixed(1)}
                        </span>
                      </div>
                      <div>Comment: 
                        <span className={`ml-1 px-2 py-1 rounded text-xs font-medium ${
                          analysis.per_move[currentMoveIndex].comment === 'Best' ? 'bg-green-100 text-green-900' :
                          analysis.per_move[currentMoveIndex].comment === 'Blunder' ? 'bg-red-100 text-red-900' :
                          analysis.per_move[currentMoveIndex].comment === 'Inaccuracy' ? 'bg-yellow-100 text-yellow-900' :
                          'bg-gray-100 text-gray-900'
                        }`}>
                          {analysis.per_move[currentMoveIndex].comment}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div>End position</div>
                )}
              </div>
            </div>
            <div className="bg-white rounded-2xl shadow-xl p-6 w-full flex flex-col items-center">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Overall Performance</h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-3 bg-blue-50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-900">{(analysis.overall.accuracy * 100).toFixed(1)}%</div>
                  <div className="text-xs text-gray-700">Accuracy</div>
                </div>
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-900">{analysis.overall.best_moves}</div>
                  <div className="text-xs text-gray-700">Best Moves</div>
                </div>
                <div className="text-center p-3 bg-red-50 rounded-lg">
                  <div className="text-2xl font-bold text-red-900">{analysis.overall.blunders}</div>
                  <div className="text-xs text-gray-700">Blunders</div>
                </div>
                <div className="text-center p-3 bg-yellow-50 rounded-lg">
                  <div className="text-2xl font-bold text-yellow-900">{analysis.overall.inaccuracies}</div>
                  <div className="text-xs text-gray-700">Inaccuracies</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
} 