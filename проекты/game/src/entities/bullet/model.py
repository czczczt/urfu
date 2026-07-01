import pygame
from random import random
from src.config import setting


class PRD:
    def __init__(self, base_chance, c):
        self.base_chance = base_chance
        self.current_chance = base_chance
        self.c = c

    def check(self):
        if random() < self.current_chance:
            self.current_chance = self.base_chance # сброс шанса
            return True
        self.current_chance += self.c # увеличение шанса
        return False


class BulletModel:
    def __init__(self):
        self.bullet_load = pygame.image.load('assets/entities/bullets/bullet1.png')
        self.crit_load = pygame.image.load('assets/entities/bullets/bullet2.png')
        self.image = pygame.transform.scale(self.bullet_load, setting.BULLET_SIZE)
        self.crit_image = pygame.transform.scale(self.crit_load, setting.BULLET_CRIT_SIZE)
        self.pool = [{"rect": pygame.Rect(0, 0, 0, 0), "crit": False, "active": False} for _ in range(setting.BULLET_POOL_SIZE)] # фиксированный пул слотов

        self.crit_chance = PRD(setting.BULLET_CRIT_BASE_CHANCE, setting.BULLET_CRIT_C)

    def spawn(self, player_rect):
        for slot in self.pool:
            if not slot["active"]:
                image = self.crit_image if self.crit_chance.check() else self.image

                rect = image.get_rect()
                rect.center = player_rect.center

                slot["rect"], slot["crit"], slot["active"] = rect, image is self.crit_image, True
                return

    def update(self, scaled_delta_time):
        for slot in self.pool:
            if not slot["active"]:
                continue

            slot["rect"].x += setting.BULLET_SPEED * scaled_delta_time * setting.FPS

            if slot["rect"].left > setting.WINDOW_SIZE[0]:
                slot["active"] = False