'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { authAPI } from '@/utils/api';
import { User } from '@/context/UserContext';

export default function LeaderboardPage() {
  const [leaderboard, setLeaderboard] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLeaderboard();
  }, []);

  const fetchLeaderboard = async () => {
    try {
      setLoading(true);
      const data = await authAPI.getLeaderboard();
      setLeaderboard(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        console.error('Leaderboard error:', err);
        setError(err.message || 'Failed to load leaderboard');
      } else {
        console.error('Leaderboard error:', err);
        setError('Failed to load leaderboard');
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gold-50 to-gold-50">
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gold-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gold-50 to-gold-50">
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
              <Link
                href="/"
                className="text-sm text-gold-600 hover:text-gold-500"
              >
                Home
              </Link>
              <Link
                href="/profile"
                className="text-sm text-gold-600 hover:text-gold-500"
              >
                Profile
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Leaderboard</h1>
          <p className="text-xl text-gray-600">
            Top players ranked by their ELO rating
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-8 bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-sm text-red-600">{error}</p>
            <button
              onClick={fetchLeaderboard}
              className="mt-2 text-sm text-red-600 hover:text-red-500 underline"
            >
              Try again
            </button>
          </div>
        )}

        {/* Leaderboard Table */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Top Players</h2>
          </div>
          
          {leaderboard.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-gray-500">No players found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Rank
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Player
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Rating
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Games
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Win Rate
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Quiz Accuracy
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {leaderboard.map((player, index) => {
                    const winRate = player.games_played > 0 
                      ? ((player.games_won / player.games_played) * 100).toFixed(1) 
                      : '0';
                    const quizAccuracy = player.quiz_attempted > 0 
                      ? ((player.quiz_correct / player.quiz_attempted) * 100).toFixed(1) 
                      : '0';

                    return (
                      <tr key={player.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            {index === 0 && (
                              <div className="w-6 h-6 bg-yellow-400 rounded-full flex items-center justify-center mr-3">
                                <span className="text-xs font-bold text-white">1</span>
                              </div>
                            )}
                            {index === 1 && (
                              <div className="w-6 h-6 bg-gray-400 rounded-full flex items-center justify-center mr-3">
                                <span className="text-xs font-bold text-white">2</span>
                              </div>
                            )}
                            {index === 2 && (
                              <div className="w-6 h-6 bg-orange-500 rounded-full flex items-center justify-center mr-3">
                                <span className="text-xs font-bold text-white">3</span>
                              </div>
                            )}
                            {index > 2 && (
                              <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center mr-3">
                                <span className="text-xs font-bold text-gray-600">{index + 1}</span>
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="flex-shrink-0 h-10 w-10">
                              <div className="h-10 w-10 rounded-full bg-gold-100 flex items-center justify-center">
                                <span className="text-sm font-medium text-gold-600">
                                  {player.username.charAt(0).toUpperCase()}
                                </span>
                              </div>
                            </div>
                            <div className="ml-4">
                              <div className="text-sm font-medium text-gray-900">
                                {player.username}
                              </div>
                              {player.preferred_subject && (
                                <div className="text-sm text-gray-500">
                                  {player.preferred_subject}
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-bold text-gold-600">
                            {player.rating}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {player.games_played}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {winRate}%
                          </div>
                          <div className="text-xs text-gray-500">
                            {player.games_won}W / {player.games_lost}L / {player.games_drawn}D
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {quizAccuracy}%
                          </div>
                          <div className="text-xs text-gray-500">
                            {player.quiz_correct}/{player.quiz_attempted}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Stats Summary */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-gold-600">
                {leaderboard.length}
              </div>
              <div className="text-sm text-gray-600">Total Players</div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">
                {leaderboard.length > 0 ? leaderboard[0].rating : 0}
              </div>
              <div className="text-sm text-gray-600">Highest Rating</div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600">
                {leaderboard.length > 0 
                  ? Math.round(leaderboard.reduce((sum, player) => sum + player.rating, 0) / leaderboard.length)
                  : 0
                }
              </div>
              <div className="text-sm text-gray-600">Average Rating</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
} 