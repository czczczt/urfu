

aa = input(str('введите слово:'))
lenn = len(aa) 
slovo = ['_'] * lenn 
q = 6
print(slovo)

while q:
    bb = input(str('введите БУКВУ:'))

    if aa.count(bb) == 0:
        print('буква неправильная')
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
        break

if q == 0:
    print('игра окончена')
