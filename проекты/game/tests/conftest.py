import pytest
from src.entities.player.model import PlayerModel
from src.entities.meteor.model import MeteorModel
from src.entities.bullet.model import BulletModel
from src.config import setting, config


class FakeHud:
    def __init__(self):
        self.hp = None

    def set_hp(self, hp):
        self.hp = hp

    def set_wave(self, wave_count):
        pass

    def set_time(self, value):
        pass


@pytest.fixture
def player():
    return PlayerModel()


@pytest.fixture
def meteor():
    return MeteorModel()


@pytest.fixture
def bullet():
    return BulletModel()


@pytest.fixture
def fake_hud():
    return FakeHud()