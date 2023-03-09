for num in range(2, 1001):
    num_list = []
    for i in range(1, num):
        if num % i == 0:
            num_list.append(i)
    # print(num_list)
    if num == sum(num_list):
        print("{}是完数：{}".format(num, num_list))