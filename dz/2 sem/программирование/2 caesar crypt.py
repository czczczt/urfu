ascii_lowercase = 'abcdefghijklmnopqrstuvwxyz'
ascii_uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
ascii_letters = ascii_lowercase + ascii_uppercase

def caesar_encrypt(text: str, key: str) -> str:
    txta = [i for i in text]
    txta_without = [i for i in text if i != ' ']
    stra = [i for i in key]
    if len (txta_without) > len(stra):
        stra_for_txta = (stra * (len(txta_without) - len(stra)))[:len(txta_without)]
    if len (txta_without) < len(stra):
        stra_for_txta = stra[:len(txta_without)]
    if len (txta_without) == len(stra):
        stra_for_txta = stra

    w = 0
    q = 0
    g = 0
    for i in txta:
        if i not in ascii_letters:
            q += 1
            g = g - 1
            continue

        if i in ascii_uppercase and stra_for_txta[q + g] in ascii_uppercase:
            w = (ascii_uppercase.index(i) + ascii_uppercase.index(stra_for_txta[q + g])) % 26
            txta[q] = ascii_uppercase[w]

        if i in ascii_uppercase and stra_for_txta[q + g] in ascii_lowercase:
            w = (ascii_uppercase.index(i) + ascii_lowercase.index(stra_for_txta[q + g])) % 26
            txta[q] = ascii_uppercase[w]

        if i in ascii_lowercase and stra_for_txta[q + g] in ascii_uppercase:
            w = (ascii_lowercase.index(i) + ascii_uppercase.index(stra_for_txta[q + g])) % 26
            txta[q] = ascii_lowercase[w]

        if i in ascii_lowercase and stra_for_txta[q + g] in ascii_lowercase:
            w = (ascii_lowercase.index(i) + ascii_lowercase.index(stra_for_txta[q + g])) % 26
            txta[q] = ascii_lowercase[w]

        q += 1

    a = ''
    for i in txta:
        a += i
    return a


def caesar_decrypt(text: str, key: str) -> str:
    txta = [i for i in text]
    txta_without = [i for i in text if i != ' ']
    stra = [i for i in key]
    if len (txta_without) > len(stra):
        stra_for_txta = (stra * (len(txta_without) - len(stra)))[:len(txta_without)]
    if len (txta_without) < len(stra):
        stra_for_txta = stra[:len(txta_without)]
    if len (txta_without) == len(stra):
        stra_for_txta = stra

    w = 0
    q = 0
    g = 0
    for i in txta:
        if i not in ascii_letters:
            q += 1
            g = g - 1
            continue

        if i in ascii_uppercase and stra_for_txta[q + g] in ascii_uppercase:
            w = (ascii_uppercase.index(i) - ascii_uppercase.index(stra_for_txta[q + g])) % 26
            txta[q] = ascii_uppercase[w]

        if i in ascii_uppercase and stra_for_txta[q + g] in ascii_lowercase:
            w = (ascii_uppercase.index(i) - ascii_lowercase.index(stra_for_txta[q + g])) % 26
            txta[q] = ascii_uppercase[w]

        if i in ascii_lowercase and stra_for_txta[q + g] in ascii_uppercase:
            w = (ascii_lowercase.index(i) - ascii_uppercase.index(stra_for_txta[q + g])) % 26
            txta[q] = ascii_lowercase[w]

        if i in ascii_lowercase and stra_for_txta[q + g] in ascii_lowercase:
            w = (ascii_lowercase.index(i) - ascii_lowercase.index(stra_for_txta[q + g])) % 26
            txta[q] = ascii_lowercase[w]
            
        q += 1

    a = ''
    for i in txta:
        a += i
    return a