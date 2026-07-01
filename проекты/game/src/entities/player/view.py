class PlayerView(object):
    def draw(self, screen, model):
        screen.blit(model.image, model.rect)