import pygame
from src.config import setting


class Map(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__() # инициализацирует innit базового класса

        self.count_bg = 0 # для анимации
        self.count_stars = 0

        self.background_load = pygame.image.load('assets/background/bg.jpg')
        self.background = pygame.transform.scale(self.background_load, setting.WINDOW_SIZE) # обрезка размера до размера экрана
        self.stars_load = pygame.image.load('assets/background/stars.png')
        self.stars = pygame.transform.scale(self.stars_load, setting.WINDOW_SIZE)
        
        self.image = pygame.Surface(setting.WINDOW_SIZE)
        self.rect = self.image.get_rect()

    def update(self, scaled_delta_time):
        self.count_bg -= setting.BACKGROUND_MAIN_ANIMATION_SPEED * scaled_delta_time # два фона двигаются влево
        
        if self.count_bg <= -setting.WINDOW_SIZE[0]: # когда 1 полностью ушел за экран - перемещение в начало
            self.count_bg = 0
        self.image.blit(self.background, (self.count_bg, 0))
        self.image.blit(self.background, (self.count_bg + setting.WINDOW_SIZE[0], 0))
        
        self.count_stars -= setting.BACKGROUND_ST_ANIMATION_SPEED * scaled_delta_time
        if self.count_stars <= -setting.WINDOW_SIZE[0]:
            self.count_stars = 0
        self.image.blit(self.stars, (self.count_stars, 0))
        self.image.blit(self.stars, (self.count_stars + setting.WINDOW_SIZE[0], 0))
