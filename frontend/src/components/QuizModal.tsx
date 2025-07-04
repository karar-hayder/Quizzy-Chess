'use client';

import React, { useState, useEffect, useCallback } from 'react';

interface QuizModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAnswer: (correct: boolean) => void;
  moveId: number;
  subject: string;
  questionId: number;
  quizData?: {
    question: string;
    choices: string[];
    correct: string;
    explanation?: string;
  };
  quizResult?: QuizResult | null;
}

export interface QuizResult {
  correct: boolean;
  explanation?: string;
}

export default function QuizModal({ 
  isOpen, 
  onClose, 
  onAnswer, 
  moveId, 
  subject, 
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  questionId,
  quizData,
  quizResult 
}: QuizModalProps) {
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState(30); // 30 second timer

  const handleTimeout = useCallback(() => {
    // Send timeout answer via WebSocket
    const ws = (window as unknown as { gameWebSocket: WebSocket }).gameWebSocket;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'quiz_answer',
        payload: {
          answer: 'TIMEOUT',
          move_number: moveId
        }
      }));
    }
    // The backend will handle the timeout and send appropriate response
  }, [moveId]);

  useEffect(() => {
    if (isOpen) {
      setTimeLeft(30);
      setSelectedAnswer(null);
      setError(null);
      setIsSubmitting(false);
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && timeLeft > 0 && !quizResult) {
      const timer = setTimeout(() => {
        setTimeLeft(prev => prev - 1);
      }, 1000);

      return () => clearTimeout(timer);
    } else if (timeLeft === 0 && !quizResult) {
      // Time's up - answer is wrong
      handleTimeout();
    }
  }, [isOpen, timeLeft, quizResult, handleTimeout]);

  const handleSubmit = async () => {
    if (!selectedAnswer || !quizData) return;

    setIsSubmitting(true);
    setError(null);

    try {
      // Send quiz answer via WebSocket instead of REST API
      const ws = (window as unknown as { gameWebSocket: WebSocket }).gameWebSocket;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'quiz_answer',
          payload: {
            answer: selectedAnswer,
            move_number: moveId
          }
        }));
        
        // Don't check answer locally - wait for backend response
        // The backend will send a move message if correct, or quiz_failed if incorrect
        
      } else {
        throw new Error('WebSocket connection not available');
      }

    } catch (err: unknown) {
      if (err instanceof Error) {
        console.error('Failed to submit quiz answer:', err);
        setError('Failed to submit answer. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting && quizResult === null) {
      // If they close without answering, it's wrong
      onAnswer(false);
    }
    onClose();
  };

  const getOptionText = (option: string) => {
    switch (option) {
      case 'A': return quizData?.choices[0];
      case 'B': return quizData?.choices[1];
      case 'C': return quizData?.choices[2];
      case 'D': return quizData?.choices[3];
      default: return '';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Quiz Challenge</h2>
            <p className="text-sm text-gray-600">Subject: {subject}</p>
          </div>
          <div className="flex items-center space-x-4">
            {/* Timer */}
            <div className={`text-lg font-mono ${
              timeLeft <= 10 ? 'text-red-600' : 'text-gray-600'
            }`}>
              {Math.floor(timeLeft / 60)}:{(timeLeft % 60).toString().padStart(2, '0')}
            </div>
            {!isSubmitting && quizResult === null && (
              <button
                onClick={handleClose}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {!quizData ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading question...</p>
            </div>
          ) : (
            <>
              {/* Question */}
              <div className="mb-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  {quizData.question}
                </h3>
              </div>

              {/* Answer Options */}
              {quizResult === null && (
                <div className="space-y-3 mb-6">
                  {['A', 'B', 'C', 'D'].map((option) => (
                    <button
                      key={option}
                      onClick={() => setSelectedAnswer(option)}
                      disabled={isSubmitting}
                      className={`w-full p-4 text-left rounded-lg border-2 transition-colors ${
                        selectedAnswer === option
                          ? 'border-indigo-500 bg-indigo-50'
                          : 'border-gray-200 hover:border-gray-300'
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      <div className="flex items-center">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center mr-3 ${
                          selectedAnswer === option
                            ? 'bg-indigo-600 text-white'
                            : 'bg-gray-200 text-gray-700'
                        }`}>
                          {option}
                        </div>
                        <span className="text-gray-900">{getOptionText(option)}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Result */}
              {quizResult !== null && (
                <div className="text-center py-6">
                  {quizResult?.correct ? (
                    <div className="text-green-600">
                      <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <h3 className="text-xl font-semibold mb-2">Correct!</h3>
                      <p className="text-green-600">Your move will be executed.</p>
                    </div>
                  ) : (
                    <div className="text-red-600">
                      <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <h3 className="text-xl font-semibold mb-2">Incorrect!</h3>
                      <p className="text-red-600">Your move will be cancelled.</p>
                    </div>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              {quizResult === null && (
                <div className="space-y-3">
                  <button
                    onClick={handleSubmit}
                    disabled={!selectedAnswer || isSubmitting}
                    className="w-full bg-indigo-600 text-white py-3 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isSubmitting ? (
                      <div className="flex items-center justify-center">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Submitting...
                      </div>
                    ) : (
                      'Submit Answer'
                    )}
                  </button>
                </div>
              )}
            </>
          )}

          {/* Info */}
          <div className="mt-6 text-xs text-gray-500 text-center">
            <p>You must answer correctly to complete your capture move</p>
            <p>Time limit: 30 seconds</p>
          </div>
        </div>
      </div>
    </div>
  );
} 