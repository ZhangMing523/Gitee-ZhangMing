import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors

# 读取数据
movies_df = pd.read_csv('movies.csv')
rating_df = pd.read_csv('ratings.csv')

# 打印前几行数据
print(movies_df.head())
print(rating_df.head())

# 删除不需要的列
movies_df.drop('genres', axis=1, inplace=True)
rating_df.drop('timestamp', axis=1, inplace=True)

# 打印处理后的数据
print(movies_df.head())
print(rating_df.head())

# 合并数据集
df = pd.merge(rating_df, movies_df, on='movieId')
print(df.head())

# 检查缺失值
print(df.isna().sum())

# 可视化评分分布
plt.figure(figsize=(8, 4))
sns.countplot(x="rating", data=rating_df)
plt.show()

# 可视化观看次数最多的前10部电影
top_10_movies = df.groupby("title").size().sort_values(ascending=False)[:10]
plt.figure(figsize=(8, 4))
top_10_movies.plot(kind="barh")
plt.xlabel("Viewership Count")
plt.ylabel("Title")
plt.show()

# 计算每部电影的评分次数
combine_movie_rating = df.dropna(axis=0, subset=['title'])
movie_ratingCount = (combine_movie_rating.
     groupby(by=['title'])['rating'].
     count().
     reset_index().
     rename(columns={'rating': 'totalRatingCount'})
     [['title', 'totalRatingCount']])
print(movie_ratingCount.head())

# 合并评分次数数据
rating_with_totalRatingCount = combine_movie_rating.merge(movie_ratingCount, left_on='title', right_on='title', how='left')
print(rating_with_totalRatingCount.head())

# 设置浮点数显示格式
pd.set_option('display.float_format', lambda x: '%.3f' % x)
print(movie_ratingCount['totalRatingCount'].describe())

print(rating_with_totalRatingCount.shape)

# 打印评分次数的分位数
print(rating_with_totalRatingCount['totalRatingCount'].quantile(np.arange(.6, 1, .02)))

# 筛选受欢迎的电影
popularity_threshold = 50
rating_popular_movie = rating_with_totalRatingCount.query('totalRatingCount >= @popularity_threshold')
print(rating_popular_movie.shape)

# 创建电影特征矩阵
movie_features_df = rating_popular_movie.pivot_table(index='title', columns='userId', values='rating').fillna(0)
print(movie_features_df.head())
print(movie_features_df.shape)

# 压缩稀疏矩阵
movie_features_df_matrix = csr_matrix(movie_features_df.values)
# 创建KNN模型
model_knn = NearestNeighbors(metric='cosine', algorithm='brute')
model_knn.fit(movie_features_df_matrix)  # 训练模型

def recommender(movie_name, data, model, n_recommendations):
    indexNamesArr = movie_features_df.index.values
    listOfRowIndexLabels = list(indexNamesArr)  # 将np数组转化为list
    movieIndex = None
    for i, m_name in enumerate(listOfRowIndexLabels):  # 遍历后备电影列表
        if movie_name in m_name:  # 搜索给定电影的下标，找到后退出循环
            movieIndex = i
            break
    if movieIndex is None:
        print(f"Movie '{movie_name}' not found in the dataset.")
        return

    distances, indices = model.kneighbors(movie_features_df.iloc[movieIndex, :].values.reshape(1, -1), n_neighbors=n_recommendations + 1)  # 根据模型找到与所选电影最近的包含自身的recommendations+1个电影
    print(f'Recommendations for {movie_features_df.index[movieIndex]}:\n')
    for i in range(1, len(distances.flatten())):  # 输出推荐的recommendations个电影
        print(f'{i}: {movie_features_df.index[indices.flatten()[i]]}, with distance of {distances.flatten()[i]:.4f}')

your_favorite = input("Enter Movie name: ")
recommender(your_favorite, movie_features_df_matrix, model_knn, 5)
