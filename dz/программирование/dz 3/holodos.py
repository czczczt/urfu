# было лень доделывать

from datetime import *

def addd(bb, cc, dd, goods):
    if bb not in goods:
        goods[bb] = [{'amount': cc, 'expiration_date': dat}]
    else:
        goods[bb].append({'amount': cc, 'expiration_date': dat})
    return goods


goods = {}
while 1:
    aal = ('добавить', '')
    aa = str(input(f'введите операцию{aal}:'))

    if aa not in aal:
        print('такой команды нет')
        continue

    if aa == 'добавить':
        bb = str(input('введите название продукта:'))
        cc = float(input('введите количество:'))
        dd = str(input('введите срок годности(ГГГГ.ММ.ДД):')) # 2000-12-20

        try:
            a = [int(i) for i in dd.split('.')]
            a1, a2, a3 = a[0], a[1], a[2]
            dat = date(a1, a2, a3)
            
        
        finally: pass


    print(addd(bb, cc, dd, goods))




# https://colab.research.google.com/drive/1KIcNPurYBJIXfs8QGoe2USLwaR5GRAUS?usp=sharing#scrollTo=cwSoZUSFT8Mi


