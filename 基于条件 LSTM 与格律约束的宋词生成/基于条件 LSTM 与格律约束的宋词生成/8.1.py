import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import random
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import re
import json
from collections import defaultdict, Counter
import datetime
import os
import matplotlib.font_manager as fm


# 设置随机种子，确保结果可复现
def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


set_seed(42)


# 数据处理类
class EnhancedTextDataset(Dataset):
    def __init__(self, data, tokenizer_type='char', seq_length=50):
        """增强版文本数据集处理类"""
        self.tokenizer_type = tokenizer_type
        self.seq_length = seq_length
        self.samples = []
        self.texts = self._clean_texts(data)
        self.char_to_idx, self.idx_to_char = self._build_vocab()
        self._create_samples()

    def _clean_texts(self, data):
        """清洗文本数据，保留中文字符"""
        cleaned_texts = []
        for item in data:
            if "paragraphs" in item:
                text = ''.join(item["paragraphs"])
                text = re.sub(r'[^\u4e00-\u9fa5]', '', text)
                if len(text) > 10:
                    cleaned_texts.append(text)
        return cleaned_texts

    def _build_vocab(self):
        """构建词汇表并添加特殊标记"""
        if self.tokenizer_type == 'char':
            all_chars = ''.join(self.texts)
            chars = [char for char, _ in Counter(all_chars).most_common(5000)]
        else:
            all_words = []
            for text in self.texts:
                all_words.extend(text.split())
            chars = [word for word, _ in Counter(all_words).most_common(5000)]

        special_tokens = ['<PAD>', '<UNK>', '<START>', '<END>']
        chars.extend(special_tokens)
        char_to_idx = {c: i for i, c in enumerate(chars)}
        idx_to_char = {i: c for i, c in enumerate(chars)}

        print(f"词汇表大小: {len(char_to_idx)}, 高频词: {chars[:10]}")
        with open('vocab.json', 'w', encoding='utf-8') as f:
            json.dump(char_to_idx, f, ensure_ascii=False, indent=2)
        return char_to_idx, idx_to_char

    def _create_samples(self):
        """创建训练样本，滑动窗口生成上下文对"""
        for text in self.texts:
            indices = [self.char_to_idx.get(c, self.char_to_idx['<UNK>']) for c in text]
            for i in range(len(indices) - self.seq_length):
                self.samples.append((
                    torch.tensor(indices[i:i + self.seq_length], dtype=torch.long),
                    torch.tensor(indices[i + self.seq_length], dtype=torch.long)
                ))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]


# 改进的循环神经网络模型，增加注意力机制
class ImprovedRNNModel(nn.Module):
    def __init__(self, vocab_size, embed_dim=192, hidden_dim=512,
                 num_layers=3, rnn_type='lstm', dropout=0.3, use_attention=True):
        super(ImprovedRNNModel, self).__init__()
        self.num_layers = num_layers  # 修复：保存num_layers为类属性
        self.hidden_dim = hidden_dim  # 修复：保存hidden_dim为类属性
        self.embed_dim = embed_dim  # 修复：保存embed_dim为类属性
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.rnn = nn.LSTM(embed_dim, hidden_dim, num_layers,
                           batch_first=True, dropout=dropout if num_layers > 1 else 0)
        self.attention = nn.Linear(hidden_dim, 1) if use_attention else None
        self.fc = nn.Linear(hidden_dim, vocab_size)
        self.init_weights()

    def init_weights(self):
        initrange = 0.1
        self.embedding.weight.data.uniform_(-initrange, initrange)
        self.fc.weight.data.uniform_(-initrange, initrange)
        self.fc.bias.data.zero_()
        if hasattr(self, 'attention'):
            self.attention.weight.data.uniform_(-initrange, initrange)
            self.attention.bias.data.zero_()

    def forward(self, x, hidden=None):
        embedded = self.embedding(x)
        batch_size = x.size(0)

        if hidden is None or hidden[0].size(1) != batch_size:
            hidden = self.init_hidden(batch_size, x.device)

        output, hidden = self.rnn(embedded, hidden)

        if self.attention:
            attn_weights = torch.softmax(self.attention(output).squeeze(-1), dim=1)
            context = torch.bmm(attn_weights.unsqueeze(1), output).squeeze(1)
            output = context
        else:
            output = output[:, -1, :]

        output = self.fc(output)
        return output, hidden

    def init_hidden(self, batch_size, device):
        weight = next(self.parameters())
        return (weight.new_zeros(self.num_layers, batch_size, self.hidden_dim).to(device),
                weight.new_zeros(self.num_layers, batch_size, self.hidden_dim).to(device))


# 模型训练函数
def train_model(model, train_loader, val_loader, criterion, optimizer, scheduler,
                epochs=20, device='cpu', clip=0.5, model_path='best_model.pth'):
    best_val_loss = float('inf')
    train_losses, val_losses, val_metrics = [], [], []

    with open('training_log.txt', 'w', encoding='utf-8') as f:
        f.write(f"训练开始时间: {datetime.datetime.now()}\n")
        f.write(f"模型参数: {sum(p.numel() for p in model.parameters())}\n")
        f.write(f"优化器: {optimizer}\n")
        f.write(f"学习率: {optimizer.param_groups[0]['lr']}\n\n")

    for epoch in range(epochs):
        model.train()
        total_loss = 0
        hidden = None

        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            if hidden is not None:
                hidden = (hidden[0].detach(), hidden[1].detach())

            optimizer.zero_grad()
            output, hidden = model(inputs, hidden)
            loss = criterion(output, targets)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), clip)
            optimizer.step()
            total_loss += loss.item()

        avg_train_loss = total_loss / len(train_loader)
        train_losses.append(avg_train_loss)

        model.eval()
        val_loss = 0
        all_preds, all_targets = [], []

        with torch.no_grad():
            hidden = None
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                if hidden is not None:
                    hidden = (hidden[0].detach(), hidden[1].detach())

                output, hidden = model(inputs, hidden)
                val_loss += criterion(output, targets).item()
                preds = output.argmax(dim=1).cpu().numpy()
                all_preds.extend(preds)
                all_targets.extend(targets.cpu().numpy())

        avg_val_loss = val_loss / len(val_loader)
        val_losses.append(avg_val_loss)

        accuracy = accuracy_score(all_targets, all_preds)
        precision = precision_score(all_targets, all_preds, average='weighted', zero_division=0)
        recall = recall_score(all_targets, all_preds, average='weighted', zero_division=0)
        f1 = f1_score(all_targets, all_preds, average='weighted', zero_division=0)
        val_metrics.append((accuracy, precision, recall, f1))

        scheduler.step(avg_val_loss)
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            torch.save(model.state_dict(), model_path)
            print(f"Epoch {epoch + 1}: 保存最佳模型，验证损失 = {best_val_loss:.4f}")

        with open('training_log.txt', 'a', encoding='utf-8') as f:
            f.write(f'Epoch {epoch + 1}/{epochs}\n')
            f.write(f'Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}\n')
            f.write(f'Val Accuracy: {accuracy:.4f}, Val Precision: {precision:.4f}\n')
            f.write(f'Val Recall: {recall:.4f}, Val F1: {f1:.4f}\n')
            f.write(f'Learning Rate: {optimizer.param_groups[0]["lr"]}\n')
            f.write('-' * 60 + '\n')

        print(f'Epoch {epoch + 1}/{epochs}')
        print(f'Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}')
        print(f'Val Accuracy: {accuracy:.4f}, Val Precision: {precision:.4f}')
        print(f'Val Recall: {recall:.4f}, Val F1: {f1:.4f}')
        print('-' * 60)

    best_epoch = np.argmax([m[3] for m in val_metrics]) + 1
    with open('training_log.txt', 'a', encoding='utf-8') as f:
        f.write(f"\n训练结束时间: {datetime.datetime.now()}\n")
        f.write(f"最佳轮次: {best_epoch}\n")
        f.write(f"最佳验证损失: {min(val_losses):.4f}\n")
        f.write(f"最佳F1分数: {max([m[3] for m in val_metrics]):.4f}\n")

    return train_losses, val_losses, val_metrics


# 文本生成函数，增强起始词处理
def generate_text(model, idx_to_char, char_to_idx, start_text='春',
                  max_length=100, temperature=0.6, device='cpu'):
    model.eval()
    start_text = re.sub(r'[^\u4e00-\u9fa5]', '', start_text).strip()

    if not start_text:
        start_text = '春'
        print("提示: 使用默认起始词'春'生成")

    for char in start_text:
        if char not in char_to_idx:
            print(f"警告: 字符 '{char}' 不在词汇表中，使用默认替代")

    indices = [char_to_idx.get(c, char_to_idx['<UNK>']) for c in start_text]
    input_tensor = torch.tensor([indices], dtype=torch.long).to(device)
    hidden = model.init_hidden(1, device)
    generated = start_text

    with torch.no_grad():
        for i in range(max_length - len(start_text)):
            output, hidden = model(input_tensor, hidden)
            probs = torch.softmax(output / temperature, dim=1)
            next_idx = torch.multinomial(probs, num_samples=1).item()
            next_char = idx_to_char[next_idx]

            # 过滤无效字符（确保生成中文字符）
            if next_char in {'<PAD>', '<UNK>', '<START>', '<END>'}:
                continue

            generated += next_char
            input_tensor = torch.tensor([[next_idx]], dtype=torch.long).to(device)

            # 提前终止条件（遇到常见结束符）
            if next_char in {'。', '！', '？', '，', '；'} and i > max_length // 2:
                break

    return generated


# 优化的宋词格律库
class CiPoetryFormats:
    @staticmethod
    def get_formats():
        return {
            "豪放": {
                "name": "水调歌头",
                "pattern": [7, 6, 7, 5, 6, 7, 3, 3, 7],
                "rhyme_positions": [1, 2, 4, 5, 6, 8, 9],
                "style": "豪放"
            },
            "婉约": {
                "name": "如梦令",
                "pattern": [6, 6, 5, 5, 6, 6],
                "rhyme_positions": [1, 2, 3, 4, 5, 6],
                "style": "婉约"
            },
            "田园": {
                "name": "浣溪沙",
                "pattern": [7, 7, 7, 7, 7, 7],
                "rhyme_positions": [1, 2, 3, 5, 6],
                "style": "田园"
            },
            "边塞": {
                "name": "渔家傲",
                "pattern": [7, 7, 3, 7, 7, 7, 3, 7, 7],
                "rhyme_positions": [1, 2, 4, 5, 6, 8, 9],
                "style": "边塞"
            },
            "宫廷": {
                "name": "菩萨蛮",
                "pattern": [7, 7, 5, 5, 7, 7, 5, 5],
                "rhyme_positions": [1, 2, 5, 6],
                "style": "宫廷"
            },
            "default": {
                "name": "七言绝句",
                "pattern": [7, 7, 7, 7],
                "rhyme_positions": [1, 2, 4],
                "style": "默认"
            }
        }


# 智能断句与格律匹配
def format_ci_poetry(text, style='default'):
    if not text:
        return "生成文本为空"

    formats = CiPoetryFormats.get_formats()
    fmt = formats.get(style, formats["default"])

    print(f"使用词牌: {fmt['name']} ({fmt['style']}风格)")
    pattern = fmt["pattern"]
    rhyme_positions = fmt["rhyme_positions"]

    lines, current_pos = [], 0
    for i, length in enumerate(pattern):
        if current_pos + length <= len(text):
            line = text[current_pos:current_pos + length]
            lines.append(line)
            current_pos += length
        else:
            lines.append(text[current_pos:])
            break

    # 处理上下阕结构
    if fmt["name"] in ["水调歌头", "渔家傲", "菩萨蛮"]:
        half = len(lines) // 2
        upper_half = lines[:half]
        lower_half = lines[half:]
        formatted = "\n".join(upper_half) + "\n\n" + "\n".join(lower_half)
    else:
        formatted = "\n".join(lines)

    # 添加词牌名和换行优化
    return f"{fmt['name']}\n{'-' * len(fmt['name'])}\n{formatted}"


# 高级文本生成函数，增强风格控制
def advanced_text_generation(model, idx_to_char, char_to_idx,
                             start_text='春', max_length=120,
                             temperature=0.7, style='豪放', device='cpu'):
    model.eval()
    formats = CiPoetryFormats.get_formats()
    fmt = formats.get(style, formats["default"])

    # 风格参数调整
    style_params = {
        "豪放": {"temperature": temperature * 1.2, "max_length": max_length + 20},
        "婉约": {"temperature": temperature * 0.8, "max_length": max_length - 10},
        "田园": {"temperature": temperature * 0.9, "max_length": max_length},
        "边塞": {"temperature": temperature * 1.1, "max_length": max_length + 10},
        "宫廷": {"temperature": temperature * 0.7, "max_length": max_length},
        "default": {"temperature": temperature, "max_length": max_length}
    }

    params = style_params.get(style, style_params["default"])
    gen_temp = params["temperature"]
    gen_length = params["max_length"]

    print(f"使用 {fmt['style']} 风格生成，词牌: {fmt['name']}, 温度: {gen_temp:.2f}")
    generated = generate_text(
        model=model,
        idx_to_char=idx_to_char,
        char_to_idx=char_to_idx,
        start_text=start_text,
        max_length=gen_length,
        temperature=gen_temp,
        device=device
    )

    # 增强连贯性处理（删除重复n-gram）
    ngram_threshold = 0.3
    coherence = calculate_coherence(generated)
    if coherence > ngram_threshold:
        generated = remove_redundant_ngrams(generated, n=3, threshold=coherence)

    return format_ci_poetry(generated, style)


# 移除冗余n-gram以增强连贯性
def remove_redundant_ngrams(text, n=3, threshold=0.3):
    if len(text) < n * 2:
        return text

    ngrams = [text[i:i + n] for i in range(len(text) - n + 1)]
    ngram_counts = Counter(ngrams)
    redundant_ngrams = [ngram for ngram, count in ngram_counts.items() if count > 1]

    if not redundant_ngrams:
        return text

    # 按出现次数排序，优先移除高频冗余
    redundant_ngrams.sort(key=lambda x: ngram_counts[x], reverse=True)

    for ngram in redundant_ngrams:
        # 只移除中间出现的重复ngram，保留首次出现
        text = text.replace(ngram, '', text.count(ngram) - 1)
        new_coherence = calculate_coherence(text)
        if new_coherence < threshold:
            break

    return text


# 计算连贯性指标
def calculate_coherence(text, n=3):
    if len(text) < n:
        return 0.0
    ngrams = [text[i:i + n] for i in range(len(text) - n + 1)]
    unique_ngrams = set(ngrams)
    return 1.0 - len(unique_ngrams) / len(ngrams) if ngrams else 0.0


# 绘制指标图表
def plot_metrics(val_metrics, train_losses, val_losses, epochs):
    accuracy, precision, recall, f1 = zip(*val_metrics)
    font_families = ['SimHei', 'WenQuanYi Micro Hei', 'Heiti TC', 'Arial Unicode MS']
    available_font = next((f for f in font_families if fm.findfont(fm.FontProperties(family=f))), 'sans-serif')

    plt.rcParams["font.family"] = available_font
    plt.rcParams["axes.unicode_minus"] = False

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), dpi=300)

    ax1.plot(train_losses, label='训练损失', color='#5DA5DA', linewidth=2)
    ax1.plot(val_losses, label='验证损失', color='#FAA43A', linewidth=2)
    ax1.set_title('训练与验证损失曲线')
    ax1.set_xlabel('训练轮次')
    ax1.set_ylabel('损失值')
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    ax1.legend()

    best_val_loss = min(val_losses)
    best_epoch = val_losses.index(best_val_loss)
    ax1.scatter(best_epoch, best_val_loss, color='red', s=50)
    ax1.annotate(f'最佳验证损失: {best_val_loss:.4f}', (best_epoch, best_val_loss),
                 xytext=(best_epoch + 1, best_val_loss + 0.1), arrowprops=dict(facecolor='black', shrink=0.05))

    ax2.plot(accuracy, label='准确率', color='#60BD68', linewidth=2)
    ax2.plot(precision, label='精确率', color='#F17CB0', linewidth=2)
    ax2.plot(recall, label='召回率', color='#B2912F', linewidth=2)
    ax2.plot(f1, label='F1分数', color='#FF9DA6', linewidth=2)
    ax2.set_title('验证集评估指标曲线')
    ax2.set_xlabel('训练轮次')
    ax2.set_ylabel('指标值')
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    ax2.legend()

    best_f1 = max(f1)
    best_epoch_f1 = f1.index(best_f1)
    ax2.scatter(best_epoch_f1, best_f1, color='red', s=50)
    ax2.annotate(f'最佳F1分数: {best_f1:.4f}', (best_epoch_f1, best_f1),
                 xytext=(best_epoch_f1 + 1, best_f1 - 0.05), arrowprops=dict(facecolor='black', shrink=0.05))

    for ax in (ax1, ax2):
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.tick_params(axis='x', labelrotation=45)

    plt.tight_layout()
    plt.savefig('metrics_visualization.png')
    print("指标图表已保存至: metrics_visualization.png")
    plt.close(fig)


# 交互式生成函数
def interactive_generation(model, idx_to_char, char_to_idx, device='cpu'):
    print("\n=== 高级宋词生成器 ===")
    print("输入起始词（仅中文字符），按回车生成宋词")
    print("输入 'q' 退出，输入 'h' 获取帮助，可指定风格如 '豪放' '婉约'")
    print("格式示例: '江南 婉约' （起始词+风格）")

    while True:
        user_input = input("\n请输入起始词 (格式: '起始词 风格'): ").strip()
        if user_input.lower() == 'q':
            break
        if user_input.lower() == 'h':
            print("\n帮助信息:")
            print("1. 风格选项: 豪放, 婉约, 田园, 边塞, 宫廷 (默认: 豪放)")
            print("2. 输入示例: '秋江 边塞' 生成边塞风格宋词")
            print("3. 直接输入起始词将使用默认风格")
            continue

        start_text, style = user_input, '豪放'
        styles = ['豪放', '婉约', '田园', '边塞', '宫廷']
        for s in styles:
            if s in user_input:
                start_text = user_input.replace(s, '').strip()
                style = s
                break

        if not start_text.strip():
            start_text = '春'
            print("提示: 起始词为空，使用默认起始词'春'")

        try:
            generated = advanced_text_generation(
                model=model,
                idx_to_char=idx_to_char,
                char_to_idx=char_to_idx,
                start_text=start_text,
                style=style,
                device=device
            )

            coherence = calculate_coherence(generated.replace('\n', ''))
            print(f"\n[起始词] {start_text} [风格] {style}")
            print(f"文本连贯性: {coherence:.4f}")
            print("-" * 40)
            print(generated)
            print("-" * 40)

            collect_feedback(generated, style)
        except Exception as e:
            print(f"生成出错: {e}")


# 收集用户反馈
def collect_feedback(generated_text, style):
    print("\n=== 反馈收集 ===")
    print(f"生成风格: {style}")
    print("生成的宋词:")
    print(generated_text)
    print("-" * 40)

    feedback = {}
    feedback["style_rating"] = input("风格匹配度 (1-5分): ")
    feedback["coherence"] = input("文本连贯性 (1-5分): ")
    feedback["aesthetic"] = input("美感评分 (1-5分): ")
    feedback["suggestions"] = input("改进建议: ")

    feedback["generated_text"] = generated_text
    feedback["timestamp"] = str(datetime.datetime.now())
    with open('feedback.json', 'a', encoding='utf-8') as f:
        json.dump(feedback, f, ensure_ascii=False)
        f.write('\n')

    print("感谢您的反馈！")


# 主函数
def main():
    print("加载数据...")
    try:
        with open('song_ci.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("错误: 未找到数据文件'song_ci.json'，请确保文件存在")
        return

    print("处理数据...")
    dataset = EnhancedTextDataset(data, tokenizer_type='char', seq_length=50)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])

    batch_size = 64
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, drop_last=False)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, drop_last=False)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")

    print("初始化模型...")
    model = ImprovedRNNModel(
        vocab_size=len(dataset.char_to_idx),
        embed_dim=192,
        hidden_dim=512,
        num_layers=3,
        use_attention=True
    ).to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.0005)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', patience=3, factor=0.5)

    print("开始训练模型...")
    model_path = 'best_improved_model.pth'
    train_losses, val_losses, val_metrics = train_model(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        criterion=criterion,
        optimizer=optimizer,
        scheduler=scheduler,
        epochs=25,
        device=device,
        model_path=model_path
    )

    analyze_metrics(val_metrics, 25)
    perplexity = calculate_perplexity(model, val_loader, device)
    print(f"模型困惑度: {perplexity:.4f}")
    plot_metrics(val_metrics, train_losses, val_losses, 25)

    model.load_state_dict(torch.load(model_path))
    print("训练完成! 开始交互式生成...")
    interactive_generation(model, dataset.idx_to_char, dataset.char_to_idx, device)


# 分析评估指标
def analyze_metrics(val_metrics, epochs):
    accuracy, precision, recall, f1 = zip(*val_metrics)
    best_epoch = np.argmax(f1) + 1

    print("\n=== 模型评估 ===")
    print(f"最佳轮次: {best_epoch}/{epochs}")
    print(f"最佳准确率: {accuracy[best_epoch - 1]:.4f}")
    print(f"最佳精确率: {precision[best_epoch - 1]:.4f}")
    print(f"最佳召回率: {recall[best_epoch - 1]:.4f}")
    print(f"最佳F1分数: {f1[best_epoch - 1]:.4f}")

    if epochs > 10:
        print("\n最近5轮趋势:")
        for i in range(-5, 0):
            idx = i + epochs
            print(f"Epoch {idx}: 准确率={accuracy[i]:.4f}, F1={f1[i]:.4f}")

    return {
        "best_epoch": best_epoch,
        "best_f1": f1[best_epoch - 1]
    }


# 计算困惑度
def calculate_perplexity(model, data_loader, device):
    model.eval()
    total_loss, total_tokens = 0, 0
    criterion = nn.CrossEntropyLoss()

    with torch.no_grad():
        hidden = None
        for inputs, targets in data_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            if hidden is not None:
                hidden = (hidden[0].detach(), hidden[1].detach())

            output, hidden = model(inputs, hidden)
            loss = criterion(output, targets)
            total_loss += loss.item() * inputs.size(0)
            total_tokens += inputs.size(0)

    perplexity = torch.exp(torch.tensor(total_loss / total_tokens)).item()
    return perplexity


if __name__ == "__main__":
    main()