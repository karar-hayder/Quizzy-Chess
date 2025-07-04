'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useUser } from '@/context/UserContext';
import { gameAPI } from '@/utils/api';

interface MatchmakingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGameFound: (gameCode: string) => void;
}

interface MatchmakingStatus {
  queue_length: number;
  active_searches: number;
}

export default function MatchmakingModal({ isOpen, onClose, onGameFound }: MatchmakingModalProps) {
  const { user } = useUser();
  const [isSearching, setIsSearching] = useState(false);
  const [searchTime, setSearchTime] = useState(0);
  const [status, setStatus] = useState<MatchmakingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const searchTimerRef = useRef<NodeJS.Timeout | null>(null);
  const statusTimerRef = useRef<NodeJS.Timeout | null>(null);

  const winRate = user ? (user.games_played > 0 ? ((user.games_won / user.games_played) * 100).toFixed(1) : '0') : '0';
  const quizAccuracy = user ? (user.quiz_attempted > 0 ? ((user.quiz_correct / user.quiz_attempted) * 100).toFixed(1) : '0') : '0';

  useEffect(() => {
    if (isOpen) {
      fetchMatchmakingStatus();
      statusTimerRef.current = setInterval(fetchMatchmakingStatus, 5000);
    }

    return () => {
      if (statusTimerRef.current) {
        clearInterval(statusTimerRef.current);
      }
    };
  }, [isOpen]);

  useEffect(() => {
    if (isSearching) {
      searchTimerRef.current = setInterval(() => {
        setSearchTime(prev => prev + 1);
      }, 1000);
    } else {
      if (searchTimerRef.current) {
        clearInterval(searchTimerRef.current);
        searchTimerRef.current = null;
      }
      setSearchTime(0);
    }

    return () => {
      if (searchTimerRef.current) {
        clearInterval(searchTimerRef.current);
      }
    };
  }, [isSearching]);

  const fetchMatchmakingStatus = async () => {
    try {
      const data = await gameAPI.getMatchmakingStatus();
      setStatus(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        console.error('Failed to fetch matchmaking status:', err.message);
      } else {
        console.error('Failed to fetch matchmaking status:', err);
      }
    }
  };

  const startSearch = () => {
    if (!user) return;

    setIsSearching(true);
    setError(null);

    const token = localStorage.getItem('access_token');
    if (!token) {
      setError('Authentication required');
      setIsSearching(false);
      return;
    }

    const wsUrl = `ws://localhost/ws/matchmaking/?token=${token}`;
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      console.log('Matchmaking WebSocket connected');
      wsRef.current?.send(JSON.stringify({
        type: 'find_game',
        payload: {}
      }));
    };

    wsRef.current.onmessage = (event: MessageEvent) => {
      try {
        const data: { type: string; payload: Record<string, unknown> } = JSON.parse(event.data);
        console.log('Matchmaking message received:', data);

        switch (data.type) {
          case 'search_started':
            console.log('Search started with ID:', data.payload.search_id);
            break;
          
          case 'game_found':
            console.log('Game found event received:', data.payload);
            console.log('Game code:', (data.payload as { game: { code: string } }).game.code);
            setIsSearching(false);
            onGameFound((data.payload as { game: { code: string } }).game.code);
            break;
          
          case 'error':
            console.error('Matchmaking error:', data.payload.reason);
            setError(data.payload.reason as string);
            setIsSearching(false);
            break;
          
          case 'pong':
            console.log('Pong received');
            break;
          
          default:
            console.warn('Unknown matchmaking message type:', data.type);
        }
      } catch (err: unknown) {
        if (err instanceof Error) {
          console.error('Failed to parse WebSocket message:', err.message);
        } else {
          console.error('Failed to parse WebSocket message:', err);
        }
      }
    };

    wsRef.current.onerror = (error: Event) => {
      console.error('WebSocket error:', error);
      setError('Connection error. Please try again.');
      setIsSearching(false);
    };

    wsRef.current.onclose = (event: CloseEvent) => {
      console.log('Matchmaking WebSocket disconnected. Code:', event.code, 'Reason:', event.reason);
      if (isSearching) {
        setError('Connection lost. Please try again.');
        setIsSearching(false);
      }
    };
  };

  const cancelSearch = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'cancel_search',
        payload: {}
      }));
    }
    setIsSearching(false);
    setError(null);
  };

  const handleClose = () => {
    if (isSearching) {
      cancelSearch();
    }
    if (wsRef.current) {
      wsRef.current.close();
    }
    onClose();
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Find Opponent</h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* User Stats */}
          {user && (
            <div className="mb-6 bg-gray-50 rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-700 mb-3">Your Stats</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-2xl font-bold text-indigo-600">{user.rating}</div>
                  <div className="text-gray-600">Rating</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-600">{user.games_played}</div>
                  <div className="text-gray-600">Games</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-600">{winRate}%</div>
                  <div className="text-gray-600">Win Rate</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-purple-600">{quizAccuracy}%</div>
                  <div className="text-gray-600">Quiz Accuracy</div>
                </div>
              </div>
            </div>
          )}

          {/* Queue Status */}
          {status && (
            <div className="mb-6 bg-blue-50 rounded-lg p-4">
              <h3 className="text-sm font-medium text-blue-700 mb-2">Queue Status</h3>
              <div className="text-sm text-blue-600">
                {status.queue_length} players searching • {status.active_searches} active searches
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Search Status */}
          {isSearching && (
            <div className="mb-6 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Searching for opponent...</h3>
              <p className="text-sm text-gray-600 mb-4">
                Time elapsed: {formatTime(searchTime)}
              </p>
              <div className="text-xs text-gray-500">
                Finding players with similar skill level...
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="space-y-3">
            {!isSearching ? (
              <button
                onClick={startSearch}
                disabled={!user}
                className="w-full bg-indigo-600 text-white py-3 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {!user ? 'Please log in to play' : 'Find Opponent'}
              </button>
            ) : (
              <button
                onClick={cancelSearch}
                className="w-full bg-red-600 text-white py-3 px-4 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors"
              >
                Cancel Search
              </button>
            )}
          </div>

          {/* Info */}
          <div className="mt-6 text-xs text-gray-500 text-center">
            <p>Players are matched based on rating and win/loss ratio</p>
            <p>Search criteria become more relaxed over time</p>
          </div>
        </div>
      </div>
    </div>
  );
} 