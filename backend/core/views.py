import json
import random
import asyncio

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404, render
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.tasks import (
    generate_quizs_in_advance,
    update_game_cache_and_broadcast_task,
    update_user_quiz_stats,
)
from users.models import CustomUser

from .models import Game, GameAnalysis, Move, QuizQuestion
from .serializers import GameSerializer, MoveSerializer, QuizQuestionSerializer
from .matchmaking import MatchmakingService


class GameCreateJoinView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        code = request.data.get("code")
        subject_list = request.data.get("subjects", ["Math"])
        if isinstance(subject_list, str):
            try:
                subject_list = json.loads(subject_list)
            except Exception:
                subject_list = [subject_list]
        subject_list = subject_list[:3]
        if code:
            game = get_object_or_404(Game, code=code)
            updated = False
            if not game.player_black and game.player_white != request.user:
                game.player_black = request.user
                game.status = "active"
                game.save()
                updated = True
                print(game.status)
                generate_quizs_in_advance.delay(game.id, 5, subject_list)
            channel_layer = get_channel_layer()
            update_game_cache_and_broadcast_task.delay(game.id, game.code)
            return Response({"spectator": not updated, **GameSerializer(game).data})
        is_vs_ai = request.data.get("is_vs_ai", False)
        ai_difficulty = request.data.get("ai_difficulty", "easy")
        if is_vs_ai:
            game = Game.objects.create(
                player_white=request.user,
                player_black=None,
                subjects=subject_list,
                is_vs_ai=True,
                ai_difficulty=ai_difficulty,
                status="active",
            )
            generate_quizs_in_advance.delay(game.id, 5, subject_list)
        else:
            game = Game.objects.create(
                player_white=request.user,
                subjects=subject_list,
                is_vs_ai=False,
                ai_difficulty="",
            )
        return Response({"spectator": False, **GameSerializer(game).data})


class GameDetailView(generics.RetrieveAPIView):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "code"


class QuizQuestionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        subject = request.query_params.get("subject", "Math")
        questions = QuizQuestion.objects.filter(subject=subject)
        if not questions.exists():
            return Response({"detail": "No questions available."}, status=404)
        question = random.choice(list(questions))
        return Response(QuizQuestionSerializer(question).data)


class QuizAnswerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, move_id):
        move = get_object_or_404(Move, id=move_id, quiz_required=True)
        answer = request.data.get("answer")
        question_id = request.data.get("question_id")
        question = get_object_or_404(QuizQuestion, id=question_id)
        correct = answer == question.correct_option
        move.quiz_correct = correct
        move.save()
        update_user_quiz_stats.delay(request.user.id, correct)
        return Response({"correct": correct})


class GameAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, code):
        try:
            game = Game.objects.get(code=code)
        except Game.DoesNotExist:
            return Response(
                {"detail": "Game not found."}, status=status.HTTP_404_NOT_FOUND
            )
        user = request.user
        try:
            analysis = game.analysis
        except GameAnalysis.DoesNotExist:
            return Response(
                {"detail": "Analysis not available yet."},
                status=status.HTTP_202_ACCEPTED,
            )
        return Response(
            {
                "overall": analysis.overall,
                "per_move": analysis.per_move,
            }
        )


class HealthCheckView(APIView):
    permission_classes = []  # No authentication required for health checks

    def get(self, request):
        return Response({"status": "healthy", "service": "chess-backend"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def matchmaking_status(request):
    """Get current matchmaking queue status."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            matchmaking_service = MatchmakingService()
            status_data = loop.run_until_complete(
                matchmaking_service.get_queue_status()
            )
            return Response(status_data)
        finally:
            loop.close()
    except Exception as e:
        return Response(
            {"error": "Failed to get matchmaking status"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
