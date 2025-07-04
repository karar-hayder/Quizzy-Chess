from datetime import timedelta

import chess
import redis
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Game

REDIS_URL = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")


class Command(BaseCommand):
    help = "Audit all FENs in the Game table and Redis, printing any invalid FENs. Also remove stale/waiting games."

    def handle(self, *args, **options):
        self.stdout.write("Auditing FENs in Game table...")
        games = Game.objects.all()
        invalid_db = 0
        for game in games:
            try:
                chess.Board(game.fen)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Invalid DB FEN for game {game.code}: {game.fen} ({e})"
                    )
                )
                invalid_db += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Checked {games.count()} games, {invalid_db} invalid FENs in DB."
            )
        )

        self.stdout.write("Auditing FENs in Redis...")
        r = redis.from_url(REDIS_URL)
        invalid_redis = 0
        for game in games:
            key = f"game:{game.code}:fen"
            fen = r.get(key)
            if fen:
                fen = fen.decode()
                try:
                    chess.Board(fen)
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Invalid Redis FEN for game {game.code}: {fen} ({e})"
                        )
                    )
                    invalid_redis += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Checked {games.count()} Redis FENs, {invalid_redis} invalid FENs in Redis."
            )
        )
        waiting_games = Game.objects.filter(status="waiting")
        count_waiting = waiting_games.count()
        for game in waiting_games:
            self.stdout.write(self.style.WARNING(f"Deleting waiting game: {game.code}"))
            game.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count_waiting} waiting games."))
        cutoff = timezone.now() - timedelta(hours=1)
        stale_games = Game.objects.filter(status="active", updated_at__lt=cutoff)
        count_stale = stale_games.count()
        for game in stale_games:
            self.stdout.write(
                self.style.WARNING(
                    f"Deleting stale active game: {game.code} (last updated {game.updated_at})"
                )
            )
            game.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {count_stale} stale active games (not updated in >1 hour)."
            )
        )

        if invalid_db == 0 and invalid_redis == 0:
            self.stdout.write(self.style.SUCCESS("All FENs are valid!"))
        else:
            self.stdout.write(self.style.WARNING("Some invalid FENs found. See above."))
