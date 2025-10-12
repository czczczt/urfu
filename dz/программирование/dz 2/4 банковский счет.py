bb = 0
sch = {"osnova": 500}


while 1:
    aa = str(input('введите операцию(перевод, пополнение, списание, проверка, создание):'))

    if aa == 'перевод' or aa == 'пополнение' or aa == 'списание':
        print(f'ваш баланс:{sch["osnova"]}')
        bb = int(input('введите сумму:'))

    if aa not in ['перевод', 'пополнение', 'списание', 'проверка', 'создание']:
        print('такой команды нет')
        continue

    def popol(bb, sch):
        sch["osnova"] += bb
        return sch

    def spis(bb, sch):
        sch["osnova"] -= bb
        return sch

    def prov(sch):
        return sch

    def sozd(sch):
        nazv = input('введите название счета:')
        balans = int(input('введите баланс:'))
        sch[nazv] = balans
        return sch

    def perevod(sch, bb):
        print(sch)
        f = input('откуда:')
        t = input('куда:')
        sch[f] -= bb
        sch[t] += bb
        return sch

    if aa == 'пополнение':
        sch = popol(bb, sch)
        print(sch["osnova"])

    if aa == 'списание':
        sch = spis(bb, sch)
        print(sch["osnova"])

    if aa == 'проверка':
        print(prov(sch))

    if aa == 'создание':
        print(sozd(sch))

    if aa == 'перевод':
        print(perevod(sch, bb))
