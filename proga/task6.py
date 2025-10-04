aa = input(str('введите слово:')) # abc
lenn = len(aa) # 3
slovo = ['_'] * lenn # ___
q = 6
print(slovo)

while q:
    bb = input(str('введите БУКВУ:')) # c

    if aa.count(bb) == 0:
        print(f'буква неправильная, осталось попыток {q-1}/6')
        q -= 1
    if aa.count(bb) == 1:
        qq = aa.index(bb)
        slovo[qq] = bb

    hh = []
    kk = -1
    if aa.count(bb) > 1:
        for i in aa:
            kk += 1
            if i == bb:
                hh.append(kk)
        for i in hh:
            slovo[i] = bb
    print(slovo)



    if '_' not in slovo:
        print('вы победили')

if q == 0:
    print('игра окончена')
