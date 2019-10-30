import backend.finance.indicators.bollinger_band as bb
import random

# a = [random.randint(1, 6) for i in range(50)]
a = [6, 4, 4, 1, 3, 5, 4, 1, 3, 4, 1, 6, 6, 4, 5, 2, 2, 3, 2, 4, 3, 2, 4, 2, 1, 2, 6, 6, 5, 4, 1, 6, 6, 5, 3, 4, 6, 5, 5, 4, 5, 2, 3, 6, 2, 1, 1, 5, 5, 3]
aa = []
for i in range(len(a)):
    aa += [bb._std_dev(a[:i+1], 10)]

print(a)
for i in range(len(a)):
    print(i+1, aa[i])