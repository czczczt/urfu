from src.config import setting

class TestBulletSpawn:
    def test_spawn_activates_one_slot(self, bullet, player):
        bullet.spawn(player.rect)
        active = sum(1 for slot in bullet.pool if slot['active'])
        assert active == 1

    def test_spawn_position_matches_player_center(self, bullet, player):
        bullet.spawn(player.rect)
        slot = next(s for s in bullet.pool if s['active'])
        assert slot['rect'].center == player.rect.center

    def test_spawn_does_nothing_when_pool_full(self, bullet, player):
        for slot in bullet.pool:
            slot['active'] = True
        before = [dict(slot) for slot in bullet.pool]
        bullet.spawn(player.rect)
        assert bullet.pool == before

    def test_pool_size_matches_setting(self, bullet):
        assert len(bullet.pool) == setting.BULLET_POOL_SIZE

    def test_cannot_exceed_pool_size(self, bullet, player):
        for _ in range(setting.BULLET_POOL_SIZE + 5):
            bullet.spawn(player.rect)
        active = sum(1 for slot in bullet.pool if slot['active'])
        assert active == setting.BULLET_POOL_SIZE


class TestBulletUpdate:
    def test_inactive_slots_not_moved(self, bullet):
        bullet.update(1.0)
        for slot in bullet.pool:
            assert slot['rect'].x == 0 or slot['active']

    def test_active_slot_moves_right(self, bullet, player):
        bullet.spawn(player.rect)
        slot = next(s for s in bullet.pool if s['active'])
        x_before = slot['rect'].x
        bullet.update(1 / setting.FPS)
        assert slot['rect'].x > x_before

    def test_slot_deactivates_off_screen_right(self, bullet, player):
        bullet.spawn(player.rect)
        slot = next(s for s in bullet.pool if s['active'])
        slot['rect'].x = setting.WINDOW_SIZE[0] + 1
        bullet.update(0.0001)
        assert slot['active'] is False


class TestBulletCrit:
    def test_non_crit_uses_base_chance(self, bullet, player):
        bullet.crit_chance.current_chance = -1
        bullet.spawn(player.rect)
        slot = next(s for s in bullet.pool if s['active'])
        assert slot['crit'] is False

    def test_guaranteed_crit_when_chance_above_one(self, bullet, player):
        bullet.crit_chance.current_chance = 1.1
        bullet.spawn(player.rect)
        slot = next(s for s in bullet.pool if s['active'])
        assert slot['crit'] is True

    def test_chance_resets_after_crit(self, bullet, player):
        bullet.crit_chance.current_chance = 1.1
        bullet.spawn(player.rect)
        assert bullet.crit_chance.current_chance == setting.BULLET_CRIT_BASE_CHANCE

    def test_chance_increases_after_miss(self, bullet, player):
        bullet.crit_chance.current_chance = -1
        chance_before = bullet.crit_chance.current_chance
        bullet.spawn(player.rect)
        assert bullet.crit_chance.current_chance == chance_before + setting.BULLET_CRIT_C


class TestPRD:
    def test_initial_chance_equals_base(self, bullet):
        assert bullet.crit_chance.current_chance == setting.BULLET_CRIT_BASE_CHANCE

    def test_check_returns_bool(self, bullet):
        assert bullet.crit_chance.check() in (True, False)

    def test_success_resets_to_base_chance(self, bullet):
        bullet.crit_chance.current_chance = 1.1
        bullet.crit_chance.check()
        assert bullet.crit_chance.current_chance == setting.BULLET_CRIT_BASE_CHANCE

    def test_miss_increments_by_c(self, bullet):
        bullet.crit_chance.current_chance = -1
        chance_before = bullet.crit_chance.current_chance
        bullet.crit_chance.check()
        assert bullet.crit_chance.current_chance == chance_before + setting.BULLET_CRIT_C

    def test_repeated_misses_increase_chance_monotonically(self, bullet):
        bullet.crit_chance.current_chance = -1
        chances = []
        for _ in range(5):
            bullet.crit_chance.check()
            chances.append(bullet.crit_chance.current_chance)
        assert chances == sorted(chances)

    def test_eventual_success_with_growing_chance(self, bullet):
        bullet.crit_chance.current_chance = -1
        bullet.crit_chance.c = 2.0
        bullet.crit_chance.check()
        assert bullet.crit_chance.check() is True