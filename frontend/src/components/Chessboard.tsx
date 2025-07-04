'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Chess, Square } from 'chess.js';

interface ChessboardProps {
  fen: string;
  onMove: (from: string, to: string, piece: string, captured?: string, promotion?: string) => void;
  lastMove?: { from: string; to: string };
  isMyTurn?: boolean;
  disabled?: boolean;
  onAnalysisClick?: () => void;
  blockedMoves?: string[];
}

const DEFAULT_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

// Board colors
const LIGHT_SQUARE_COLOR = '#f0d9b5'; // classic beige
const DARK_SQUARE_COLOR = '#b58863'; // classic brown
const HIGHLIGHT_COLOR = 'rgba(255, 215, 0, 0.3)'; // subtle gold for last move
const LEGAL_MOVE_COLOR = 'rgba(0, 255, 0, 0.3)'; // subtle green for legal moves

const Chessboard: React.FC<ChessboardProps> = ({
  fen,
  onMove,
  lastMove,
  isMyTurn = false,
  disabled = false,
  onAnalysisClick,
  blockedMoves = [],
}) => {
  const [selectedSquare, setSelectedSquare] = useState<string | null>(null);
  const [legalMoves, setLegalMoves] = useState<string[]>([]);
  const [chess, setChess] = useState<Chess | null>(null);
  const [loading, setLoading] = useState(true);
  const boardRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const initChess = async () => {
      try {
        const { Chess } = await import('chess.js');
        const validFen = getValidFen(fen);
        const chessInstance = new Chess(validFen);
        setChess(chessInstance);
        setLoading(false);
      } catch (error) {
        console.error('Failed to initialize chess:', error);
        setLoading(false);
      }
    };
    
    initChess();
  }, [fen]);

  const getValidFen = (fenString: string) => {
    if (!fenString || fenString.trim() === '') return DEFAULT_FEN;
    try {
      // Check if FEN has 6 parts
      const parts = fenString.split(' ');
      if (parts.length !== 6) return DEFAULT_FEN;
      return fenString;
    } catch {
      return DEFAULT_FEN;
    }
  };

  const updateLegalMoves = (chessInstance: Chess, square: string) => {
    if (!chessInstance) return;
    try {
      const moves = chessInstance.moves({ square: square as unknown as Square, verbose: true });
      setLegalMoves(moves.map((move: { to: string }) => move.to));
    } catch (error) {
      console.error('Failed to get legal moves:', error);
      setLegalMoves([]);
    }
  };

  const handleSquareClick = (square: string) => {
    if (disabled || !isMyTurn) return;
    if (selectedSquare) {
      try {
        const piece = chess?.get(selectedSquare as unknown as Square)?.type;
        const isPawn = piece === 'p';
        const isPromotionRank =
          (isPawn && chess?.turn() === 'w' && square[1] === '8') ||
          (isPawn && chess?.turn() === 'b' && square[1] === '1');
        const moveStr = `${selectedSquare}${square}`;
        if (blockedMoves.includes(moveStr)) {
          setSelectedSquare(null);
          setLegalMoves([]);
          return;
        }
        let promotion: string | undefined = undefined;
        if (isPawn && isPromotionRank) {
          promotion = 'q';
        }
        const move = chess?.move({
          from: selectedSquare,
          to: square,
          ...(promotion ? { promotion } : {}),
        });
        if (move) {
          setSelectedSquare(null);
          setLegalMoves([]);
          onMove(move.from, move.to, move.piece, move.captured, promotion);
        } else {
          setSelectedSquare(null);
          setLegalMoves([]);
        }
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
      } catch (err) {
        setSelectedSquare(null);
        setLegalMoves([]);
      }
    } else {
      setSelectedSquare(square);
      updateLegalMoves(chess as Chess, square);
    }
  };

  const getSquareColor = (square: string) => {
    const file = square.charCodeAt(0) - 97;
    const rank = parseInt(square[1]) - 1;
    return (file + rank) % 2 === 0 ? LIGHT_SQUARE_COLOR : DARK_SQUARE_COLOR;
  };

  const getPieceSymbol = (piece: string) => {
    const symbols: { [key: string]: string } = {
      'k': '♔', 'q': '♕', 'r': '♖', 'b': '♗', 'n': '♘', 'p': '♙',
      'K': '♚', 'Q': '♛', 'R': '♜', 'B': '♝', 'N': '♞', 'P': '♟'
    };
    return symbols[piece] || piece;
  };

  const renderSquare = (square: string) => {
    if (!chess) return null;
    
    const piece = chess.get(square as unknown as Square);
    const isSelected = selectedSquare === square;
    const isLegalMove = legalMoves.includes(square);
    const isLastMove = lastMove && (lastMove.from === square || lastMove.to === square);
    const isBlocked = selectedSquare && blockedMoves.includes(`${selectedSquare}${square}`);
    
    const bgColor = getSquareColor(square);

    return (
      <div
        key={square}
        className="w-16 h-16 flex items-center justify-center cursor-pointer border border-gray-400"
        style={{
          backgroundColor: isBlocked
            ? 'rgba(255,0,0,0.3)'
            : isSelected
            ? HIGHLIGHT_COLOR
            : isLegalMove
            ? LEGAL_MOVE_COLOR
            : bgColor,
          border: isLastMove ? `2px solid ${HIGHLIGHT_COLOR}` : '1px solid #8B4513',
          transition: 'background 0.2s',
        }}
        onClick={() => handleSquareClick(square)}
      >
        {piece && (
          <span className={`text-3xl ${piece.color === 'w' ? 'text-white' : 'text-black'}`}>
            {getPieceSymbol(piece.type)}
          </span>
        )}
      </div>
    );
  };

  const renderBoard = () => {
    const squares = [];
    for (let rank = 8; rank >= 1; rank--) {
      for (let file = 0; file < 8; file++) {
        const square = String.fromCharCode(97 + file) + rank;
        squares.push(renderSquare(square));
      }
    }
    return squares;
  };

  if (loading || !chess) {
    return (
      <div className="flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center">
      <div className="grid grid-cols-8 gap-0 border-2 border-gray-800" ref={boardRef}>
        {renderBoard()}
      </div>
      <div className="mt-4 flex items-center gap-4">
        <div className="text-sm text-gray-600">
          {chess.turn() === 'w' ? 'White to move' : 'Black to move'}
        </div>
        {onAnalysisClick && (
          <button
            onClick={onAnalysisClick}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors text-sm"
          >
            Game Analysis
          </button>
        )}
      </div>
    </div>
  );
};

export default Chessboard; 