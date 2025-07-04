'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useUser } from '@/context/UserContext';
import AuthForm from '@/components/AuthForm';
import MatchmakingModal from '@/components/MatchmakingModal';
import { gameAPI } from '@/utils/api';
import { useRouter } from 'next/navigation';

export default function HomePage() {
  const { user, loading, logout } = useUser();
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [showAuth, setShowAuth] = useState(false);
  const [showMatchmaking, setShowMatchmaking] = useState(false);
  const [creatingGame, setCreatingGame] = useState(false);
  const [joinCode, setJoinCode] = useState('');
  const [joinError, setJoinError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [showAIOptions, setShowAIOptions] = useState(false);
  const [aiDifficulty, setAiDifficulty] = useState<'easy' | 'medium' | 'hard'>('easy');
  const router = useRouter();

  // Handle game found/created
  const handleGameFound = (code: string) => {
    console.log('handleGameFound called with code:', code);
    setShowMatchmaking(false);
    setCreatingGame(false);
    setShowAIOptions(false);
    setJoinError(null);
    setCreateError(null);
    console.log('About to navigate to game:', `/game/${code}`);
    router.push(`/game/${code}`);
  };

  // Handle create game
  const handleCreateGame = async () => {
    setCreatingGame(true);
    setCreateError(null);
    try {
      const data = await gameAPI.createOrJoinGame({ subjects: ['Math', 'Science', 'Sports'] });
      handleGameFound(data.code);
    } catch (err: unknown) {
      setCreateError('Failed to create game.');
      setCreatingGame(false);
      if (err instanceof Error) {
        console.error('Create game error:', err.message);
      } else {
        console.error('Create game error:', err);
      }
    }
  };

  // Handle create AI game
  const handleCreateAIGame = async () => {
    setCreatingGame(true);
    setCreateError(null);
    try {
      const data = await gameAPI.createOrJoinGame({ 
        subjects: ['Math', 'Science', 'Sports'],
        is_vs_ai: true,
        ai_difficulty: aiDifficulty
      });
      handleGameFound(data.code);
    } catch (err: unknown) {
      setCreateError('Failed to create AI game.');
      setCreatingGame(false);
      if (err instanceof Error) {
        console.error('Create AI game error:', err.message);
      } else {
        console.error('Create AI game error:', err);
      }
    }
  };

  // Handle join game
  const handleJoinGame = async (e: React.FormEvent) => {
    e.preventDefault();
    setJoinError(null);
    if (!joinCode.trim()) {
      setJoinError('Please enter a game code.');
      return;
    }
    try {
      const data = await gameAPI.createOrJoinGame({ code: joinCode.trim() });
      handleGameFound(data.code);
    } catch (err: unknown) {
      setJoinError('Invalid or unavailable game code.');
      if (err instanceof Error) {
        console.error('Join game error:', err.message);
      } else {
        console.error('Join game error:', err);
      }
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gold-600"></div>
      </div>
    );
  }

  if (user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gold-50 to-white">
        {/* Header */}
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-6">
              <div className="flex items-center">
                <h1 className="text-2xl font-bold text-gold-700">Quizzy Chess</h1>
                <span className="ml-2 text-sm text-gold-500">Think Before You Take</span>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gold-700">
                  Welcome, <span className="font-medium">{user.username}</span>
                </span>
                <span className="text-sm text-gold-500">Rating: {user.rating}</span>
                <div className="flex space-x-2">
                  <Link
                    href="/profile"
                    className="text-sm text-gold-700 hover:text-gold-900"
                  >
                    Profile
                  </Link>
                  <Link
                    href="/leaderboard"
                    className="text-sm text-gold-700 hover:text-gold-900"
                  >
                    Leaderboard
                  </Link>
                  <button
                    onClick={logout}
                    className="text-sm text-gold-700 hover:text-gold-900"
                  >
                    Logout
                  </button>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-gold-900 mb-4">
              Ready to Play Chess with a Twist?
            </h2>
            <p className="text-xl text-gold-700 max-w-3xl mx-auto">
              Challenge your mind with strategic chess moves and educational quizzes. 
              When you capture valuable pieces, you&apos;ll need to answer questions to complete your move!
            </p>
          </div>

          {/* Game Options */}
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 max-w-6xl mx-auto">
            {/* Find Opponent */}
            <div className="bg-white rounded-lg shadow-md p-6 border border-gold-200">
              <div className="text-center">
                <div className="w-16 h-16 bg-gold-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-gold-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gold-900 mb-2">Find Opponent</h3>
                <p className="text-gold-700 mb-4">
                  Match with players of similar skill level using our intelligent matchmaking system.
                </p>
                <button
                  className="w-full bg-gold-500 text-white py-2 px-4 rounded-md hover:bg-gold-600 transition-colors"
                  onClick={() => setShowMatchmaking(true)}
                >
                  Find Game
                </button>
              </div>
            </div>

            {/* Play vs AI */}
            <div className="bg-white rounded-lg shadow-md p-6 border border-gold-200">
              <div className="text-center">
                <div className="w-16 h-16 bg-gold-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-gold-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gold-900 mb-2">Play vs AI</h3>
                <p className="text-gold-700 mb-4">
                  Practice against our intelligent AI opponent with adjustable difficulty levels.
                </p>
                <button
                  className="w-full bg-gold-500 text-white py-2 px-4 rounded-md hover:bg-gold-600 transition-colors"
                  onClick={() => setShowAIOptions(true)}
                >
                  Play vs AI
                </button>
              </div>
            </div>

            {/* Create Game */}
            <div className="bg-white rounded-lg shadow-md p-6 border border-gold-200">
              <div className="text-center">
                <div className="w-16 h-16 bg-gold-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-gold-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gold-900 mb-2">Create Game</h3>
                <p className="text-gold-700 mb-4">
                  Start a new game and share the link with a friend to play together.
                </p>
                <button
                  className="w-full bg-gold-500 text-white py-2 px-4 rounded-md hover:bg-gold-600 transition-colors"
                  onClick={handleCreateGame}
                  disabled={creatingGame}
                >
                  {creatingGame ? 'Creating...' : 'Create Game'}
                </button>
                {createError && <div className="text-red-600 text-sm mt-2">{createError}</div>}
              </div>
            </div>

            {/* Join Game */}
            <div className="bg-white rounded-lg shadow-md p-6 border border-gold-200">
              <div className="text-center">
                <div className="w-16 h-16 bg-gold-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-gold-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12H9m12 0A9 9 0 11 3 12a9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gold-900 mb-2">Join Game</h3>
                <p className="text-gold-700 mb-4">
                  Enter a game code to join a friend&apos;s game.
                </p>
                <form onSubmit={handleJoinGame} className="flex flex-col items-center gap-2">
                  <input
                    type="text"
                    value={joinCode}
                    onChange={e => setJoinCode(e.target.value)}
                    placeholder="Game code"
                    className="w-full px-3 py-2 border border-gold-300 rounded-md focus:outline-none focus:ring-gold-500 focus:border-gold-500"
                  />
                  <button
                    type="submit"
                    className="w-full bg-gold-500 text-white py-2 px-4 rounded-md hover:bg-gold-600 transition-colors"
                  >
                    Join Game
                  </button>
                  {joinError && <div className="text-red-600 text-sm mt-2">{joinError}</div>}
                </form>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="mt-12 bg-white rounded-lg shadow-md p-6 max-w-2xl mx-auto">
            <h3 className="text-lg font-semibold text-gold-900 mb-4 text-center">Your Stats</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-gold-600">{user.games_played}</div>
                <div className="text-sm text-gold-700">Games Played</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-gold-600">{user.games_won}</div>
                <div className="text-sm text-gold-700">Wins</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-gold-600">{user.games_lost}</div>
                <div className="text-sm text-gold-700">Losses</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-gold-600">{user.quiz_correct}</div>
                <div className="text-sm text-gold-700">Quiz Correct</div>
              </div>
            </div>
          </div>
        </main>

        {/* Matchmaking Modal */}
        {showMatchmaking && (
          <MatchmakingModal
            isOpen={showMatchmaking}
            onClose={() => setShowMatchmaking(false)}
            onGameFound={handleGameFound}
          />
        )}

        {/* AI Options Modal */}
        {showAIOptions && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg p-8 max-w-md w-full">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gold-900">Play vs AI</h2>
                <button
                  onClick={() => setShowAIOptions(false)}
                  className="text-gold-400 hover:text-gold-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="mb-6">
                <label className="block text-sm font-medium text-gold-700 mb-2">
                  AI Difficulty
                </label>
                <div className="space-y-2">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="difficulty"
                      value="easy"
                      checked={aiDifficulty === 'easy'}
                      onChange={(e) => setAiDifficulty(e.target.value as 'easy' | 'medium' | 'hard')}
                      className="mr-2"
                    />
                    <span className="text-sm text-gold-700">Easy - Great for beginners</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="difficulty"
                      value="medium"
                      checked={aiDifficulty === 'medium'}
                      onChange={(e) => setAiDifficulty(e.target.value as 'easy' | 'medium' | 'hard')}
                      className="mr-2"
                    />
                    <span className="text-sm text-gold-700">Medium - Balanced challenge</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="difficulty"
                      value="hard"
                      checked={aiDifficulty === 'hard'}
                      onChange={(e) => setAiDifficulty(e.target.value as 'easy' | 'medium' | 'hard')}
                      className="mr-2"
                    />
                    <span className="text-sm text-gold-700">Hard - Expert level</span>
                  </label>
                </div>
              </div>

              <div className="flex space-x-3">
                <button
                  onClick={() => setShowAIOptions(false)}
                  className="flex-1 bg-gold-300 text-gold-700 py-2 px-4 rounded-md hover:bg-gold-400 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateAIGame}
                  disabled={creatingGame}
                  className="flex-1 bg-gold-500 text-white py-2 px-4 rounded-md hover:bg-gold-600 transition-colors disabled:opacity-50"
                >
                  {creatingGame ? 'Creating...' : 'Start AI Game'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gold-50 to-white">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gold-700">Quizzy Chess</h1>
              <span className="ml-2 text-sm text-gold-500">Think Before You Take</span>
            </div>
            <div className="flex space-x-4">
              <button
                onClick={() => {
                  setAuthMode('login');
                  setShowAuth(true);
                }}
                className="text-sm text-gold-700 hover:text-gold-900"
              >
                Sign In
              </button>
              <button
                onClick={() => {
                  setAuthMode('register');
                  setShowAuth(true);
                }}
                className="bg-gold-600 text-white px-4 py-2 rounded-md text-sm hover:bg-gold-700"
              >
                Sign Up
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <h2 className="text-5xl font-bold text-gold-900 mb-6">
            Chess + Education = 
            <span className="text-gold-600"> Quizzy Chess</span>
          </h2>
          <p className="text-xl text-gold-700 max-w-3xl mx-auto mb-8">
            Experience the ultimate fusion of strategic chess gameplay and educational quizzes. 
            Every capture of a valuable piece requires you to answer a subject-based question to complete your move.
          </p>
          <div className="flex justify-center space-x-4">
            <button
              onClick={() => {
                setAuthMode('register');
                setShowAuth(true);
              }}
              className="bg-gold-600 text-white px-8 py-3 rounded-md text-lg font-medium hover:bg-gold-700 transition-colors"
            >
              Get Started
            </button>
            <Link
              href="/leaderboard"
              className="border border-gold-600 text-gold-600 px-8 py-3 rounded-md text-lg font-medium hover:bg-gold-50 transition-colors"
            >
              View Leaderboard
            </Link>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto mb-12">
          <div className="text-center">
            <div className="w-16 h-16 bg-gold-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gold-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gold-900 mb-2">Smart Learning</h3>
            <p className="text-gold-700">
              Answer questions in Math, Science, and Sports while playing chess
            </p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-gold-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gold-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gold-900 mb-2">Real-time Multiplayer</h3>
            <p className="text-gold-700">
              Play against friends or find opponents with our matchmaking system
            </p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-gold-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gold-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gold-900 mb-2">ELO Rating</h3>
            <p className="text-gold-700">
              Track your progress with a competitive rating system
            </p>
          </div>
        </div>
      </main>

      {/* Auth Modal */}
      {showAuth && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-gold-900">
                {authMode === 'login' ? 'Sign In' : 'Create Account'}
              </h2>
              <button
                onClick={() => setShowAuth(false)}
                className="text-gold-400 hover:text-gold-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <AuthForm
              mode={authMode}
              onSuccess={() => setShowAuth(false)}
            />
            <div className="mt-4 text-center">
              <button
                onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
                className="text-sm text-gold-600 hover:text-gold-500"
              >
                {authMode === 'login' 
                  ? "Don't have an account? Sign up" 
                  : "Already have an account? Sign in"
                }
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
