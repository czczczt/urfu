import pygame
from random import randint, uniform
from src.config import setting


class MeteorModel:
    def __init__(self):
        self.meteor_load = pygame.image.load('assets/entities/meteor.png')
        self.scaled_cache = {} # кэш изображений по размеру
        self.pool = [{"image": None, "rect": pygame.Rect(0, 0, 0, 0), "speed": 0, "hp": 0, "active": False} for _ in range(setting.METEOR_POOL_SIZE)] # фиксированный пул слотов

        self.wave_count = 0
        self.wave_active = False
        self.wave_duration = setting.METEOR_BASE_WAVE_DURATION

        self.wave_timer = 0
        self.spawn_timer = 0

    def get_scaled(self, size):
        if size not in self.scaled_cache:
            self.scaled_cache[size] = pygame.transform.scale(self.meteor_load, (size, size))
        return self.scaled_cache[size]

    def spawn(self):
        for slot in self.pool:
            if not slot["active"]: # нашли мертвый метеор
                size = randint(*setting.METEOR_SIZE_RANGE)
                image = self.get_scaled(size)

                rect = image.get_rect()
                rect.center = (setting.WINDOW_SIZE[0] + size, randint(setting.CHAR_SIZE[0], setting.WINDOW_SIZE[1] - setting.CHAR_SIZE[0]))

                speed = uniform(*setting.METEOR_SPEED_RANGE)
                speed *= 1 + self.wave_count * setting.METEOR_SPEED_MULTIPLIER

                slot["image"], slot["rect"], slot["speed"], slot["hp"], slot["active"] = image, rect, speed, setting.METEOR_HP, True
                return # создать только один метеор за вызов функции

    def wave(self, scaled_delta_time):
        self.wave_timer += scaled_delta_time

        if not self.wave_active:
            if self.wave_timer >= setting.METEOR_NEXT_WAVE_INTERVAL:
                self.wave_count += 1

                self.wave_active = True
                self.wave_duration = setting.METEOR_BASE_WAVE_DURATION + self.wave_count
                self.wave_timer = 0
                self.spawn_timer = 0

        else:
            self.wave_duration -= scaled_delta_time
            self.spawn_timer += scaled_delta_time

            if self.spawn_timer >= setting.METEOR_SPAWN_INTERVAL:
                self.spawn_timer = 0

                for _ in range(self.wave_count):
                    self.spawn()

            if self.wave_duration <= 0:
                self.wave_active = False
                self.wave_timer = 0

    def update(self, scaled_delta_time):
        self.wave(scaled_delta_time)

        for slot in self.pool:
            if not slot["active"]:
                continue

            slot["rect"].x -= slot["speed"] * scaled_delta_time * setting.FPS

            if slot["rect"].right < 0:
                slot["active"] = False

    def collide(self, player_rect):
        for slot in self.pool:
            if slot["active"] and slot["rect"].colliderect(player_rect):
                slot["active"] = False
                return True
        return False

    def damage(self, bullet_rect, value):
        for slot in self.pool:
            if slot["active"] and slot["rect"].colliderect(bullet_rect):
                slot["hp"] -= value
                if slot["hp"] <= 0:
                    slot["active"] = False
                return True
        return False