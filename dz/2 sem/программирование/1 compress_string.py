from typing import List
import re

def compress_string(st: str) -> str:
    s = {}
    for ch in st:
        s[ch] = s.get(ch, 0) + 1

    for ii in s:
        q = s[ii]
        for i in range(q, 1, -1):
            if ii * i in st:
                st = st.replace(ii * i, ii + f'({i})')

    return st

def decompress_string(st: str) -> str:
    for i in re.findall(r'\(\d+\)', st):
        intt = int(i[1:-1])
        simv = st[st.index(i) - 1]
        st = st.replace(simv + i, str(intt * simv))
    return st
