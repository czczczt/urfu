class BulletView(object):
    def draw(self, screen, model):
        for slot in model.pool:
            if slot["active"]:
                image = model.crit_image if slot["crit"] else model.image
                screen.blit(image, slot["rect"])