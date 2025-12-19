from datetime import date
from decimal import Decimal

DATE_FORMAT = '%Y-%m-%d'


def add(title, amt, exp_dt, goods):
    if title not in goods:
        goods[title] = []

    goods[title].append({
        'amount': amt,
        'expiration_date': exp_dt
    })
    return goods


def add_by_note(note, goods):
    parts = note.split()

    if len(parts) < 2:
        print('ошибка: нужны название и количество')
        return goods

    date_str = parts[-1]
    is_date = False

    if len(date_str.split('-')) == 3:
        is_date = True

    if is_date and len(parts) > 2:
        title = ' '.join(parts[:-2])
        amt = Decimal(parts[-2])
        exp_dt = date.fromisoformat(date_str)
    else:
        title = ' '.join(parts[:-1])
        amt = Decimal(parts[-1])
        exp_dt = None

    return add(title, amt, exp_dt, goods)


def amount(query, goods):
    query_low = query.lower()
    total = Decimal('0')

    for title in goods:
        if query_low in title.lower():
            for batch in goods[title]:
                total += batch['amount']

    return total


def add_handler(goods):
    t = input('название продукта: ')
    a = Decimal(input('количество: '))
    d = input('срок годности (ГГГГ-ММ-ДД, можно пусто): ')
    if d:
        e = date.fromisoformat(d)
    else:
        e = None
    add(t, a, e, goods)
    print('добавлено')


def add_note_handler(goods):
    note = input('название количество дата (опционально): ')
    add_by_note(note, goods)
    print('добавлено')


def info_handler(goods):
    print(goods)


def amount_handler(goods):
    q = input('название продукта: ')
    print(amount(q, goods))


goods = {}

while 1:
    cmds = ('добавить', 'добавить по записке', 'информация', 'количество')
    cmd = input(f'введите операцию {cmds}: ')

    if cmd not in cmds:
        print('такой команды нет')
        continue

    if cmd == 'добавить':
        add_handler(goods)

    if cmd == 'добавить по записке':
        add_note_handler(goods)

    if cmd == 'информация':
        info_handler(goods)

    if cmd == 'количество':
        amount_handler(goods)
