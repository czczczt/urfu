class MeteorView(object):
    def draw(self, screen, model):
        for slot in model.pool:
            if slot["active"]:
                screen.blit(slot["image"], slot["rect"])