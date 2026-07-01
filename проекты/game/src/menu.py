import pygame
from src.ui import Ui


class Menu(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.ui = Ui()

    def event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN:
            return None
        if self.ui.play_button.collidepoint(event.pos):
            return "start"
        if self.ui.music_button.collidepoint(event.pos):
            return "music"
        if self.ui.effect_button.collidepoint(event.pos):
            return "effect"
        if self.ui.exit_button.collidepoint(event.pos):
            return "exit"

    def update(self, scaled_delta_time):
        self.ui.update_menu(scaled_delta_time)