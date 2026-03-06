/**
 * Genesis X Unified Navigation
 * 统一导航组件 - 提供跨页面一致的导航体验
 */

(function() {
    'use strict';

    // ============================================================================
    // 配置
    // ============================================================================

    const PAGES = {
        'chat': {
            name: '对话',
            icon: 'fa-comments',
            url: '/chat',
            description: '与 Genesis X 进行对话交流',
            shortcut: 'Alt+C'
        },
        'dashboard': {
            name: '仪表盘',
            icon: 'fa-chart-line',
            url: '/dashboard',
            description: '查看系统状态和详细数据',
            shortcut: 'Alt+D'
        },
        'settings': {
            name: '设置',
            icon: 'fa-cog',
            url: '/settings',
            description: '配置系统参数',
            shortcut: 'Alt+S'
        },
        'debug': {
            name: '调试',
            icon: 'fa-bug',
            url: '/debug',
            description: '调试和测试功能',
            shortcut: 'Alt+X'
        }
    };

    // ============================================================================
    // 导航栏管理器
    // ============================================================================

    const NavigationBar = {
        container: null,
        currentPage: null,
        isMobileMenuOpen: false,

        init() {
            this.currentPage = this.detectCurrentPage();
            this.create();
            this.bindEvents();
            this.setupKeyboardShortcuts();
        },

        detectCurrentPage() {
            const path = window.location.pathname;
            if (path === '/chat' || path === '/') return 'chat';
            if (path === '/dashboard') return 'dashboard';
            if (path === '/settings') return 'settings';
            if (path === '/debug') return 'debug';
            return 'chat';
        },

        create() {
            // 创建导航栏容器
            this.container = document.createElement('nav');
            this.container.className = 'genesis-nav';
            this.container.innerHTML = this.render();

            // 插入到页面
            document.body.insertBefore(this.container, document.body.firstChild);
        },

        render() {
            return `
                <div class="nav-container">
                    <!-- Logo 区域 -->
                    <div class="nav-brand">
                        <div class="nav-logo">
                            <i class="fas fa-dna"></i>
                        </div>
                        <span class="nav-brand-text">Genesis X</span>
                    </div>

                    <!-- 导航链接 -->
                    <div class="nav-links">
                        ${Object.entries(PAGES).map(([key, page]) => `
                            <a href="${page.url}"
                               class="nav-link ${key === this.currentPage ? 'active' : ''}"
                               data-page="${key}"
                               title="${page.description} (${page.shortcut})">
                                <i class="fas ${page.icon}"></i>
                                <span class="nav-link-text">${page.name}</span>
                            </a>
                        `).join('')}
                    </div>

                    <!-- 右侧工具栏 -->
                    <div class="nav-tools">
                        <button class="nav-tool-btn" id="nav-quick-status" title="快速状态">
                            <i class="fas fa-heartbeat"></i>
                        </button>
                        <button class="nav-tool-btn" id="nav-theme-toggle" title="切换主题">
                            <i class="fas fa-moon"></i>
                        </button>
                        <button class="nav-tool-btn" id="nav-menu-toggle" title="菜单">
                            <i class="fas fa-bars"></i>
                        </button>
                    </div>

                    <!-- 移动端菜单按钮 -->
                    <button class="nav-mobile-toggle" id="nav-mobile-toggle">
                        <span></span>
                        <span></span>
                        <span></span>
                    </button>
                </div>

                <!-- 快速状态面板 -->
                <div class="nav-status-panel" id="nav-status-panel">
                    <div class="status-panel-content">
                        <div class="status-item">
                            <i class="fas fa-bolt"></i>
                            <span id="quick-energy">--%</span>
                        </div>
                        <div class="status-item">
                            <i class="fas fa-smile"></i>
                            <span id="quick-mood">--%</span>
                        </div>
                        <div class="status-item">
                            <i class="fas fa-tired"></i>
                            <span id="quick-stress">--%</span>
                        </div>
                        <div class="status-item">
                            <i class="fas fa-clock"></i>
                            <span id="quick-tick">0</span>
                        </div>
                    </div>
                </div>
            `;
        },

        bindEvents() {
            // 移动端菜单切换
            const mobileToggle = document.getElementById('nav-mobile-toggle');
            if (mobileToggle) {
                mobileToggle.addEventListener('click', () => this.toggleMobileMenu());
            }

            // 快速状态面板切换
            const statusBtn = document.getElementById('nav-quick-status');
            if (statusBtn) {
                statusBtn.addEventListener('click', () => this.toggleStatusPanel());
            }

            // 主题切换
            const themeToggle = document.getElementById('nav-theme-toggle');
            if (themeToggle) {
                themeToggle.addEventListener('click', () => this.toggleTheme());
            }

            // 点击外部关闭面板
            document.addEventListener('click', (e) => {
                if (!e.target.closest('.nav-status-panel') &&
                    !e.target.closest('#nav-quick-status')) {
                    this.closeStatusPanel();
                }
            });

            // 页面导航前的确认
            this.setupNavigationGuard();
        },

        setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                // Alt + 快捷键
                if (e.altKey) {
                    for (const [key, page] of Object.entries(PAGES)) {
                        const shortcutKey = page.shortcut.split('+')[1];
                        if (e.key === shortcutKey.toLowerCase() || e.key === shortcutKey.toUpperCase()) {
                            e.preventDefault();
                            this.navigateTo(key);
                            return;
                        }
                    }
                }

                // Escape 关闭所有面板
                if (e.key === 'Escape') {
                    this.closeStatusPanel();
                    this.closeMobileMenu();
                }
            });
        },

        setupNavigationGuard() {
            // 保存聊天输入状态
            const chatInput = document.getElementById('chat-input');
            if (chatInput) {
                const navLinks = document.querySelectorAll('.nav-link');
                navLinks.forEach(link => {
                    link.addEventListener('click', (e) => {
                        if (chatInput.value.trim()) {
                            const confirm = window.confirm('您有未发送的消息，确定要离开吗？');
                            if (!confirm) {
                                e.preventDefault();
                            }
                        }
                    });
                });
            }
        },

        navigateTo(pageKey) {
            const page = PAGES[pageKey];
            if (page && pageKey !== this.currentPage) {
                // 添加过渡动画
                document.body.classList.add('page-transition');
                setTimeout(() => {
                    window.location.href = page.url;
                }, 150);
            }
        },

        toggleMobileMenu() {
            this.isMobileMenuOpen = !this.isMobileMenuOpen;
            this.container.classList.toggle('mobile-menu-open', this.isMobileMenuOpen);
        },

        closeMobileMenu() {
            this.isMobileMenuOpen = false;
            this.container.classList.remove('mobile-menu-open');
        },

        toggleStatusPanel() {
            const panel = document.getElementById('nav-status-panel');
            if (panel) {
                panel.classList.toggle('open');
            }
        },

        closeStatusPanel() {
            const panel = document.getElementById('nav-status-panel');
            if (panel) {
                panel.classList.remove('open');
            }
        },

        toggleTheme() {
            const btn = document.getElementById('nav-theme-toggle');
            const icon = btn?.querySelector('i');
            if (icon) {
                const isDark = icon.classList.contains('fa-moon');
                icon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
                // TODO: 实际主题切换逻辑
            }
        },

        updateQuickStatus(status) {
            const energy = Math.round((status.energy || 0) * 100);
            const mood = Math.round((status.mood || 0) * 100);
            const stress = Math.round((status.stress || 0) * 100);

            const energyEl = document.getElementById('quick-energy');
            const moodEl = document.getElementById('quick-mood');
            const stressEl = document.getElementById('quick-stress');
            const tickEl = document.getElementById('quick-tick');

            if (energyEl) energyEl.textContent = `${energy}%`;
            if (moodEl) moodEl.textContent = `${mood}%`;
            if (stressEl) stressEl.textContent = `${stress}%`;
            if (tickEl) tickEl.textContent = status.tick || 0;
        }
    };

    // ============================================================================
    // 面包屑导航
    // ============================================================================

    const Breadcrumb = {
        create() {
            const currentPage = NavigationBar.currentPage;
            const page = PAGES[currentPage];

            const breadcrumb = document.createElement('div');
            breadcrumb.className = 'breadcrumb';
            breadcrumb.innerHTML = `
                <a href="/" class="breadcrumb-item">
                    <i class="fas fa-home"></i>
                </a>
                <span class="breadcrumb-separator"><i class="fas fa-chevron-right"></i></span>
                <span class="breadcrumb-item current">
                    <i class="fas ${page.icon}"></i>
                    ${page.name}
                </span>
            `;

            // 找到页面主容器并插入
            const mainContainer = document.querySelector('main, .chat-main, .dashboard-main, .settings-container');
            if (mainContainer) {
                mainContainer.insertBefore(breadcrumb, mainContainer.firstChild);
            }
        }
    };

    // ============================================================================
    // 返回按钮助手
    // ============================================================================

    const BackButton = {
        create(options = {}) {
            const {
                text = '返回',
                target = 'history',
                url = null,
                icon = 'fa-arrow-left'
            } = options;

            const btn = document.createElement('button');
            btn.className = 'btn btn-ghost back-button';
            btn.innerHTML = `<i class="fas ${icon}"></i> ${text}`;

            btn.addEventListener('click', () => {
                if (target === 'history') {
                    window.history.back();
                } else if (target === 'url' && url) {
                    window.location.href = url;
                }
            });

            return btn;
        },

        inject(selector = 'header') {
            const header = document.querySelector(selector);
            if (header && !header.querySelector('.back-button')) {
                const btn = this.create();
                header.insertBefore(btn, header.firstChild);
            }
        }
    };

    // ============================================================================
    // 页面过渡管理器
    // ============================================================================

    const PageTransition = {
        init() {
            // 页面加载时的过渡
            document.body.classList.add('page-loading');
            window.addEventListener('load', () => {
                setTimeout(() => {
                    document.body.classList.remove('page-loading');
                    document.body.classList.add('page-loaded');
                }, 100);
            });

            // 页面卸载前的过渡
            window.addEventListener('beforeunload', () => {
                document.body.classList.add('page-unloading');
            });
        }
    };

    // ============================================================================
    // 初始化和导出
    // ============================================================================

    function init() {
        // 初始化页面过渡
        PageTransition.init();

        // 初始化导航栏
        NavigationBar.init();

        // 创建面包屑（可选）
        if (document.querySelector('.enable-breadcrumb')) {
            Breadcrumb.create();
        }

        // 启动状态更新
        startStatusUpdates();

        console.log('Genesis X Navigation initialized');
    }

    function startStatusUpdates() {
        const updateStatus = async () => {
            try {
                const res = await fetch('/api/status');
                const status = await res.json();
                NavigationBar.updateQuickStatus(status);
            } catch (error) {
                console.error('Status update failed:', error);
            }
        };

        updateStatus();
        setInterval(updateStatus, 5000);
    }

    // 自动初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // 导出全局 API
    window.GenesisXNav = {
        navigateTo: (page) => NavigationBar.navigateTo(page),
        createBackButton: (options) => BackButton.create(options),
        injectBackButton: (selector) => BackButton.inject(selector),
        updateStatus: (status) => NavigationBar.updateQuickStatus(status),
        PAGES
    };

})();
