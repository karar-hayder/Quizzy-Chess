from rest_framework import serializers

from users.serializers import UserSerializer

from .models import Game, Move, QuizQuestion


class QuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = "__all__"


class MoveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Move
        fields = "__all__"


class GameSerializer(serializers.ModelSerializer):
    moves = MoveSerializer(many=True, read_only=True)
    player_white = UserSerializer(read_only=True)
    player_black = UserSerializer(read_only=True)
    analysis = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = "__all__"

    def get_analysis(self, obj):
        if obj.analysis_status == "completed":
            try:
                analysis = obj.analysis
                if analysis:
                    return {"overall": analysis.overall, "per_move": analysis.per_move}
            except Exception:
                pass
        return None
