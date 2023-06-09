import numpy as np
arr = np.linspace(1, 10, 20)
matrix = arr.reshape((2, 10))
row_sums = matrix.sum(axis=1)
print(matrix)
print(row_sums)
