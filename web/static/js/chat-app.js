/**
 * Genesis X Chat Application
 * 增强版聊天应用 - 支持实时更新、表情、命令等
 */

(function() {
    'use strict';

    // ============================================================================
    // 配置
    // ============================================================================

    const CONFIG = {
        UPDATE_INTERVAL: 2000,        // 状态更新间隔
        RECONNECT_DELAY: 3000,        // 重连延迟
        MAX_MESSAGE_HISTORY: 100,     // 最大消息历史
        TYPING_TIMEOUT: 30000,        // 打字超时
        ANIMATION_DURATION: 300,      // 动画持续时间
    };

    // ============================================================================
    // 应用状态
    // ============================================================================

    const AppState = {
        isConnected: false,
        isTyping: false,
        currentMessage: '',
        messageHistory: [],
        lastStatus: null,
        reconnectTimer: null,
        updateTimer: null,
        typingTimer: null
    };

    // ============================================================================
    // DOM 元素引用
    // ============================================================================

    const DOM = {
        chatMessages: null,
        chatForm: null,
        chatInput: null,
        sendButton: null,

        // 侧边栏元素
        sideTick: null,
        sideStage: null,
        sideMemory: null,

        // 状态元素
        headerEnergy: null,
        headerMood: null,
        headerStress: null,

        // 器官元素
        organsGrid: null,

        // 循环阶段
        cycleStage: null,
        stageText: null,

        // 重启按钮
        restartBtn: null,

        // 初始化DOM引用
        init() {
            this.chatMessages = document.getElementById('chat-messages');
            this.chatForm = document.getElementById('chat-form');
            this.chatInput = document.getElementById('chat-input');
            this.sendButton = document.getElementById('send-button');

            this.sideTick = document.getElementById('side-tick');
            this.sideStage = document.getElementById('side-stage');
            this.sideMemory = document.getElementById('side-memory');

            this.headerEnergy = document.getElementById('header-energy');
            this.headerMood = document.getElementById('header-mood');
            this.headerStress = document.getElementById('header-stress');

            this.organsGrid = document.getElementById('organs-grid');

            this.cycleStage = document.getElementById('cycle-stage');
            this.stageText = document.getElementById('stage-text');

            this.restartBtn = document.getElementById('restart-btn');

            // 调试：打印找到的元素
            console.log('DOM elements found:', {
                chatMessages: !!this.chatMessages,
                chatForm: !!this.chatForm,
                organsGrid: !!this.organsGrid,
                restartBtn: !!this.restartBtn
            });
        }
    };

    // ============================================================================
    // 阶段名称映射
    // ============================================================================

    const CYCLE_STAGES = {
        'init': '初始化',
        'body_update': '身体更新',
        'observe': '观察环境',
        'retrieve': '检索记忆',
        'axiology': '价值计算',
        'goal_compile': '目标编译',
        'organ_proposals': '器官提案',
        'plan_evaluate': '计划评估',
        'safety_check': '安全检查',
        'execute': '执行动作',
        'reward_affect': '奖赏情感',
        'memory_write': '写入记忆',
        'invariants': '不变量检查',
        'value_learn': '价值学习',
        'sleep_reflect_trigger': '睡眠反思',
        'persist_override': '持久化覆盖'
    };

    const DEVELOPMENT_STAGES = {
        0: '胚胎',
        100: '幼年',
        500: '成年',
        5000: '长老'
    };

    // ============================================================================
    // 工具函数
    // ============================================================================

    const Utils = {
        // HTML转义
        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },

        // 格式化时间
        formatTime(isoString) {
            const date = new Date(isoString);
            return date.toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit'
            });
        },

        // 防抖
        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        // 节流
        throttle(func, limit) {
            let inThrottle;
            return function(...args) {
                if (!inThrottle) {
                    func.apply(this, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        },

        // 获取发育阶段
        getDevelopmentStage(tick) {
            for (const [threshold, stage] of Object.entries(DEVELOPMENT_STAGES).sort((a, b) => b[0] - a[0])) {
                if (tick >= parseInt(threshold)) {
                    return stage;
                }
            }
            return '胚胎';
        },

        // 创建元素
        createElement(tag, className, html) {
            const el = document.createElement(tag);
            if (className) el.className = className;
            if (html) el.innerHTML = html;
            return el;
        }
    };

    // ============================================================================
    // 消息管理
    // ============================================================================

    const MessageManager = {
        // 添加消息
        add(type, content, options = {}) {
            const messageDiv = Utils.createElement('div', `message ${type}`);

            const avatar = this.getAvatar(type);
            const bubble = this.getBubble(type, content, options);

            messageDiv.innerHTML = avatar + bubble;

            if (options.timestamp) {
                const timeEl = Utils.createElement('div', 'message-time');
                timeEl.textContent = Utils.formatTime(options.timestamp);
                messageDiv.querySelector('.message-bubble').appendChild(timeEl);
            }

            DOM.chatMessages.appendChild(messageDiv);
            this.scrollToBottom();

            // 保存到历史
            if (type === 'user' || type === 'assistant') {
                AppState.messageHistory.push({ type, content, timestamp: options.timestamp });
                if (AppState.messageHistory.length > CONFIG.MAX_MESSAGE_HISTORY) {
                    AppState.messageHistory.shift();
                }
            }

            return messageDiv;
        },

        // 获取头像HTML
        getAvatar(type) {
            if (type === 'user') {
                return '<div class="message-avatar"><i class="fas fa-user"></i></div>';
            }
            return '<div class="message-avatar"><i class="fas fa-robot"></i></div>';
        },

        // 获取消息气泡HTML
        getBubble(type, content, options) {
            let html = Utils.escapeHtml(content);

            // 处理代码块
            html = this.formatCodeBlocks(html);

            // 处理链接
            html = this.formatLinks(html);

            return `<div class="message-bubble">${html}</div>`;
        },

        // 格式化代码块
        formatCodeBlocks(text) {
            return text.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
                return `<pre class="code-block"><code class="language-${lang || 'text'}">${Utils.escapeHtml(code.trim())}</code></pre>`;
            });
        },

        // 格式化链接
        formatLinks(text) {
            return text.replace(
                /(https?:\/\/[^\s<]+)/g,
                '<a href="$1" target="_blank" rel="noopener" class="message-link">$1</a>'
            );
        },

        // 显示打字指示器
        showTyping() {
            if (AppState.isTyping) return;

            AppState.isTyping = true;
            const typingDiv = Utils.createElement('div', 'message assistant typing-message');
            typingDiv.innerHTML = `
                <div class="message-avatar"><i class="fas fa-robot"></i></div>
                <div class="message-bubble">
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            `;
            DOM.chatMessages.appendChild(typingDiv);
            this.scrollToBottom();

            // 设置超时
            AppState.typingTimer = setTimeout(() => {
                this.hideTyping();
            }, CONFIG.TYPING_TIMEOUT);

            return typingDiv;
        },

        // 隐藏打字指示器
        hideTyping() {
            const typingEl = DOM.chatMessages.querySelector('.typing-message');
            if (typingEl) {
                typingEl.remove();
            }
            AppState.isTyping = false;
            if (AppState.typingTimer) {
                clearTimeout(AppState.typingTimer);
            }
        },

        // 滚动到底部
        scrollToBottom(smooth = true) {
            const scrollOptions = smooth ? { behavior: 'smooth' } : {};
            DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
        },

        // 清空消息
        clear() {
            DOM.chatMessages.innerHTML = '';
            AppState.messageHistory = [];
        }
    };

    // ============================================================================
    // 状态管理
    // ============================================================================

    const StatusManager = {
        // 更新快速统计
        updateQuickStats(status, metrics) {
            const tick = status.tick || 0;
            DOM.sideTick.textContent = tick;

            const stage = Utils.getDevelopmentStage(tick);
            DOM.sideStage.textContent = stage;

            const memoryCount = metrics.episodic_count || 0;
            DOM.sideMemory.textContent = memoryCount > 999 ? '999+' : memoryCount;
        },

        // 更新情感状态
        updateEmotions(status) {
            const energy = Math.round((status.energy || 0) * 100);
            const mood = Math.round((status.mood || 0) * 100);
            const stress = Math.round((status.stress || 0) * 100);

            // 侧边栏情感
            this.updateProgressBar('emotion-energy', energy, '#f59e0b', '#fbbf24');
            this.updateProgressBar('emotion-mood', mood, '#10b981', '#34d399');
            this.updateProgressBar('emotion-stress', stress, '#ef4444', '#f87171');

            // 头部情感
            DOM.headerEnergy.textContent = `${energy}%`;
            DOM.headerMood.textContent = `${mood}%`;
            DOM.headerStress.textContent = `${stress}%`;

            // 更新颜色
            this.updateEmotionColor(DOM.headerEnergy, energy, 'energy');
            this.updateEmotionColor(DOM.headerMood, mood, 'mood');
            this.updateEmotionColor(DOM.headerStress, stress, 'stress');
        },

        // 更新进度条
        updateProgressBar(id, value, color1, color2) {
            const bar = document.getElementById(id);
            const pct = document.getElementById(`pct-${id.split('-')[1]}`);
            if (bar) {
                bar.style.width = `${value}%`;
                bar.style.background = `linear-gradient(90deg, ${color1}, ${color2})`;
            }
            if (pct) {
                pct.textContent = `${value}%`;
            }
        },

        // 更新情感颜色
        updateEmotionColor(el, value, type) {
            if (!el) return;

            let color;
            if (type === 'energy' || type === 'mood') {
                if (value > 70) color = '#10b981';
                else if (value > 40) color = '#f59e0b';
                else color = '#ef4444';
            } else if (type === 'stress') {
                if (value < 30) color = '#10b981';
                else if (value < 60) color = '#f59e0b';
                else color = '#ef4444';
            }

            el.parentElement.style.color = color;
        },

        // 更新价值维度
        updateValues(status) {
            const values = status.values || {};
            const dimensions = ['homeostasis', 'attachment', 'curiosity', 'competence', 'safety'];

            dimensions.forEach(dim => {
                const val = Math.round((values[dim] || 0) * 100);
                const bar = document.getElementById(`val-${dim}`);
                const pct = document.getElementById(`pct-${dim}`);

                if (bar) bar.style.width = `${val}%`;
                if (pct) pct.textContent = `${val}%`;
            });
        },

        // 更新器官状态
        updateOrgans(status) {
            const organs = status.organs || {};
            const organIds = ['mind', 'caretaker', 'scout', 'builder', 'archivist', 'immune'];

            organIds.forEach(organ => {
                // 直接通过ID查找，不依赖organsGrid
                const card = document.querySelector(`[data-organ="${organ}"]`);
                const statusEl = document.getElementById(`organ-${organ}`);
                const isActive = organs[organ]?.active !== false;

                if (card && statusEl) {
                    if (isActive) {
                        card.classList.add('active');
                        statusEl.textContent = '活跃';
                    } else {
                        card.classList.remove('active');
                        statusEl.textContent = '休眠';
                    }
                } else {
                    // 调试信息
                    if (!card) console.warn(`Organ card not found: ${organ}`);
                    if (!statusEl) console.warn(`Organ status element not found: organ-${organ}`);
                }
            });
        },

        // 更新循环阶段
        updateCycleStage(status) {
            const currentStage = status.current_stage || 'init';
            const stageName = CYCLE_STAGES[currentStage] || currentStage;

            if (DOM.stageText) {
                DOM.stageText.textContent = stageName;
            }

            // 添加阶段变化动画
            if (DOM.cycleStage && AppState.lastStatus?.current_stage !== currentStage) {
                DOM.cycleStage.style.animation = 'none';
                DOM.cycleStage.offsetHeight; // 触发重排
                DOM.cycleStage.style.animation = 'fadeIn 0.3s ease';
            }
        },

        // 完整状态更新
        async update() {
            try {
                const [statusRes, metricsRes] = await Promise.all([
                    fetch('/api/status'),
                    fetch('/api/metrics')
                ]);

                const status = await statusRes.json();
                const metrics = await metricsRes.json();

                // 检查是否有变化
                const hasChanged = JSON.stringify(status) !== JSON.stringify(AppState.lastStatus);
                AppState.lastStatus = status;

                // 更新各个部分
                this.updateQuickStats(status, metrics);
                this.updateEmotions(status);
                this.updateValues(status);
                this.updateOrgans(status);
                this.updateCycleStage(status);

            } catch (error) {
                console.error('Status update failed:', error);
            }
        }
    };

    // ============================================================================
    // API 调用
    // ============================================================================

    const API = {
        async send(message, user = 'User') {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, user })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        },

        async restart() {
            const response = await fetch('/api/restart-system', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            return await response.json();
        },

        async getStatus() {
            const response = await fetch('/api/status');
            return await response.json();
        },

        async getMetrics() {
            const response = await fetch('/api/metrics');
            return await response.json();
        },

        async getMessages() {
            const response = await fetch('/api/messages');
            return await response.json();
        }
    };

    // ============================================================================
    // 事件处理
    // ============================================================================

    const EventHandler = {
        // 发送消息
        async sendMessage(message) {
            if (!message?.trim()) return;

            MessageManager.add('user', message, {
                timestamp: new Date().toISOString()
            });

            DOM.chatInput.value = '';
            DOM.chatInput.style.height = 'auto';

            DOM.chatInput.disabled = true;
            DOM.sendButton.disabled = true;

            const typingIndicator = MessageManager.showTyping();

            try {
                const data = await API.send(message);

                MessageManager.hideTyping();
                MessageManager.add('assistant', data.response, {
                    timestamp: data.timestamp || new Date().toISOString()
                });

                await StatusManager.update();

            } catch (error) {
                MessageManager.hideTyping();
                MessageManager.add('system', '错误: ' + error.message);
            } finally {
                DOM.chatInput.disabled = false;
                DOM.sendButton.disabled = false;
                DOM.chatInput.focus();
            }
        },

        // 重启系统
        async restartSystem() {
            if (!DOM.restartBtn) return;

            DOM.restartBtn.classList.add('spinning');
            DOM.restartBtn.disabled = true;

            try {
                const data = await API.restart();

                if (data.status === 'success') {
                    MessageManager.clear();
                    MessageManager.add('system', '系统已重启，代码更新已生效！');
                    await StatusManager.update();
                } else {
                    MessageManager.add('system', '重启失败: ' + (data.error || '未知错误'));
                }
            } catch (error) {
                MessageManager.add('system', '重启错误: ' + error.message);
            } finally {
                DOM.restartBtn.classList.remove('spinning');
                DOM.restartBtn.disabled = false;
            }
        },

        // 输入处理
        handleInput(e) {
            const target = e.target;
            target.style.height = 'auto';
            target.style.height = Math.min(target.scrollHeight, 140) + 'px';
        },

        // 键盘快捷键
        handleKeydown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                DOM.chatForm.dispatchEvent(new Event('submit'));
            }
            // Escape 清空输入
            else if (e.key === 'Escape') {
                DOM.chatInput.value = '';
                DOM.chatInput.style.height = 'auto';
            }
        },

        // 加载历史消息
        async loadHistory() {
            try {
                const messages = await API.getMessages();

                messages.forEach(msg => {
                    if (msg.type === 'user' || msg.type === 'assistant') {
                        MessageManager.add(msg.type, msg.content, {
                            timestamp: msg.timestamp
                        });
                    }
                });

                await StatusManager.update();

            } catch (error) {
                console.error('Failed to load history:', error);
            }
        }
    };

    // ============================================================================
    // 应用初始化
    // ============================================================================

    function init() {
        // 初始化DOM引用
        DOM.init();

        // 检查必要的DOM元素
        if (!DOM.chatMessages || !DOM.chatForm) {
            console.error('Required DOM elements not found');
            return;
        }

        // 绑定事件
        DOM.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            EventHandler.sendMessage(DOM.chatInput.value);
        });

        DOM.chatInput.addEventListener('input', Utils.throttle(EventHandler.handleInput, 100));
        DOM.chatInput.addEventListener('keydown', EventHandler.handleKeydown);

        if (DOM.restartBtn) {
            DOM.restartBtn.addEventListener('click', () => EventHandler.restartSystem());
        }

        // 加载历史消息
        EventHandler.loadHistory();

        // 启动状态更新
        StatusManager.update();
        AppState.updateTimer = setInterval(() => StatusManager.update(), CONFIG.UPDATE_INTERVAL);

        // 标记为已连接
        AppState.isConnected = true;

        console.log('Genesis X Chat App initialized');
    }

    // ============================================================================
    // 导出
    // ============================================================================

    window.GenesisXChat = {
        init,
        sendMessage: (msg) => EventHandler.sendMessage(msg),
        restart: () => EventHandler.restartSystem(),
        updateStatus: () => StatusManager.update(),
        VERSION: '2.0.0'
    };

    // 自动初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
