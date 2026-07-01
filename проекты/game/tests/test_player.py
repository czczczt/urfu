import pygame
from src.config import setting


class TestPlayerHit:
    def test_reduces_hp_by_damage(self, player):
        player.hit()
        assert player.hp == setting.CHAR_HP - setting.CHAR_HIT_DAMAGE

    def test_returns_false_while_alive(self, player):
        assert player.hit() is False

    def test_returns_true_on_death(self, player):
        hits = setting.CHAR_HP // setting.CHAR_HIT_DAMAGE
        for _ in range(hits - 1):
            assert player.hit() is False
        assert player.hit() is True

    def test_hp_never_negative(self, player):
        for _ in range(100):
            player.hit()
        assert player.hp == 0

    def test_hp_clamped_exactly_zero_not_below(self, player):
        while player.hp > 0:
            player.hit()
        assert player.hp == 0
        player.hit()
        assert player.hp == 0


class TestPlayerAnimation:
    def test_frame_unchanged_before_threshold(self, player):
        player.frame = 0
        player.count = 0
        player.animation(player.frame_player, setting.CHAR_ANIMATION_SPEED / 2)
        assert player.frame == 0

    def test_frame_advances_on_threshold(self, player):
        player.frame = 0
        player.count = 0
        player.animation(player.frame_player, setting.CHAR_ANIMATION_SPEED)
        assert player.frame == 1

    def test_count_resets_after_advance(self, player):
        player.frame = 0
        player.count = 0
        player.animation(player.frame_player, setting.CHAR_ANIMATION_SPEED)
        assert player.count == 0

    def test_frame_wraps_to_zero(self, player):
        frames = player.frame_player
        player.frame = len(frames) - 1
        player.count = 0
        player.animation(frames, setting.CHAR_ANIMATION_SPEED)
        assert player.frame == 0

    def test_image_matches_current_frame(self, player):
        player.frame = 0
        player.count = 0
        player.animation(player.frame_player, setting.CHAR_ANIMATION_SPEED)
        assert player.image is player.frame_player[player.frame]

    def test_out_of_range_frame_resets_to_zero(self, player):
        player.frame = len(player.frame_player) + 5
        player.animation(player.frame_player, 0)
        assert player.frame == 0


class TestPlayerMovementBounds:
    def test_does_not_move_up_past_bound(self, player):
        player.rect.y = setting.CHAR_BOUNDS_W
        keys = {pygame.K_w: True, pygame.K_s: False, pygame.K_a: False, pygame.K_d: False}
        y_before = player.rect.y
        player.update(keys, 1 / setting.FPS)
        assert player.rect.y == y_before

    def test_does_not_move_down_past_bound(self, player):
        player.rect.y = setting.CHAR_BOUNDS_S
        keys = {pygame.K_w: False, pygame.K_s: True, pygame.K_a: False, pygame.K_d: False}
        y_before = player.rect.y
        player.update(keys, 1 / setting.FPS)
        assert player.rect.y == y_before

    def test_opposite_horizontal_keys_cancel_movement(self, player):
        keys = {pygame.K_w: False, pygame.K_s: False, pygame.K_a: True, pygame.K_d: True}
        x_before = player.rect.x
        player.update(keys, 1 / setting.FPS)
        assert player.rect.x == x_before

    def test_moves_left_within_bounds(self, player):
        player.rect.x = setting.CHAR_BOUNDS_A + 100
        keys = {pygame.K_w: False, pygame.K_s: False, pygame.K_a: True, pygame.K_d: False}
        x_before = player.rect.x
        player.update(keys, 1 / setting.FPS)
        assert player.rect.x < x_before