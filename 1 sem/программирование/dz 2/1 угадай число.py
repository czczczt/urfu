from random import *
q = 3
a = [i for i in range(1, 100)]
b = choice(a)

while q:
    q -= 1
    c = int(input('введите число:'))

    if c < b:
        print("Загаданное число больше")
        if q == 0:
            print('вы проиграли')
    if c > b:
        print("Загаданное число меньше")
        if q == 0:
            print('вы проиграли')

    if c == b:
        print("вы победили")
        q = 0

    if q == 1:
        if b % 2 == 0:
            print('подсказка, число четное')
        if b % 2 != 0:
            print('подсказка, число нечетное')

print(f'Ответ: {b}')