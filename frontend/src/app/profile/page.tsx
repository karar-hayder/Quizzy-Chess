'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI } from '../../utils/api';
import Link from 'next/link';

interface GamePlayer {
  id: number;
  username: string;
  rating: number;
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

interface GameSummary {
  id: string;
  code: string;
  player_white: GamePlayer | null;
  player_black: GamePlayer | null;
  status: string;
  winner: GamePlayer | null;
  created_at: string;
  analysis_status: string;
  analysis: AnalysisResult | null;
}

interface UserProfile {
  id: number;
  username: string;
  rating: number;
  preferred_subject: string | null;
  games_played: number;
  quiz_attempted: number;
  quiz_correct: number;
  games: GameSummary[];
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedGame, setExpandedGame] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    async function fetchProfile() {
      setLoading(true);
      try {
        const data = await authAPI.getProfile();
        setProfile(data);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(`Failed to load profile: ${err.message}`);
        } else {
          setError('Failed to load profile.');
        }
      } finally {
        setLoading(false);
      }
    }
    fetchProfile();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gold-600"></div>
      </div>
    );
  }

  if (error || !profile) {
    return <div className="text-center text-red-600 mt-8">{error || 'No profile data.'}</div>;
  }

  return (
    <div className="min-h-screen bg-offWhite">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <Link href="/" className="text-2xl font-bold text-gold-600">
                Quizzy Chess
              </Link>
              <span className="ml-2 text-sm text-gray-500">Think Before You Take</span>
            </div>
            <div className="flex space-x-4">
              <Link href="/" className="text-sm text-gold-600 hover:text-gold-500">Home</Link>
              <Link href="/leaderboard" className="text-sm text-gold-600 hover:text-gold-500">Leaderboard</Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-white rounded-lg shadow-md p-8">
          <div className="flex justify-between items-center mb-8 ">
            <h1 className="text-3xl font-bold text-deepCharcoal">Profile</h1>
          </div>

          {/* Error/Success Messages */}
          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Profile Details */}
          <div className="mb-8 grid grid-cols-2 gap-4">
            <div>
              <div className="text-slate-700 font-medium">Rating</div>
              <div className="text-2xl font-bold text-deepCharcoal">{profile.rating}</div>
            </div>
            <div>
              <div className="text-slate-700 font-medium">Preferred Subject</div>
              <div className="text-xl font-semibold text-deepCharcoal">{profile.preferred_subject || '-'}</div>
            </div>
            <div>
              <div className="text-slate-700 font-medium">Games Played</div>
              <div className="text-xl font-semibold text-deepCharcoal">{profile.games_played}</div>
            </div>
            <div>
              <div className="text-slate-700 font-medium">Quiz Accuracy</div>
              <div className="text-xl font-semibold text-deepCharcoal">
                {profile.quiz_attempted > 0
                  ? `${Math.round((profile.quiz_correct / profile.quiz_attempted) * 100)}%`
                  : '-'}
              </div>
            </div>
          </div>

          {/* Games Table */}
          <h2 className="text-2xl font-bold mb-4 mt-8 text-deepCharcoal">Your Games</h2>
          {profile.games.length === 0 ? (
            <div className="text-slate-600 font-medium">No games played yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full bg-white border rounded-lg shadow">
                <thead>
                  <tr className="bg-gold-50">
                    <th className="py-2 px-3 text-left text-deepCharcoal font-semibold">Date</th>
                    <th className="py-2 px-3 text-left text-deepCharcoal font-semibold">Opponent</th>
                    <th className="py-2 px-3 text-left text-deepCharcoal font-semibold">Result</th>
                    <th className="py-2 px-3 text-left text-deepCharcoal font-semibold">Analysis</th>
                    <th className="py-2 px-3 text-left text-deepCharcoal font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.games.map((game) => {
                    const isWhite = game.player_white?.id === profile.id;
                    const opponent = isWhite ? game.player_black : game.player_white;
                    let result = '-';
                    if (game.status === 'finished') {
                      if (game.winner && game.winner.id === profile.id) result = 'Win';
                      else if (game.winner) result = 'Loss';
                      else result = 'Draw';
                    } else {
                      result = game.status.charAt(0).toUpperCase() + game.status.slice(1);
                    }
                    return (
                      <React.Fragment key={game.id}>
                        <tr className="border-b hover:bg-gold-50 transition">
                          <td className="py-2 px-3 whitespace-nowrap text-deepCharcoal">{new Date(game.created_at).toLocaleString()}</td>
                          <td className="py-2 px-3 whitespace-nowrap text-deepCharcoal font-medium">{opponent ? opponent.username : 'AI'}</td>
                          <td className="py-2 px-3 whitespace-nowrap">
                            {game.status === 'finished' ? (
                              <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
                                result === 'Win' ? 'bg-green-100 text-green-700' :
                                result === 'Loss' ? 'bg-red-100 text-red-700' :
                                result === 'Draw' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-700'
                              }`}>{result}</span>
                            ) : (
                              <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs font-semibold">{result}</span>
                            )}
                          </td>
                          <td className="py-2 px-3 whitespace-nowrap">
                            {game.analysis_status === 'completed' && game.analysis ? (
                              <span className="inline-block px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-700">Analyzed</span>
                            ) : game.analysis_status === 'in_progress' ? (
                              <span className="inline-block px-2 py-1 rounded text-xs font-semibold bg-yellow-100 text-yellow-700">In Progress</span>
                            ) : (
                              <span className="inline-block px-2 py-1 rounded text-xs font-semibold bg-gray-100 text-gray-700">{game.analysis_status.replace('_', ' ')}</span>
                            )}
                          </td>
                          <td className="py-2 px-3">
                            {game.analysis && (
                              <>
                                <button
                                  className="text-gold-700 hover:text-gold-900 hover:underline text-sm font-medium"
                                  onClick={() => setExpandedGame(expandedGame === game.id ? null : game.id)}
                                >
                                  {expandedGame === game.id ? 'Hide' : 'View'} Analysis
                                </button>
                                <button
                                  className="ml-4 text-green-700 hover:text-green-900 hover:underline text-sm font-medium"
                                  onClick={() => router.push(`/analysis/${game.code}`)}
                                >
                                  View Full Analysis
                                </button>
                              </>
                            )}
                            <button
                              className="ml-4 text-blue-700 hover:text-blue-900 hover:underline text-sm font-medium"
                              onClick={() => router.push(`/game/${game.code}`)}
                            >
                              View Game
                            </button>
                          </td>
                        </tr>
                        {expandedGame === game.id && game.analysis && (
                          <tr>
                            <td colSpan={5} className="bg-gradient-to-br from-gold-50 to-purple-100 p-4 border-t-4 border-gold-300 rounded-b-lg shadow-inner">
                              <div className="rounded-lg p-4 bg-white/90 shadow-md">
                                <div className="mb-2 font-semibold text-deepCharcoal text-lg">Analysis Summary</div>
                                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
                                  <div className="text-deepCharcoal">
                                    <div className="text-sm font-medium">Accuracy</div>
                                    <div className="text-xl font-bold text-gold-800">{Math.round((game.analysis.overall.accuracy || 0) * 100)}%</div>
                                  </div>
                                  <div className="text-deepCharcoal">
                                    <div className="text-sm font-medium">Best Moves</div>
                                    <div className="text-xl font-bold text-green-800">{game.analysis.overall.best_moves || 0}</div>
                                  </div>
                                  <div className="text-deepCharcoal">
                                    <div className="text-sm font-medium">Total Moves</div>
                                    <div className="text-xl font-bold text-deepCharcoal">{game.analysis.overall.total_moves}</div>
                                  </div>
                                  <div className="text-deepCharcoal">
                                    <div className="text-sm font-medium">Blunders</div>
                                    <div className="text-xl font-bold text-red-800">{game.analysis.overall.blunders}</div>
                                  </div>
                                  <div className="text-deepCharcoal">
                                    <div className="text-sm font-medium">Inaccuracies</div>
                                    <div className="text-xl font-bold text-yellow-800">{game.analysis.overall.inaccuracies}</div>
                                  </div>
                                </div>
                                <div className="mb-2 font-semibold text-deepCharcoal text-lg">Per-Move Analysis</div>
                                <div className="overflow-x-auto">
                                  <table className="min-w-full text-xs border rounded-lg">
                                    <thead>
                                      <tr className="bg-gold-100">
                                        <th className="py-1 px-2 text-deepCharcoal font-semibold">#</th>
                                        <th className="py-1 px-2 text-deepCharcoal font-semibold">Played</th>
                                        <th className="py-1 px-2 text-deepCharcoal font-semibold">Best</th>
                                        <th className="py-1 px-2 text-deepCharcoal font-semibold">Eval</th>
                                        <th className="py-1 px-2 text-deepCharcoal font-semibold">Comment</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {game.analysis.per_move.map((move, idx) => (
                                        <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gold-50'}>
                                          <td className="py-1 px-2 text-deepCharcoal">{move.move_number}</td>
                                          <td className="py-1 px-2 font-mono text-deepCharcoal">{move.played}</td>
                                          <td className="py-1 px-2 font-mono text-deepCharcoal">{move.best || '-'}</td>
                                          <td className="py-1 px-2 text-deepCharcoal">
                                            {move.evaluation !== null ? (
                                              <span className={`font-semibold ${
                                                move.evaluation > 0 ? 'text-green-800' :
                                                move.evaluation < 0 ? 'text-red-800' : 'text-deepCharcoal'
                                              }`}>
                                                {(move.evaluation / 100).toFixed(1)}
                                              </span>
                                            ) : '-'}
                                          </td>
                                          <td className="py-1 px-2">
                                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                                              move.comment === 'Best' ? 'bg-green-100 text-green-900' :
                                              move.comment === 'Blunder' ? 'bg-red-100 text-red-900' :
                                              move.comment === 'Inaccuracy' ? 'bg-yellow-100 text-yellow-900' :
                                              'bg-gray-100 text-gray-900'
                                            }`}>{move.comment}</span>
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
} 