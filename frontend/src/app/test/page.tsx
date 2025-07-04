'use client';

import React, { useEffect, useState } from 'react';
import { authAPI } from '@/utils/api';

export default function TestPage() {
  const [leaderboard, setLeaderboard] = useState<{id:number;username:string;rating:number}[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [frontendUrl, setFrontendUrl] = useState<string>('Loading...');

  useEffect(() => {
    testAPI();
    // Set frontend URL on client side only
    setFrontendUrl(window.location.origin);
  }, []);

  const testAPI = async () => {
    try {
      setLoading(true);
      console.log('Testing API call...');
      const data = await authAPI.getLeaderboard();
      console.log('API response:', data);
      setLeaderboard(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        console.error('API error:', err);
        setError(err.message || 'API call failed');
      } else {
        console.error('API error:', err);
        setError('An unexpected error occurred');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-offWhite p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8 text-deepCharcoal">API Test Page</h1>
        
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 text-deepCharcoal">Leaderboard API Test</h2>
          
          {loading && (
            <div className="text-matteGold">Loading...</div>
          )}
          
          {error && (
            <div className="text-red-600 mb-4">
              Error: {error}
            </div>
          )}
          
          {leaderboard.length > 0 && (
            <div>
              <div className="text-green-600 mb-4">✅ API call successful!</div>
              <div className="text-sm text-slateGray mb-2">
                Found {leaderboard.length} players
              </div>
              <div className="space-y-2">
                {leaderboard.slice(0, 3).map((player: {id:number;username:string;rating:number}) => (
                  <div key={player.id} className="p-2 bg-gray-50 rounded">
                    {player.username} - Rating: {player.rating}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          <button
            onClick={testAPI}
            className="mt-4 bg-matteGold text-deepCharcoal px-4 py-2 rounded hover:bg-gold"
          >
            Test Again
          </button>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4 text-deepCharcoal">API Configuration</h2>
          <div className="text-sm space-y-2">
            <div>Base URL: {process.env.NEXT_PUBLIC_API_URL || 'http://localhost/api'}</div>
            <div>Environment: {process.env.NODE_ENV}</div>
            <div>Frontend URL: {frontendUrl}</div>
          </div>
        </div>
      </div>
    </div>
  );
} 