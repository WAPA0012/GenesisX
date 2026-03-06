/**
 * Genesis X Web UI - Main JavaScript
 */

// Genesis X App namespace
const GenesisX = {
    version: '1.0.0',

    // API endpoints
    api: {
        status: '/api/status',
        metrics: '/api/metrics',
        memory: '/api/memory',
        messages: '/api/messages',
        chat: '/api/chat',
        configure: '/api/configure',
        reset: '/api/reset',
        stream: '/api/stream'
    },

    // Current state
    state: {
        connected: false,
        data: null
    },

    // Initialize app
    init() {
        console.log('Genesis X Web UI v' + this.version);
        this.setupEventListeners();
    },

    // Setup event listeners
    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav a').forEach(link => {
            link.addEventListener('click', (e) => {
                document.querySelectorAll('.nav a').forEach(l => l.classList.remove('active'));
                e.target.classList.add('active');
            });
        });
    },

    // API helper
    async apiCall(endpoint, options = {}) {
        try {
            const response = await fetch(endpoint, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    },

    // Get system status
    async getStatus() {
        return await this.apiCall(this.api.status);
    },

    // Get metrics
    async getMetrics() {
        return await this.apiCall(this.api.metrics);
    },

    // Get memory
    async getMemory() {
        return await this.apiCall(this.api.memory);
    },

    // Get messages
    async getMessages() {
        return await this.apiCall(this.api.messages);
    },

    // Send chat message
    async sendMessage(message) {
        return await this.apiCall(this.api.chat, {
            method: 'POST',
            body: JSON.stringify({
                message: message,
                user: 'User'
            })
        });
    },

    // Format value as percentage
    formatPercent(value) {
        if (typeof value !== 'number') return '--';
        return (value * 100).toFixed(0) + '%';
    },

    // Color based on value
    getColorForValue(value, type = 'default') {
        if (type === 'energy' || type === 'mood') {
            if (value > 0.7) return '#4CAF50';
            if (value > 0.4) return '#FFC107';
            return '#F44336';
        }
        if (type === 'stress') {
            if (value < 0.3) return '#4CAF50';
            if (value < 0.6) return '#FFC107';
            return '#F44336';
        }
        return '#2196F3';
    },

    // Debounce function
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

    // Throttle function
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

    // Safe HTML escape
    escapeHtml(unsafe) {
        const div = document.createElement('div');
        div.textContent = unsafe;
        return div.innerHTML;
    },

    // Format timestamp
    formatTimestamp(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return '刚刚';
        if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
        if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';

        return date.toLocaleDateString('zh-CN', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // Show notification
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            background: ${type === 'error' ? '#F44336' : type === 'success' ? '#4CAF50' : '#2196F3'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    },

    // Local storage helpers
    storage: {
        get(key, defaultValue = null) {
            try {
                const item = localStorage.getItem('genesisx_' + key);
                return item ? JSON.parse(item) : defaultValue;
            } catch {
                return defaultValue;
            }
        },

        set(key, value) {
            try {
                localStorage.setItem('genesisx_' + key, JSON.stringify(value));
            } catch (e) {
                console.error('Storage error:', e);
            }
        },

        remove(key) {
            localStorage.removeItem('genesisx_' + key);
        }
    }
};

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }

    .notification {
        animation: slideIn 0.3s ease-out;
    }
`;
document.head.appendChild(style);

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => GenesisX.init());
} else {
    GenesisX.init();
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GenesisX;
}
