x = int(input('число:'))
def f(i):
    t1 = 0
    t2 = 0
    t3 = 0

    if i % 5 == 0:
        t1 = 1
    if i % 3 == 0:
        t2 = 1
    if i % 3 != 0 and i % 5 != 0:
        t3 = 1

    if t1 and not t2: return (i, 'расфасуем по 5')
    if t2 and not t1: return (i, 'расфасуем по 3')
    if t1 and t2: return (i, 'расфасуем по 3 или по 5')
    if t1 + t2 == 0: return (i, 'не работаем')

for i in range(x, 1, -1):
    print(f(i))
