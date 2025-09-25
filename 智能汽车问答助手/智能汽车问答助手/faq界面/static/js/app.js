// 搜索功能
async function searchAnswer() {
    const input = document.getElementById('searchInput');
    const resultsContainer = document.getElementById('searchResults');
    resultsContainer.innerHTML = '<div class="loading">正在搜索中...</div>';

    try {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `question=${encodeURIComponent(input.value)}`
        });

        const data = await response.json();

        if (data.error) {
            resultsContainer.innerHTML = `
                <div class="result-item error">
                    <i class="fas fa-exclamation-triangle"></i>
                    ${data.error}
                </div>
            `;
        } else {
            resultsContainer.innerHTML = `
                <div class="result-item">
                    <h3>${data.question}</h3>
                    <p class="answer-text">${data.answer}</p>
                </div>
            `;
        }
    } catch (error) {
        resultsContainer.innerHTML = `
            <div class="result-item error">
                <i class="fas fa-exclamation-triangle"></i>
                网络连接失败，请稍后重试
            </div>
        `;
    }
}

// 输入框回车触发搜索
document.getElementById('searchInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') searchAnswer();
});

// 表单提交动画
document.getElementById('addForm')?.addEventListener('submit', (e) => {
    const button = e.target.querySelector('button[type="submit"]');
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中...';
    button.disabled = true;
});
// 语音识别逻辑
function startVoiceRecognition() {
    const recognition = new webkitSpeechRecognition();
    recognition.lang = 'zh-CN';

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        searchInput.value = transcript;
        searchAnswer();
    };

    recognition.start();
}