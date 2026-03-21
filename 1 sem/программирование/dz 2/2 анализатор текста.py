a = str(input('введите строку:'))

alp_glas = 'aeiouyаеёиоуыэюя'
alp_neglas = 'bcdfghjklmnpqrstvwxzбвгджзйклмнпрстфхцчшщъь'

glas = 0
neglas = 0
probel = 0
for i in a:
    if i in alp_glas:
        glas += 1
    if i in alp_neglas:
        neglas += 1
    if i == ' ':
        probel += 1

print(f'количество глассных:{glas}, количество неглассных:{neglas}, количество пробелов: {probel}, количество слов: {probel+1}, ') # не знаю как подсчитать топ символов, поэтому без него =/