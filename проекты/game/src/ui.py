import pygame
from src.config import setting, config


class Button:
    def __init__(self, ui_load, rect, xy):
        self.frames = [pygame.transform.scale(ui_load.subsurface(pygame.Rect(*r)), setting.BUTTONS_SIZE) for r in rect]
        self.image, self.rect = self.load_image_rect(self.frames, xy)

    @staticmethod
    def load_image_rect(frames, xy):
        image = frames[0]
        rect = image.get_rect()
        rect.center = xy
        return image, rect

    def collidepoint(self, pos):
        return self.rect.collidepoint(pos)

    def turn(self, state):
        self.image = self.frames[state]

    def draw(self, screen):
        screen.blit(self.image, self.rect)


class AnimButton(Button):
    def __init__(self, frames, start_index, count, size, xy, animation_speed):
        self.frames = [pygame.transform.scale(pygame.image.load(frames.format(i)), size) for i in range(start_index, start_index + count)]
        self.image, self.rect = self.load_image_rect(self.frames, xy)
        self.animation_speed = animation_speed
        self.frame = 0
        self.count = 0

    def update(self, scaled_delta_time):
        self.count += scaled_delta_time
        if self.count >= self.animation_speed:
            self.count = 0
            self.frame += 1
            if self.frame == len(self.frames):
                self.frame = 0
        self.image = self.frames[self.frame]


class Hud:
    def __init__(self):
        self.font = pygame.font.Font('assets/ui/8bit.ttf', setting.FONT_SIZE)

        self.bg_alpha = pygame.Surface(setting.WINDOW_SIZE, pygame.SRCALPHA)
        self.bg_alpha.fill((0, 0, 0, setting.BACKGROUND_ALPHA))

        self.dead_image, self.dead_rect = self.render_text('Вы проиграли!', setting.CHAR_DEAD_XY)
        self.pause_image, self.pause_rect = self.render_text('Пауза', setting.CHAR_DEAD_XY)

        self.set_hp(setting.CHAR_HP)
        self.set_wave(0)
        self.set_time(0)

    def render_text(self, text, xy):
        image = self.font.render(text, False, 'white')
        rect = image.get_rect()
        rect.center = xy
        return image, rect

    def set_hp(self, hp):
        self.hp_image, self.hp_rect = self.render_text(str(hp), setting.CHAR_HP_XY)

    def set_wave(self, wave_count):
        self.wave_image, self.wave_rect = self.render_text(f'Волна: {wave_count}', setting.CHAR_WAVE_XY)

    def set_time(self, value):
        self.time_image, self.time_rect = self.render_text(f'Таймер: {int(value)}', setting.CHAR_TIMER_XY)

    def draw_hp(self, screen):
        screen.blit(self.hp_image, self.hp_rect)
        
    def draw_dead(self, screen):
        screen.blit(self.bg_alpha, (0, 0))
        screen.blit(self.dead_image, self.dead_rect)

    def draw_pause(self, screen):
        screen.blit(self.bg_alpha, (0, 0))
        screen.blit(self.pause_image, self.pause_rect)

    def draw_wave(self, screen):
        screen.blit(self.wave_image, self.wave_rect)
        screen.blit(self.time_image, self.time_rect)


class Ui:
    def __init__(self):
        self.ui_load = pygame.image.load('assets/ui/buttons/ui.png')
        self.uio_load = pygame.image.load('assets/ui/buttons/uio.png')

        self.music_button = Button(self.ui_load, [(48, 16, 16, 16), (0, 32, 16, 16)], setting.MENU_MUSIC_XY) # 16 - размер спрайта в файле
        self.effect_button = Button(self.ui_load, [(16, 32, 16, 16), (32, 32, 16, 16)], setting.MENU_EFFECT_XY)
        self.exit_button = Button(self.ui_load, [(0, 0, 16, 16)], (setting.MENU_MUSIC_XY[0], setting.WINDOW_SIZE[1] - setting.MENU_MUSIC_XY[1]))
        self.menu_button = Button(self.uio_load, [(2 * 16, 1 * 16, 16, 16)], setting.PLAY_BUTTONS_XY)

        self.play_button = AnimButton('assets/menu/singlp/{}.png', 0, 12, setting.MENU_PLAY_SIZE, setting.MENU_PLAY_XY, setting.MENU_PLAY_ANIMATION_SPEED)
        self.title_button = AnimButton('assets/menu/title/{}.png', 0, 4, setting.MENU_TITLE_SIZE, setting.MENU_TITLE_XY, setting.MENU_TITLE_ANIMATION_SPEED)

    def update_menu(self, scaled_delta_time):
        self.play_button.update(scaled_delta_time)
        self.title_button.update(scaled_delta_time)

    def draw_menu(self, screen):
        self.play_button.draw(screen)
        self.music_button.turn(0 if config.data['music'] else 1)
        self.music_button.draw(screen)
        self.effect_button.turn(0 if config.data['effects'] else 1)
        self.effect_button.draw(screen)
        self.exit_button.draw(screen)
        self.title_button.draw(screen)

    def draw_play(self, screen, hud):
        self.menu_button.draw(screen)
        hud.draw_hp(screen)