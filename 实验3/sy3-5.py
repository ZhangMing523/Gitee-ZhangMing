num=int(input("please input number:"))
for i in range(2,num):
    if num%i==0:
        print("%d is Not a prime number."%num)
        break
    else:
        print("%d is a prime number."%num)