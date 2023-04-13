def count(str):
    pass
    import re
    str1 = input('请输入字符串')
    alpha = 0
    space = 0
    digit = 0
    other = 0
    for i in str1:
        if re.findall(r"[A-Za-z]", i):
            alpha += 1
        elif re.findall(r"\s", i):
            space += 1
        elif re.findall(r"\d", i):
            digit += 1
        else:
            other += 1
    print(f"{str1}中的英文字母个数为：{alpha}")
    print(f"{str1}中的空格个数为：{space}")
    print(f"{str1}中的数字个数为：{digit}")
    print(f"{str1}中的其他字符个数为：{other}")
count(str)
if not count(''):
    print('测试成功')
if count('12abAB [$') == (2, 4, 1, 2):
    print('测试成功')
else:
    print('测试失败')
