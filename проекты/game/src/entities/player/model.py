import pygame
from random import randint
from src.config import setting
from src.ui import Button


class PlayerModel:
    def __init__(self):
        self.frame = 0 # для анимации
        self.count = 0
        self.color = randint(0, 6) # [0, 6]
        self.hp = setting.CHAR_HP

        self.player_load = pygame.image.load(f'assets/entities/player/{self.color}.png')
        width = self.player_load.get_width() // 4 # количество спрайтов в файле
        height = self.player_load.get_height()
        self.frame_player = [pygame.transform.rotate(pygame.transform.scale(self.player_load.subsurface(pygame.Rect(i * width, 0, width, height)), setting.CHAR_SIZE), -90) for i in range(4)] # Rect создает область, subsurface обрезает
        self.image, self.rect = Button.load_image_rect(self.frame_player, setting.CHAR_XY)

    def animation(self, frames, scaled_delta_time):
        self.count += scaled_delta_time
        if self.count >= setting.CHAR_ANIMATION_SPEED: # смена кадра зависит от ANIMATION_SPEED
            self.count = 0
            self.frame += 1
            if self.frame == len(frames):
                self.frame = 0
        if self.frame >= len(frames):
            self.frame = 0
        self.image = frames[self.frame]

    def hit(self):
        self.hp = max(0, self.hp - setting.CHAR_HIT_DAMAGE)
        return self.hp <= 0

    def update(self, keys, scaled_delta_time):
        speed = setting.CHAR_SPEED * scaled_delta_time * setting.FPS # лок на 60 фпс, чтобы на всех пк скорость была одинаковой

        if keys[pygame.K_w] and self.rect.y > setting.CHAR_BOUNDS_W:
            self.rect.y -= speed
        if keys[pygame.K_s] and self.rect.y < setting.CHAR_BOUNDS_S:
            self.rect.y += speed
        if keys[pygame.K_a] and self.rect.x > setting.CHAR_BOUNDS_A and not keys[pygame.K_d]:
            self.rect.x -= speed
        if keys[pygame.K_d] and self.rect.x < setting.CHAR_BOUNDS_D and not keys[pygame.K_a]:
            self.rect.x += speed

        self.animation(self.frame_player, scaled_delta_time)