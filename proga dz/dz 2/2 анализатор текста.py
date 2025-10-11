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

print(f'количество глассных:{glas}, количество неглассных:{neglas}, количество пробелов: {probel}, количество слов: {probel+1}, ')

top3 = sorted(set(a), key=lambda c: a.count(c), reverse=True)[:3]
top3_counts = [(char, a.count(char)) for char in top3]
print('Топ 3 самых часто встречающихся символов:', top3_counts)