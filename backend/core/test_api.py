import asyncio
import json
import logging
from unittest.mock import patch

import pytest
from channels.db import database_sync_to_async
from channels.testing import ChannelsLiveServerTestCase, WebsocketCommunicator
from django.conf import settings
from django.db import transaction
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from backend.asgi import application
from users.models import CustomUser

from .consumers import get_quiz_question, get_redis
from .models import Game, Move, QuizQuestion
from .tasks import generate_quizs_in_advance

print("TEST DB:", settings.DATABASES)


class CoreAPITests(TransactionTestCase):
    def setUp(self):
        patcher1 = patch("core.tasks.generate_quizs_in_advance.delay", autospec=True)
        patcher2 = patch("core.tasks.analyze_game_task.delay", autospec=True)
        patcher3 = patch("core.tasks.run_ai_move_task.delay", autospec=True)
        self.mock_generate_quizs = patcher1.start()
        self.mock_analyze_game = patcher2.start()
        self.mock_run_ai_move = patcher3.start()
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        self.addCleanup(patcher3.stop)
        with transaction.atomic():
            CustomUser.objects.all().delete()
            self.user1 = CustomUser.objects.create_user(
                username="player1", password="pass1"
            )
            self.user2 = CustomUser.objects.create_user(
                username="player2", password="pass2"
            )
            self.user3 = CustomUser.objects.create_user(
                username="spectator", password="spectatorpass"
            )
            self.quiz = QuizQuestion.objects.create(
                subject="Math",
                question="2+2=?",
                option_a="3",
                option_b="4",
                option_c="5",
                option_d="6",
                correct_option="B",
                explanation="2+2=4",
            )
            self.game_url = reverse("game-create-join")
            self.quiz_url = reverse("quiz-question")
            self.client = Client()

    def authenticate(self, user):
        login = self.client.post(
            reverse("token_obtain_pair"),
            {
                "username": user.username,
                "password": (
                    "pass1"
                    if user == self.user1
                    else ("pass2" if user == self.user2 else "spectatorpass")
                ),
            },
        )
        token = login.json()["access"]
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    @pytest.mark.asyncio
    def test_game_creation_and_joining(self):
        self.authenticate(self.user1)
        code = self.client.post(
            reverse("game-create-join"), {"subjects": ["Math"]}
        ).data["code"]
        self.authenticate(self.user2)
        response2 = self.client.post(reverse("game-create-join"), {"code": code})
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertFalse(response2.data["spectator"])
        self.authenticate(self.user3)
        response3 = self.client.post(reverse("game-create-join"), {"code": code})
        self.assertEqual(response3.status_code, status.HTTP_200_OK)
        self.assertTrue(response3.data["spectator"])

    def test_quiz_question_retrieval(self):
        self.authenticate(self.user1)
        response = self.client.get(self.quiz_url + "?subject=Math")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["question"], "2+2=?")

    def test_quiz_answer_submission(self):
        self.authenticate(self.user1)
        game = Game.objects.create(
            player_white=self.user1, subjects=["Math"], status="active"
        )
        move: Move = Move.objects.create(
            game=game,
            player=self.user1,
            from_square="e2",
            to_square="e4",
            piece="pawn",
            move_number=1,
            fen_after="somefen",
            quiz_required=True,
        )
        answer_url = reverse("quiz-answer", args=[move.id])
        response = self.client.post(
            answer_url, {"answer": "B", "question_id": self.quiz.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["correct"])

    def test_ai_game_creation(self):
        self.authenticate(self.user1)
        response = self.client.post(
            reverse("game-create-join"),
            {"subjects": ["Math"], "is_vs_ai": True, "ai_difficulty": "normal"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["is_vs_ai"])
        self.assertEqual(data["ai_difficulty"], "normal")
        game = Game.objects.get(code=data["code"])
        self.assertIsNone(game.player_black)
        self.assertEqual(game.player_white, self.user1)

    def test_normal_game_creation_not_ai(self):
        self.authenticate(self.user1)
        response = self.client.post(
            reverse("game-create-join"),
            {"subjects": ["Math"]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["is_vs_ai"])
        self.assertEqual(data["ai_difficulty"], "")

    def tearDown(self):
        with transaction.atomic():
            self.client.logout()


class QuizGenerationTests(TestCase):
    def setUp(self):
        patcher1 = patch("core.tasks.generate_quizs_in_advance.delay", autospec=True)
        patcher2 = patch("core.tasks.analyze_game_task.delay", autospec=True)
        patcher3 = patch("core.tasks.run_ai_move_task.delay", autospec=True)
        self.mock_generate_quizs = patcher1.start()
        self.mock_analyze_game = patcher2.start()
        self.mock_run_ai_move = patcher3.start()
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        self.addCleanup(patcher3.stop)
        self.user = CustomUser.objects.create_user(
            username="testuser", password="testpass"
        )
        self.game = Game.objects.create(
            player_white=self.user, subjects=["Math", "Science"], status="active"
        )
        self.subjects = ["Math", "Science"]
        self.N = 3
        redis = get_redis()
        for subject in self.subjects:
            key = f"game:{self.game.code}:quizzes:{subject}"
            asyncio.get_event_loop().run_until_complete(redis.delete(key))

    def test_generate_and_fetch_quizzes(self):
        result = generate_quizs_in_advance(self.game.id, self.N, self.subjects)
        self.assertIsInstance(result, dict)
        redis = get_redis()
        for subject in self.subjects:
            key = f"game:{self.game.code}:quizzes:{subject}"
            questions_json = asyncio.get_event_loop().run_until_complete(redis.get(key))
            self.assertIsNotNone(questions_json)
            questions = json.loads(questions_json)
            self.assertIsInstance(questions, list)
            self.assertGreaterEqual(len(questions), 1)
            q = questions[0]
            self.assertIn("question", q)
            self.assertIn("choices", q)
            self.assertIn("correct", q)
            self.assertIn("explanation", q)

    def test_random_question_fetch(self):
        generate_quizs_in_advance(self.game.id, self.N, self.subjects)
        for subject in self.subjects:
            question = asyncio.get_event_loop().run_until_complete(
                get_quiz_question(self.game, subject)
            )
            self.assertIn("question", question)
            self.assertIn("choices", question)
            self.assertIn("correct", question)
            self.assertIn("explanation", question)
