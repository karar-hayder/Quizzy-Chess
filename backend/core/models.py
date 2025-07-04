import random
import string
from uuid import uuid4

from django.contrib.postgres.fields import ArrayField
from django.db import models

from users.models import CustomUser


def generate_game_code(length=12):
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class Game(models.Model):
    STATUS_CHOICES = [
        ("waiting", "Waiting for opponent"),
        ("active", "Active"),
        ("finished", "Finished"),
    ]
    ANALYSIS_STATUS_CHOICES = [
        ("pending", "Pending Analysis"),
        ("in_progress", "Analysis In Progress"),
        ("completed", "Analysis Completed"),
        ("failed", "Analysis Failed"),
    ]
    code = models.CharField(
        max_length=30, unique=True, default=generate_game_code, db_index=True
    )
    player_white = models.ForeignKey(
        CustomUser, related_name="games_white", on_delete=models.CASCADE
    )
    player_black = models.ForeignKey(
        CustomUser,
        related_name="games_black",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    subjects = models.JSONField(default=list, blank=True)  # Up to 3 subjects as a list
    fen = models.CharField(max_length=100, default=STARTING_FEN)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="waiting")
    analysis_status = models.CharField(
        max_length=20, choices=ANALYSIS_STATUS_CHOICES, default="pending"
    )
    winner = models.ForeignKey(
        CustomUser,
        related_name="games_won_as_winner",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_vs_ai = models.BooleanField(default=False)
    ai_difficulty = models.CharField(
        max_length=10,
        choices=[("easy", "Easy"), ("normal", "Normal")],
        default="easy",
        blank=True,
    )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_game_code(random.randint(10, 30))
        super().save(*args, **kwargs)


class Move(models.Model):
    uuid = models.UUIDField(default=uuid4, editable=False, unique=True, db_index=True)
    game = models.ForeignKey(Game, related_name="moves", on_delete=models.CASCADE)
    player = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, null=True, blank=True
    )
    from_square = models.CharField(max_length=5)
    to_square = models.CharField(max_length=5)
    piece = models.CharField(max_length=10)
    captured_piece = models.CharField(max_length=10, blank=True, null=True)
    move_number = models.IntegerField()
    fen_after = models.CharField(max_length=100)
    quiz_required = models.BooleanField(default=False)
    quiz_correct = models.BooleanField(null=True, blank=True)
    quiz_data = models.JSONField(
        default=dict, blank=True, null=True
    )  # Store quiz question details
    created_at = models.DateTimeField(auto_now_add=True)
    fen_before = models.CharField(
        max_length=100, blank=True, null=True
    )  # FEN before the move


class QuizQuestion(models.Model):
    SUBJECT_CHOICES = [
        ("Math", "Math"),
        ("Science", "Science"),
        ("Sports", "Sports"),
    ]
    avg_elo = models.IntegerField(
        default=1200, help_text="Average Elo of players for whom this quiz is intended"
    )
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES)
    question = models.TextField()
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200)
    option_d = models.CharField(max_length=200)
    correct_option = models.CharField(
        max_length=1, choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")]
    )
    explanation = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"[{self.subject}] {self.question[:40]}..."


class GameAnalysis(models.Model):
    game = models.OneToOneField(Game, related_name="analysis", on_delete=models.CASCADE)
    overall = models.JSONField(
        default=dict, blank=True
    )  # e.g. summary, blunders, accuracy
    per_move = models.JSONField(
        default=list, blank=True
    )  # list of dicts: move_number, best_move, evaluation, comment
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
