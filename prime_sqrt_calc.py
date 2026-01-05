import math
# 一个新的想法：使用质数查表+平方根的可乘性来快速计算整数平方根
prime_dict: dict[int, float] = {}
"""质数查表，键为质数，值为该质数的平方根"""

input_max = 1919810
"""预计算的最大输入值"""

try:
    tmp_isprime: list[bool] = [True] * (input_max + 1)
    use_sieve = True
except MemoryError:
    use_sieve = False
    tmp_isprime = []
    print("无法分配足够的内存来初始化质数筛。退化到质数遍历版本。")

# 若允许使用质数筛法填充质数筛，并计算平方根
if use_sieve:
    for i in range(2, input_max + 1):
        if tmp_isprime[i]:
            # 标记质数
            prime_dict[i] = math.sqrt(i)
            # 填筛
        for j in range(i * 2, input_max + 1, i):
            tmp_isprime[j] = False
else: # 遍历法，更慢
    for i in range(2, input_max + 1):
        is_prime = True
        for p in prime_dict.keys():
            if p * p > i:
                break
            if i % p == 0:
                is_prime = False
                break
        if is_prime:
            prime_dict[i] = math.sqrt(i)

# 删掉临时变量
del tmp_isprime

def calc_sqrt(n: int) -> float:
    """计算整数n的平方根，使用质数查表和可乘性。
    
    参数:
        n: 非负整数
    
    返回:
        n的平方根
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 0.0
    result = 1.0
    # 质因数分解
    for prime in prime_dict:
        # 若质数大于n，结束A
        if prime > n:
            break
        count = 0
        # 计算质数prime在n中的指数
        while n % prime == 0:
            n //= prime
            count += 1
        # 利用质数平方根的可乘性
        for _ in range(count):
            result *= prime_dict[prime]
    
    return result

if __name__ == "__main__":
    v = 114514
    print("calc_sqrt:", calc_sqrt(v))
    print("math.sqrt:", math.sqrt(v))