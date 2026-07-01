import pygame
import sys
from src.config import setting, config
from src.entities.player.model import PlayerModel
from src.entities.player.view import PlayerView
from src.entities.player.controller import PlayerController
from src.entities.meteor.model import MeteorModel
from src.entities.meteor.view import MeteorView
from src.entities.bullet.model import BulletModel
from src.entities.bullet.view import BulletView
from src.entities.bullet.controller import BulletController
from src.menu import Menu
from src.map import Map
from src.ui import Hud, Ui


class Game:
    def __init__(self):
        self.is_paused = False
        self.game_speed = 1.0
        self.delta_time = 0.016 # время для 60 фпс
        self.dead_count = 0
        self.state = "menu"

        self.menu_sound = pygame.mixer.Sound('assets/audio/menu.mp3') # музыка в меню
        self.play_sound = pygame.mixer.Sound('assets/audio/play.wav') # музыка во время игры
        self.dead_sound = pygame.mixer.Sound('assets/audio/dead.wav') # музыка смерти
        self.hit_effect = pygame.mixer.Sound('assets/audio/hit.wav') # звук урона
        self.click_effect = pygame.mixer.Sound('assets/audio/click.wav') # звук нажатия кнопок
        self.bullet_effect = pygame.mixer.Sound('assets/audio/bullet.wav') # звук выстрела
        self.meteor_hit_effect = pygame.mixer.Sound('assets/audio/meteor_hit.wav') # звук попадания по метеориту

        self.menu_sound.set_volume(0.3)
        self.play_sound.set_volume(0.3)
        self.dead_sound.set_volume(0.3)

        self.map = Map()
        self.menu = Menu()
        self.player_model = PlayerModel()
        self.player_view = PlayerView()
        self.player_controller = PlayerController()
        self.meteor_model = MeteorModel()
        self.meteor_view = MeteorView()
        self.bullet_model = BulletModel()
        self.bullet_view = BulletView()
        self.bullet_controller = BulletController()
        self.ui = Ui()
        self.hud = Hud()

        self.sound(self.menu_sound)

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            pygame.mixer.pause()
        else:
            pygame.mixer.unpause()

        self.effect(self.click_effect)

    def toggle_music(self):
        config.data['music'] = not config.data['music']
        if config.data['music']:
            self.sound(self.menu_sound)
        else:
            self.menu_sound.stop()

    def sound(self, sound):
        if config.data['music']:
            sound.play(-1)

    def effect(self, sound):
        if config.data['effects']:
            sound.play()

    def return_to_menu(self):
        if self.state != "dead": 
            self.effect(self.click_effect)
        self.state = "menu"
        self.play_sound.stop()
        self.dead_sound.stop()
        self.sound(self.menu_sound)

    def start_play(self):
        self.effect(self.click_effect)
        self.player_model = PlayerModel()
        self.meteor_model = MeteorModel()
        self.bullet_model = BulletModel()
        self.play_sprites = pygame.sprite.Group(self.map)
        self.state = "play"
        self.hud_wave_count = 0
        self.hud.set_hp(self.player_model.hp)
        self.hud.set_wave(0)
        self.hud.set_time(0)
        self.menu_sound.stop()
        self.sound(self.play_sound)

    def enter_dead_state(self):
        self.dead_count = 0
        self.state = "dead"
        self.play_sound.stop()
        self.sound(self.dead_sound)

    def update(self):
        if self.state == "menu": # обновляется меню
            scaled_delta_time = self.delta_time * self.game_speed # реальное время между кадрами * коэф
            self.map.update(scaled_delta_time)
            self.menu.update(scaled_delta_time)
        elif self.state == "play" and not self.is_paused: # обновляется игра
            scaled_delta_time = self.delta_time * self.game_speed
            self.update_game_world(scaled_delta_time)
        elif self.state == "dead":
            self.dead_count += self.delta_time
            if self.dead_count >= setting.DEAD_SCREEN_DURATION:
                self.return_to_menu()

    def update_game_world(self, scaled_delta_time):
        self.player_controller.update(self.player_model, scaled_delta_time) # передача реального времени между кадрами
        self.map.update(scaled_delta_time)
        self.meteor_model.update(scaled_delta_time)
        self.bullet_model.update(scaled_delta_time)
        if self.meteor_model.wave_count != self.hud_wave_count:
            self.hud_wave_count = self.meteor_model.wave_count
            self.hud.set_wave(self.hud_wave_count)
        self.hud.set_time(self.meteor_model.wave_duration)

        for slot in self.bullet_model.pool:
            if not slot["active"]:
                continue
            value = setting.BULLET_CRIT_DAMAGE if slot["crit"] else setting.BULLET_DAMAGE
            if self.meteor_model.damage(slot["rect"], value):
                slot["active"] = False
                self.effect(self.meteor_hit_effect)

        if self.meteor_model.collide(self.player_model.rect):
            is_dead = self.player_model.hit()
            self.hud.set_hp(self.player_model.hp)
            self.effect(self.hit_effect)
            if is_dead:
                self.enter_dead_state()

    def draw(self, screen):
        screen.blit(self.map.image, self.map.rect)

        if self.state == "menu":
            self.ui.draw_menu(screen)

        else:
            self.player_view.draw(screen, self.player_model)
            self.meteor_view.draw(screen, self.meteor_model)
            self.bullet_view.draw(screen, self.bullet_model)

            self.ui.draw_play(screen, self.hud)
            self.hud.draw_wave(screen)

            if self.state == "dead":
                self.hud.draw_dead(screen)

            elif self.is_paused:
                self.hud.draw_pause(screen)


if __name__ == "__main__":
    pygame.init()
    game = Game()
    clock = pygame.time.Clock()

    pygame.display.set_caption("spaceships") # название
    logo_load = pygame.image.load('assets/logo.png') # иконка
    pygame.display.set_icon(logo_load)
    screen = pygame.display.set_mode(setting.WINDOW_SIZE) # открытие окна

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: # закрытие окна
                running = False
    
            elif game.state == "menu":
                menu_action = game.menu.event(event)
                if menu_action == "start":
                    game.start_play()
                elif menu_action == "music":
                    game.effect(game.click_effect)
                    game.toggle_music()
                elif menu_action == "effect":
                    config.data['effects'] = not config.data['effects']
                    game.effect(game.click_effect)
                elif menu_action == "exit":
                    game.effect(game.click_effect)
                    running = False

            elif game.state == "play":
                if event.type == pygame.KEYDOWN: # пауза на p и esc
                    if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                        game.toggle_pause()
                elif event.type == pygame.MOUSEBUTTONDOWN and game.ui.menu_button.collidepoint(event.pos):
                    game.return_to_menu()
                if not game.is_paused and event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    active_before = sum(1 for slot in game.bullet_model.pool if slot["active"])
                    game.bullet_controller.update(game.bullet_model, game.player_model.rect, event)
                    active_after = sum(1 for slot in game.bullet_model.pool if slot["active"])
                    if active_after > active_before:
                        game.effect(game.bullet_effect)

            elif game.state == "dead":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    game.return_to_menu()

        game.update()
        game.draw(screen)
        pygame.display.flip()

        game.delta_time = clock.tick(setting.FPS) / 1000.0 # реальное время между кадрами в секундах

    config.save()
    pygame.quit()
    sys.exit()