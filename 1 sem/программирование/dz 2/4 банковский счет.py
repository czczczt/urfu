bb = 0
sch = {"osnova": 500}

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
    for i in sch:
        if f in sch and t in sch:
            sch[f] -= bb
            sch[t] += bb
        else: 
            print('такого счета нет')
    return sch
            

while 1:
    aa = str(input('введите операцию(перевод, пополнение, списание, проверка, создание):'))

    if aa == 'пополнение' or aa == 'списание':
        print(f'ваш баланс:{sch["osnova"]}')
        bb = int(input('введите сумму:'))

    if aa not in ['перевод', 'пополнение', 'списание', 'проверка', 'создание']:
        print('такой команды нет')
        continue
    

    if aa == 'пополнение':
        sch = popol(bb, sch)
        print(f'ваш баланс: {sch["osnova"]}')

    if aa == 'списание': 
        sch = spis(bb, sch)
        print(f'ваш баланс: {sch["osnova"]}')

    if aa == 'проверка':
        print(prov(sch))

    if aa == 'создание':
        print(sozd(sch))

    if aa == 'перевод':
        print(perevod(sch, bb))

    for i in sch:
        if sch[i] < 0:
            print('ваш баланс отрицательный, коллекторы уже выехали')
