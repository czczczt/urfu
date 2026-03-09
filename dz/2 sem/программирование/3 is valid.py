from string import digits
def is_valid_compressed_string(compressed_string: str) -> bool:
    st = compressed_string

    if st == '': return True
    if st.count(")") != st.count("("): return False
    if st[0] == '(' or st[0] == ')': return False
    if '))' in st: return False
    if '((' in st: return False
    if ')(' in st: return False
    if '()' in st: return False
    for i in digits:
        if f'(0{i})' in st: return False

    simvco = 0
    lind = []
    rind = []
    for i in st:
        if i == ('('):
            lind.append(simvco)
        if i == (')'):
            rind.append(simvco)
        simvco += 1

    for i in range(len(lind)):
        for ii in st[1+lind[i]:rind[i]]:
            if ii not in digits:
                return False

    return True