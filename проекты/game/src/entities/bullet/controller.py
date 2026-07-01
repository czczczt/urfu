import pygame


class BulletController(object):
    def update(self, model, player_rect, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            model.spawn(player_rect)