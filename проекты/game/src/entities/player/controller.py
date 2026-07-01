import pygame


class PlayerController(object):
    def update(self, model, scaled_delta_time):
        keys = pygame.key.get_pressed()
        model.update(keys, scaled_delta_time)