H_maybe = set()
S_maybe = set()
V_maybe = set()
from fractions import Fraction

import itertools

# 一次性生成所有组合
colors = itertools.product(
    (
        Fraction(x, 255) for x in range(256)
    ), 
    repeat=3)

for r, g, b in colors:
    V = max(r,g,b)
    if V == 0:
        S = Fraction(0); H = None #H=NaN
    else:
        delta = V - min(r, g, b)
        S = delta / V
        
        if S == 0:
            H = None
        else:
            if V == r:
                H = (g - b) / delta
            elif V == g:
                H = (b - r) / delta + Fraction(2)
            else:  # V == b
                H = (r - g) / delta + Fraction(4)
            
            # H原本是0-6范围，除以6归一化到0-1
            H = Fraction(1, 6) * H

            if H < 0:
                H += 1
            elif H > 1:
                H -= 1
    H_maybe.add(H)
    S_maybe.add(S)
    V_maybe.add(V)

print(len(H_maybe), len(S_maybe), len(V_maybe))