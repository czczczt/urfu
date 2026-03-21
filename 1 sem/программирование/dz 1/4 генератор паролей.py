from string import *
from random import *

aa = int(input('длина пароля:'))
bb = int(input('нижний регистр - 0, верхний регистр - 1, оба регистра- 2:'))
cc = int(input('0 без цифр, 1 с цифрами:'))
dd = int(input('0 без спец символов, 1 с спец символами:'))

def f(aa, bb, cc, dd):
    len = aa
    if bb == 0: reg = ascii_lowercase
    if bb == 1: reg = ascii_uppercase
    if bb == 2: reg = ascii_letters

    if cc == 0: dig = ''
    if cc == 1: dig = digits

    if dd == 0: spec = ''
    if dd == 1: spec = punctuation

    z = reg + dig + spec

    pas = ''
    for i in range(1, len + 1):
        pas += choice(z)

    return pas

print(f(aa, bb, cc, dd))
