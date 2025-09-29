from string import *
x = str(input('строка с маленькой буквы:'))
wh =int(input('1 если шифр, 0 если дешифр:'))
def f(x, wh):
    alp = ''
    rus = 0
    if any(i in x for i in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'):
        rus = 1

    if rus == 1:
        alp = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    if rus == 0:
        alp = ascii_lowercase

    if wh == 1:
        y = ''
        c = 1
        for i in x:
            bb = alp.index(i)
            bbb = bb + c
            y += alp[bbb]
        return y
    if wh == 0:
        y = ''
        c = 1
        for i in x:
            bb = alp.index(i)
            bbb = bb - c
            y += alp[bbb]
        return y

print(f(x, wh))
