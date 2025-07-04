from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import logging

from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    games = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        exclude = ["password"]

    def get_games(self, obj):
        logger = logging.getLogger(__name__)
        games = obj.games_white.all() | obj.games_black.all()
        games = games.order_by("-created_at")
        result = []
        for game in games:
            try:
                computed_result = None
                if game.status == "finished":
                    if game.winner is None:
                        computed_result = "draw"
                    elif game.winner == game.player_white:
                        computed_result = "white_win"
                    elif game.winner == game.player_black:
                        computed_result = "black_win"
                analysis_data = None
                if (
                    hasattr(game, "analysis_status")
                    and game.analysis_status == "completed"
                ):
                    try:
                        from core.models import GameAnalysis

                        analysis = GameAnalysis.objects.filter(game=game).first()
                        if analysis:
                            analysis_data = {
                                "overall": analysis.overall,
                                "per_move": analysis.per_move,
                            }
                    except Exception as e:
                        logger.error(f"Error getting analysis for game {game.id}: {e}")

                result.append(
                    {
                        "id": getattr(game, "id", None),
                        "code": getattr(game, "code", None),
                        "status": getattr(game, "status", None),
                        "result": computed_result,
                        "fen": getattr(game, "fen", None),
                        "subject": getattr(game, "subject", None),
                        "is_vs_ai": getattr(game, "is_vs_ai", None),
                        "ai_difficulty": getattr(game, "ai_difficulty", None),
                        "score": getattr(game, "score", None),
                        "analysis_status": getattr(game, "analysis_status", None),
                        "analysis": analysis_data,
                        "winner": (
                            {
                                "id": getattr(game.winner, "id", None),
                                "username": getattr(game.winner, "username", None),
                                "rating": getattr(game.winner, "rating", None),
                            }
                            if getattr(game, "winner", None)
                            else None
                        ),
                        "created_at": getattr(game, "created_at", None),
                        "updated_at": getattr(game, "updated_at", None),
                        "player_white": (
                            {
                                "id": getattr(game.player_white, "id", None),
                                "username": getattr(
                                    game.player_white, "username", None
                                ),
                                "rating": getattr(game.player_white, "rating", None),
                            }
                            if getattr(game, "player_white", None)
                            else None
                        ),
                        "player_black": (
                            {
                                "id": getattr(game.player_black, "id", None),
                                "username": getattr(
                                    game.player_black, "username", None
                                ),
                                "rating": getattr(game.player_black, "rating", None),
                            }
                            if getattr(game, "player_black", None)
                            else None
                        ),
                    }
                )
            except Exception as e:
                logger.error(f"Error serializing game for user profile: {e}")
        return result


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "username",
            "email",
            "password",
            "rating",
            "games_played",
            "games_won",
            "games_lost",
            "games_drawn",
            "quiz_correct",
            "quiz_attempted",
            "preferred_subject",
        ]

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            rating=validated_data.get("rating", 1200),
            games_played=validated_data.get("games_played", 0),
            games_won=validated_data.get("games_won", 0),
            games_lost=validated_data.get("games_lost", 0),
            games_drawn=validated_data.get("games_drawn", 0),
            quiz_correct=validated_data.get("quiz_correct", 0),
            quiz_attempted=validated_data.get("quiz_attempted", 0),
            preferred_subject=validated_data.get("preferred_subject", ""),
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = CustomUser.USERNAME_FIELD

    def validate(self, attrs):
        data = super().validate(
            {"username": attrs.get("username"), "password": attrs.get("password")}
        )
        return data

    class Meta:
        model = CustomUser
        fields = ["username", "password"]
