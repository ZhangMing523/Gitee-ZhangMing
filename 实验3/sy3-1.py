a={'姓名':'小明','身高':'1.75m','体重':'80.5kg'}
print(a)
BIM=(80.5/(1.75**2))
print(BIM)
if BIM<18.5:
    print("过轻")
elif 18.5 <= BIM<25:
    print("正常")
elif 25 <= BIM< 28:
    print("过重")
elif 28 < BIM <= 32:
    print("肥胖")
elif BIM>32:
    print("严重肥胖")
