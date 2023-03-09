l = [1,2]
n = int(input("斐波那契数列长度： "))
while (len(l) < n):
    l.append(l[len(l)-1] + l[len(l)-2])
    print(l)