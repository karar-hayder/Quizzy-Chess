from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):

    REQUIRED_FIELDS = []
    rating = models.IntegerField(default=1200)
    games_played = models.IntegerField(default=0)
    games_won = models.IntegerField(default=0)
    games_lost = models.IntegerField(default=0)
    games_drawn = models.IntegerField(default=0)
    quiz_correct = models.IntegerField(default=0)
    quiz_attempted = models.IntegerField(default=0)
    preferred_subject = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="User's default subject for quiz questions",
    )
