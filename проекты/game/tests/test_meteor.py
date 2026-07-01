import pygame
from src.config import setting


class TestMeteorSpawn:
    def test_spawn_activates_one_slot(self, meteor):
        meteor.spawn()
        active = sum(1 for slot in meteor.pool if slot['active'])
        assert active == 1
 
    def test_spawn_position_off_screen_right(self, meteor):
        meteor.spawn()
        slot = next(s for s in meteor.pool if s['active'])
        assert slot['rect'].centerx > setting.WINDOW_SIZE[0]
 
    def test_spawn_does_nothing_when_pool_full(self, meteor):
        for slot in meteor.pool:
            slot['active'] = True
        before = [dict(slot) for slot in meteor.pool]
        meteor.spawn()
        assert meteor.pool == before
 
    def test_spawn_speed_scales_with_wave_count(self, meteor):
        meteor.wave_count = 10
        meteor.spawn()

        slot = next(s for s in meteor.pool if s['active'])

        min_speed = setting.METEOR_SPEED_RANGE[0] * (
            1 + meteor.wave_count * setting.METEOR_SPEED_MULTIPLIER
        )

        assert slot['speed'] >= min_speed
 
 
class TestMeteorUpdate:
    def test_inactive_slots_not_moved(self, meteor):
        meteor.update(1.0)
        for slot in meteor.pool:
            assert slot['rect'].x == 0 or slot['active']
 
    def test_active_slot_moves_left(self, meteor):
        meteor.spawn()
        slot = next(s for s in meteor.pool if s['active'])
        x_before = slot['rect'].x
        meteor.update(1 / setting.FPS)
        assert slot['rect'].x < x_before
 
    def test_slot_deactivates_off_screen_left(self, meteor):
        meteor.spawn()
        slot = next(s for s in meteor.pool if s['active'])
        slot['rect'].x = -slot['rect'].width - 1
        meteor.update(0.0001)
        assert slot['active'] is False
 
    def test_wave_count_increments_after_interval(self, meteor):
        meteor.wave_timer = setting.METEOR_NEXT_WAVE_INTERVAL
        meteor.update(0)
        assert meteor.wave_count == 1
        assert meteor.wave_active is True
 
    def test_wave_spawns_meteors_on_spawn_interval(self, meteor):
        meteor.wave_timer = setting.METEOR_NEXT_WAVE_INTERVAL
        meteor.update(0)
        meteor.spawn_timer = setting.METEOR_SPAWN_INTERVAL
        meteor.update(0)
        active = sum(1 for slot in meteor.pool if slot['active'])
        assert active == meteor.wave_count
 
    def test_wave_ends_after_duration(self, meteor):
        meteor.wave_timer = setting.METEOR_NEXT_WAVE_INTERVAL
        meteor.update(0)
        meteor.wave_duration = 0
        meteor.update(0)
        assert meteor.wave_active is False
 
 
class TestMeteorCollide:
    def test_no_collision_when_no_active_slots(self, meteor, player):
        assert meteor.collide(player.rect) is False
 
    def test_collision_deactivates_slot(self, meteor, player):
        meteor.spawn()
        slot = next(s for s in meteor.pool if s['active'])
        slot['rect'].center = player.rect.center
        assert meteor.collide(player.rect) is True
        assert slot['active'] is False
 
    def test_collision_returns_false_when_no_overlap(self, meteor, player):
        meteor.spawn()
        slot = next(s for s in meteor.pool if s['active'])
        slot['rect'].x = player.rect.right + 10000
        assert meteor.collide(player.rect) is False
 
    def test_collision_stops_after_first_match(self, meteor, player):
        meteor.spawn()
        meteor.spawn()
        for slot in meteor.pool:
            if slot['active']:
                slot['rect'].center = player.rect.center
        meteor.collide(player.rect)
        active_after = sum(1 for slot in meteor.pool if slot['active'])
        assert active_after == 1
 
 
class TestMeteorScaledCache:
    def test_same_size_uses_cache(self, meteor):
        img1 = meteor.get_scaled(80)
        img2 = meteor.get_scaled(80)
        assert img1 is img2
 
    def test_different_size_creates_new_entry(self, meteor):
        img1 = meteor.get_scaled(80)
        img2 = meteor.get_scaled(90)
        assert img1 is not img2
        assert len(meteor.scaled_cache) == 2


class TestMeteorDamage:
    def test_no_damage_when_no_active_slots(self, meteor):
        assert meteor.damage(pygame.Rect(0, 0, 10, 10), setting.BULLET_DAMAGE) is False

    def test_damage_reduces_hp(self, meteor):
        meteor.spawn()
        slot = next(s for s in meteor.pool if s['active'])
        hp_before = slot['hp']
        meteor.damage(slot['rect'], setting.BULLET_DAMAGE)
        assert slot['hp'] == hp_before - setting.BULLET_DAMAGE

    def test_damage_returns_true_on_overlap(self, meteor):
        meteor.spawn()
        slot = next(s for s in meteor.pool if s['active'])
        assert meteor.damage(slot['rect'], setting.BULLET_DAMAGE) is True

    def test_damage_returns_false_when_no_overlap(self, meteor):
        meteor.spawn()
        slot = next(s for s in meteor.pool if s['active'])
        bullet_rect = slot['rect'].copy()
        bullet_rect.x = slot['rect'].right + 10000
        assert meteor.damage(bullet_rect, setting.BULLET_DAMAGE) is False

    def test_slot_stays_active_while_hp_remains(self, meteor):
        meteor.spawn()
        slot = next(s for s in meteor.pool if s['active'])
        meteor.damage(slot['rect'], setting.METEOR_HP - 1)
        assert slot['active'] is True

    def test_slot_deactivates_when_hp_reaches_zero(self, meteor):
        meteor.spawn()
        slot = next(s for s in meteor.pool if s['active'])
        meteor.damage(slot['rect'], setting.METEOR_HP)
        assert slot['active'] is False

    def test_slot_deactivates_when_hp_drops_below_zero(self, meteor):
        meteor.spawn()
        slot = next(s for s in meteor.pool if s['active'])
        meteor.damage(slot['rect'], setting.METEOR_HP + 100)
        assert slot['active'] is False

    def test_full_kill_requires_multiple_hits(self, meteor):
        meteor.spawn()
        slot = next(s for s in meteor.pool if s['active'])
        hits = -(-setting.METEOR_HP // setting.BULLET_DAMAGE) # ceil-деление
        for _ in range(hits - 1):
            meteor.damage(slot['rect'], setting.BULLET_DAMAGE)
            assert slot['active'] is True
        meteor.damage(slot['rect'], setting.BULLET_DAMAGE)
        assert slot['active'] is False

    def test_crit_damage_kills_faster(self, meteor):
        meteor.spawn()
        slot = next(s for s in meteor.pool if s['active'])
        meteor.damage(slot['rect'], setting.BULLET_CRIT_DAMAGE)
        meteor.damage(slot['rect'], setting.BULLET_CRIT_DAMAGE)
        assert slot['active'] is False

    def test_damage_stops_after_first_match(self, meteor):
        meteor.spawn()
        meteor.spawn()
        for slot in meteor.pool:
            if slot['active']:
                slot['rect'].center = (500, 500)
        bullet_rect = pygame.Rect(0, 0, 10, 10)
        bullet_rect.center = (500, 500)
        meteor.damage(bullet_rect, setting.METEOR_HP)
        active_after = sum(1 for slot in meteor.pool if slot['active'])
        assert active_after == 1