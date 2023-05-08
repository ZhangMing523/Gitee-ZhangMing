import jieba
txt = open(r"西游记.txt", "rb").read()
excludes = {"一个", "那里", "怎么", "我们", "不知", "两个", "甚么", "只见", "不是", "原来", "不敢", "闻言", "如何", "什么"}
words = jieba.lcut(txt)
counts = {}
for word in words:
    if len(word) ==1:
        continue
    elif word == "行者" or word == "大圣" or word =="老孙":
        rword = "悟空"
    elif word == "师父" or word == "三藏" or word == "长老":
        rword = "唐僧"
    elif word == "悟净" or word == "沙和尚":
        rword = "沙僧"
    else:
        rword = word
        counts[rword] = counts.get(rword, 0)+1
    for word in excludes:
        del counts[word]
    items = list(counts.items())
    items.sort(key=lambda x: x[1], reverse=True)
    for i in range(9):
        word, count = items[i]
        print("{0:<5}{1:>5}次".format(word, count))
from wordcloud import WordCloudimport
matplotlib.pyplot as plt
wordcloud = WordCloud(background_color="white", font_step=4, width=1000, height=860, margin=2)generate_from_frequencies(word_dict)
plt
imshow(wordcloud, interpolation="bilinear")
pltaxis("off")
plt
show()
repr(``)