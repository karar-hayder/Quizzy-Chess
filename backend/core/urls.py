from django.urls import path

from .views import (
    GameAnalysisView,
    GameCreateJoinView,
    GameDetailView,
    HealthCheckView,
    QuizAnswerView,
    QuizQuestionView,
    matchmaking_status,
)

urlpatterns = [
    path("game/", GameCreateJoinView.as_view(), name="game-create-join"),
    path("game/<str:code>/", GameDetailView.as_view(), name="game-detail"),
    path("quiz/", QuizQuestionView.as_view(), name="quiz-question"),
    path("move/<int:move_id>/quiz/", QuizAnswerView.as_view(), name="quiz-answer"),
    path("game/<str:code>/analysis/", GameAnalysisView.as_view(), name="game-analysis"),
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("matchmaking/status/", matchmaking_status, name="matchmaking-status"),
]
