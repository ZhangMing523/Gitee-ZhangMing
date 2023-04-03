x=float( input("该员工的销售额:"))
if x <=3000:
    s=2000
elif x >3000 and x <= 7000:
    s=2000+x*0.1
elif x >7000 and x <=10000:
    s=2000+x*0.15
else:
    s=2000+x*0.2
print("该员工的薪水总额为: {:.2f}".format(s))