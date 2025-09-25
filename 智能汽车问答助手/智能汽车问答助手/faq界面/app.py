from flask import Flask, render_template, request, redirect, url_for, jsonify
import jieba
import json
import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__, static_folder='static')
app.config['FAQ_DATA'] = 'faq_data.json'


# --------------------------
# 初始化配置
# --------------------------
def load_faq():
    """加载数据（文件不存在时返回空列表）"""
    if os.path.exists(app.config['FAQ_DATA']):
        try:
            with open(app.config['FAQ_DATA'], 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []  # 文件内容为空时返回空列表
    return []


def save_faq(data):
    """保存数据（含错误处理）"""
    try:
        with open(app.config['FAQ_DATA'], 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            print("✅ 数据保存成功！")
            return True
    except Exception as e:
        print("❌ 保存失败:", e)
        return False

# --------------------------
# 文本预处理
# --------------------------
def clean_text(text):
    """清理特殊字符"""
    text = re.sub(r"[^\w\s]", "", text)  # 移除标点
    text = re.sub(r"\d+", "", text)  # 移除数字
    return text.strip()


def tokenize(text):
    """分词函数"""
    text = clean_text(text)
    return " ".join(jieba.cut(text))


# --------------------------
# 模型初始化
# --------------------------
def init_model():
    """初始化TF-IDF模型"""
    faq_data = load_faq()
    if not faq_data:
        raise ValueError("FAQ数据为空，请先添加数据！")

    # 预处理文本
    questions = [tokenize(item["question"]) for item in faq_data]
    questions = [q for q in questions if q.strip() != ""]

    if not questions:
        raise ValueError("预处理后所有文本均为空，请检查数据或分词逻辑。")

    # 配置Vectorizer
    vectorizer = TfidfVectorizer(
        token_pattern=r"(?u)\b\S+\b",  # 匹配非空格字符（中文适用）
        stop_words=None  # 禁用停用词
    )
    matrix = vectorizer.fit_transform(questions)
    return vectorizer, matrix, faq_data


# 全局模型变量
try:
    tfidf_vectorizer, tfidf_matrix, faq = init_model()
except Exception as e:
    print("初始化失败:", e)
    tfidf_vectorizer, tfidf_matrix, faq = None, None, []


# --------------------------
# Flask路由
# --------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def handle_ask():
    user_question = request.form.get("question", "").strip()
    if not user_question:
        return jsonify({"error": "问题不能为空"})

    try:
        # 预处理用户问题
        user_vec = tfidf_vectorizer.transform([tokenize(user_question)])
        similarities = cosine_similarity(user_vec, tfidf_matrix)
        max_index = similarities.argmax()

        if similarities.max() < 0.3:  # 相似度阈值
            return jsonify({"error": "未找到相关答案"})
        return jsonify(faq[max_index])
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/add", methods=["GET", "POST"])
def add_data():
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        answer = request.form.get("answer", "").strip()
        if not question or not answer:
            return render_template("add.html", error="问题和答案不能为空")

        # 加载现有数据并追加新条目
        faq_data = load_faq()
        faq_data.append({"question": question, "answer": answer})

        # 保存数据并检查结果
        if save_faq(faq_data):
            return redirect(url_for("index"))
        else:
            return render_template("add.html", error="保存失败，请检查文件权限！")

    return render_template("add.html")


if __name__ == "__main__":
    app.run(port=5001)  # 使用新端口
