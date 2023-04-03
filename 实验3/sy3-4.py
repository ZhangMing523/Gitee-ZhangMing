for  i in range(100,1000):
     ge =i%10
     shi=i//10 %10
     bai=i//100
     if i==ge**3 +shi ** 3+bai**bai:
         print("水仙花数分别是：" ,i)
