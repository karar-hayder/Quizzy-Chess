from django.urls import re_path

from . import consumers
from . import matchmaking_consumer

websocket_urlpatterns = [
    re_path(
        r"ws/game/(?P<game_code>[A-Za-z0-9]{10,30})/$", consumers.GameConsumer.as_asgi()
    ),
    re_path(r"ws/matchmaking/$", matchmaking_consumer.MatchmakingConsumer.as_asgi()),
]
