from random import randint

class Herro:
    def __init__(self, hp, gold, damage):
        self.hp = hp
        self.gold = gold
        self.damage = damage

    def info(self):
        return f'hp {self.hp}, gold {self.gold}, damage {self.damage}'

    def kick(self, other):
        return Dragon(other.hp - self.damage, other.gold, other.damage), Herro(self.hp-other.damage, self.gold, self.damage)

    def work(self):
        return Herro(self.hp, self.gold + 5000, self.damage)

    def dolg(self):
        return Herro(self.hp, self.gold-100000, self.damage)

    def sportiki(self):
        return Herro(self.hp-50, self.gold-100000, self.damage)

    def sword(self):
        return Herro(self.hp, self.gold-15000, self.damage+145)

    def apple(self):
        return Herro(self.hp+30, self.gold-2500, self.damage)

    def slot(self):
        w = randint(1, 10)
        if w % 2 == 0:
            return Herro(self.hp, self.gold+10000, self.damage)
        if w % 2 != 0:
            return Herro(self.hp, self.gold-10000, self.damage)
        

class Dragon(Herro):
    def __init__(self, hp, gold, damage):
        self.hp = hp
        self.gold = gold
        self.damage = damage

    def die(self):
        if self.hp <= 0:
            return 1

    def add(self, other):
        return Herro(other.hp, other.gold + self.gold, other.damage), Dragon(self.hp, 0, 0)



her = Herro(90, -1000, 5)
drag = Dragon(1000, 100000, 20)

print('Главный герой этой игры - лудоман. Вам предстоит помочь ему накопить 100000 золота, чтобы выбраться из финансовой ямы/')
print('Герой знает, что дракон никогда не крутил слоты и он решает убить его, чтобы забрать его накопления.')
print('Но, возможно, убийство это не единственное решение этой проблемы/')
print('')

p = 1
sportiki = 0
commands = ['kick', 'work', 'shop', 'slot']
shopl = {'apple':2500, 'sword':15000}
live = 1

while p:
    print(f'герой: {her.info()}',"    ", f'дракон: {drag.info()}')
    print(f'комманды: {commands}')
    action = input('действие:')
    print('')

    if action == 'shop':
        print(shopl)
        shopw = input('введите название товара:')
        if shopw in shopl and her.gold >= shopl[f'{shopw}']:
            if shopw == 'apple':
                her = her.apple()
                commands.append('buy apple')
            if shopw == 'sword':
                her = her.sword()
                del shopl['sword']
        elif shopw not in shopl:
            print('Такого товара нет')
        elif her.gold < shopl[f'{shopw}']:
            print('Недостаточно средств')

    if action == 'buy apple':
        her = her.apple()
        
    if action == 'slot':
        her = her.slot()

    if action == 'kick' and drag.hp > 0:
        drag, her = her.kick(drag)

    if action == 'work':
        her = her.work()

    if drag.die() == 1 and drag.gold > 0:
        her, drag = drag.add(her)
        print(f'Вы убили дракона, ваш баланс: {her.gold}')
        live = 0

    if sportiki == 1 and her.gold >= 100000:
        rand = randint(1, 2)
        if rand == 1:
            print('Вы решили не отдавать долг, за вами приехали спортики')
            if her.hp > 50:
                print("Вы помогли герою рассплатиться с долгами, игра закончена")
                p = 0
            her = her.sportiki()

    if sportiki == 0 and her.gold >= 100000:
        print('Главный герой может расплатиться с долгами')
        sportiki = 1
        commands.append('dolg')

    if action == 'dolg' and live == 0:
        her = her.dolg()
        print("Вы помогли герою рассплатиться с долгами. Так как вы убили дракона, началось расследование.")
        print('Полиция быстро вычеслила преступника по отпечаткам, героя посадили на 10 лет общего режима')
        print('Игра окончена')
        p = 0

    if action == 'dolg' and live == 1:
        her = her.dolg()
        print("Вы помогли герою рассплатиться с долгами. Так как вы не убили дракона, герою, кроме лудомании, больше ничего не угрожает")
        print('Игра окончена')
        p = 0

    if her.hp <= 0:
        print('Герой умер')
        print('Вы не смогли ему помочь, игра закончена')
        p = 0