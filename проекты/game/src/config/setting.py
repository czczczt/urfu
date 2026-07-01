WINDOW_SIZE = (2560,1440) # (1920, 1080) (2560,1440)
def s(v): return int(v * min(WINDOW_SIZE[0] / 1920, WINDOW_SIZE[1] / 1080))

FPS = 60 # игра подгоняется под 60 фпс
FONT_SIZE = 40 # размер шрифта
BUTTONS_SIZE = (s(85), s(85)) # размер кнопок

BACKGROUND_MAIN_ANIMATION_SPEED = 27 # скорость фона
BACKGROUND_ST_ANIMATION_SPEED = 47 # скорость доп фона
BACKGROUND_ALPHA = 128 # затемнение фона при поражении/паузе

PLAY_BUTTONS_XY = (s(75), s(75)) # позиция кнопки назад
PLAY_BUTTON_SIZE = (s(85), s(85)) # размер кнопок

MENU_PLAY_SIZE = (s(669), s(171)) # размер кнопки играть
MENU_PLAY_ANIMATION_SPEED = 0.15 # скорость анимации кнопки играть
MENU_PLAY_XY = (WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 1.5) # позиция кнопки играть
MENU_TITLE_SIZE = (s(616), s(140)) # размер кнопки заголовка
MENU_TITLE_ANIMATION_SPEED = 0.15 # скорость анимации заголовка
MENU_TITLE_XY = (WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 4) # позиция заголовка
MENU_MUSIC_XY = (s(75), s(75)) # позиция кнопки музыки
MENU_EFFECT_XY = (s(75), s(75) + BUTTONS_SIZE[0]) # позиция кнопки звука

CHAR_SIZE = (s(85), s(85)) # размер персонажа
CHAR_SPEED = 9 # скорость персонажа
CHAR_ANIMATION_SPEED = 0.07 # скорость анимации персонажа
CHAR_XY = (s(400), WINDOW_SIZE[1] // 2) # позиция персонажа
CHAR_HP = 100 # хп игрока
CHAR_HIT_DAMAGE = 10 # урон при столкновении с метеоритом
CHAR_HP_XY = (WINDOW_SIZE[0] // 2, BUTTONS_SIZE[0] // 2) # позиция текста хп
CHAR_WAVE_XY = (WINDOW_SIZE[0] // 2, BUTTONS_SIZE[0]) # позиция номера волны
CHAR_TIMER_XY = (WINDOW_SIZE[0] // 2, 3 * BUTTONS_SIZE[0] // 2) # 
CHAR_DEAD_XY = (WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2) # позиция текста проигрыша
CHAR_BOUNDS_W = CHAR_SIZE[0] # граница движения вверх
CHAR_BOUNDS_A = CHAR_SIZE[0] # граница движения влево
CHAR_BOUNDS_S = WINDOW_SIZE[1] - 2 * CHAR_SIZE[0] # граница движения вниз
CHAR_BOUNDS_D = WINDOW_SIZE[0] - 2 * CHAR_SIZE[0] # граница движения вправо

BULLET_SIZE = (s(10), s(10)) # размер пули
BULLET_CRIT_SIZE = (s(15), s(15)) # размер крит пули
BULLET_SPEED = 14 # скорость пули
BULLET_DAMAGE = 20 # урон пули
BULLET_POOL_SIZE = 3 # лимит пуль
BULLET_CRIT_BASE_CHANCE = 0.1 # шанс крита
BULLET_CRIT_DAMAGE = BULLET_DAMAGE * 2 # урон крита
BULLET_CRIT_C = 0.015 # константа из таблицы

METEOR_SIZE_RANGE = (s(60), s(110)) # диапазон размера метеорита
METEOR_HP = 100 # хп метеорита
METEOR_SPEED_RANGE = (5, 12) # диапазон скорости метеорита
METEOR_SPAWN_INTERVAL = 0.5 # интервал появления метеоритов
METEOR_POOL_SIZE = 20 # количество метеоритов в пуле
METEOR_NEXT_WAVE_INTERVAL = 5 # интервал между волнами
METEOR_SPEED_MULTIPLIER = 0.03 # скорость зависит от номера волны
METEOR_BASE_WAVE_DURATION = 8 # продолжительность волны зависит от номера волны

DEAD_SCREEN_DURATION = 7 # продолжительность окна смерти