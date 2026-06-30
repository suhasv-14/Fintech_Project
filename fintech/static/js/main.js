/**
 * SmartSpend — Main JavaScript
 * Chart.js initialization, form validation, UI interactions, theme toggle
 */

// ============================================================
// Theme Toggle (Dark / Light)
// ============================================================
function toggleTheme() {
    var html = document.documentElement;
    var current = html.getAttribute('data-theme') || 'dark';
    var next = current === 'dark' ? 'light' : 'dark';

    // Add smooth transition class
    html.classList.add('theme-transitioning');
    html.setAttribute('data-theme', next);
    localStorage.setItem('smartspend-theme', next);
    syncThemeUI(next);

    // Remove transition class after animation completes
    setTimeout(function () {
        html.classList.remove('theme-transitioning');
    }, 500);
}

function syncThemeUI(theme) {
    // Update sidebar toggle button
    var icon = document.getElementById('themeIcon');
    var label = document.getElementById('themeLabel');
    if (icon) {
        icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
    }
    if (label) {
        label.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
    }

    // Update auth page floating toggle
    var authIcon = document.getElementById('authThemeIcon');
    if (authIcon) {
        authIcon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
    }
}

// ============================================================
// Flash message auto-dismiss
// ============================================================
document.addEventListener('DOMContentLoaded', function () {
    // Sync theme toggle UI with current theme
    var currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    syncThemeUI(currentTheme);

    // Auto-remove flash messages after 4 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function (msg) {
        setTimeout(function () {
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-10px)';
            setTimeout(function () { msg.remove(); }, 400);
        }, 4000);
    });

    // Mobile sidebar toggle
    const mobileToggle = document.querySelector('.mobile-toggle');
    const sidebar = document.querySelector('.sidebar');
    if (mobileToggle && sidebar) {
        mobileToggle.addEventListener('click', function () {
            sidebar.classList.toggle('open');
        });

        // Close sidebar on outside click
        document.addEventListener('click', function (e) {
            if (sidebar.classList.contains('open') &&
                !sidebar.contains(e.target) &&
                !mobileToggle.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    }

    // Animate summary cards on load
    const summaryCards = document.querySelectorAll('.summary-card');
    summaryCards.forEach(function (card, index) {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(function () {
            card.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100 + index * 100);
    });

    // Animate health score ring
    initHealthScoreRing();

    // Initialize progress bars with animation
    initProgressBars();
});


// ============================================================
// Dashboard Charts (called from dashboard.html)
// ============================================================
function initPieChart(canvasId, labels, values, colors) {
    var ctx = document.getElementById(canvasId);
    if (!ctx) return;

    if (labels.length === 0) {
        ctx.parentElement.innerHTML = '<div class="empty-state" style="padding: 40px 20px;"><i class="bi bi-pie-chart"></i><p>No expense data yet</p></div>';
        return;
    }

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 0,
                hoverBorderWidth: 3,
                hoverBorderColor: '#fff',
                spacing: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#9d9db5',
                        font: { family: 'Inter', size: 12, weight: '500' },
                        padding: 16,
                        usePointStyle: true,
                        pointStyleWidth: 10,
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(30, 30, 50, 0.95)',
                    titleColor: '#e8e8f0',
                    bodyColor: '#9d9db5',
                    titleFont: { family: 'Inter', weight: '600' },
                    bodyFont: { family: 'Inter' },
                    padding: 12,
                    cornerRadius: 8,
                    borderColor: 'rgba(255,255,255,0.06)',
                    borderWidth: 1,
                    callbacks: {
                        label: function (context) {
                            var total = context.dataset.data.reduce(function (a, b) { return a + b; }, 0);
                            var pct = ((context.parsed / total) * 100).toFixed(1);
                            return context.label + ': ₹' + context.parsed.toLocaleString('en-IN') + ' (' + pct + '%)';
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 1200,
                spacing: 2,
            }
        }
    });
}


function initBarChart(canvasId, labels, expenseData, incomeData) {
    var ctx = document.getElementById(canvasId);
    if (!ctx) return;

    if (labels.length === 0) {
        ctx.parentElement.innerHTML = '<div class="empty-state" style="padding: 40px 20px;"><i class="bi bi-bar-chart"></i><p>Add income and expenses to see trends</p></div>';
        return;
    }

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Income',
                    data: incomeData,
                    backgroundColor: 'rgba(0, 230, 118, 0.25)',
                    borderColor: '#00e676',
                    borderWidth: 2,
                    borderRadius: 6,
                    borderSkipped: false,
                },
                {
                    label: 'Expenses',
                    data: expenseData,
                    backgroundColor: 'rgba(255, 82, 82, 0.25)',
                    borderColor: '#ff5252',
                    borderWidth: 2,
                    borderRadius: 6,
                    borderSkipped: false,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    align: 'end',
                    labels: {
                        color: '#9d9db5',
                        font: { family: 'Inter', size: 12, weight: '500' },
                        padding: 16,
                        usePointStyle: true,
                        pointStyleWidth: 10,
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(30, 30, 50, 0.95)',
                    titleColor: '#e8e8f0',
                    bodyColor: '#9d9db5',
                    titleFont: { family: 'Inter', weight: '600' },
                    bodyFont: { family: 'Inter' },
                    padding: 12,
                    cornerRadius: 8,
                    borderColor: 'rgba(255,255,255,0.06)',
                    borderWidth: 1,
                    callbacks: {
                        label: function (context) {
                            return context.dataset.label + ': ₹' + context.parsed.y.toLocaleString('en-IN');
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.03)', drawBorder: false },
                    ticks: { color: '#6b6b85', font: { family: 'Inter', size: 11 } },
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.03)', drawBorder: false },
                    ticks: {
                        color: '#6b6b85',
                        font: { family: 'Inter', size: 11 },
                        callback: function (value) { return '₹' + value.toLocaleString('en-IN'); }
                    },
                    beginAtZero: true,
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeInOutQuart',
            }
        }
    });
}


// ============================================================
// Health Score Ring Animation
// ============================================================
function initHealthScoreRing() {
    var ring = document.querySelector('.health-score-ring');
    if (!ring) return;

    var score = parseInt(ring.getAttribute('data-score') || '0');
    var fillCircle = ring.querySelector('.ring-fill');
    if (!fillCircle) return;

    var radius = parseFloat(fillCircle.getAttribute('r'));
    var circumference = 2 * Math.PI * radius;

    fillCircle.style.strokeDasharray = circumference;
    fillCircle.style.strokeDashoffset = circumference;

    // Set color based on score
    var strokeColor;
    if (score >= 80) strokeColor = '#00e676';
    else if (score >= 60) strokeColor = '#00d2ff';
    else if (score >= 40) strokeColor = '#ffd740';
    else strokeColor = '#ff5252';

    fillCircle.style.stroke = strokeColor;

    // Animate after a short delay
    setTimeout(function () {
        var offset = circumference - (score / 100) * circumference;
        fillCircle.style.strokeDashoffset = offset;
    }, 300);
}


// ============================================================
// Progress Bar Animation
// ============================================================
function initProgressBars() {
    var bars = document.querySelectorAll('.progress-bar-fill');
    bars.forEach(function (bar) {
        var width = bar.getAttribute('data-width') || '0';
        bar.style.width = '0%';
        setTimeout(function () {
            bar.style.width = width + '%';
        }, 300);
    });
}


// ============================================================
// Form Validation
// ============================================================
function validateExpenseForm(form) {
    var amount = parseFloat(form.querySelector('[name="amount"]').value);
    var category = form.querySelector('[name="category"]').value;

    if (!category) {
        showToast('Please select a category.', 'warning');
        return false;
    }
    if (isNaN(amount) || amount <= 0) {
        showToast('Please enter a valid amount.', 'warning');
        return false;
    }
    return true;
}

function validateIncomeForm(form) {
    var amount = parseFloat(form.querySelector('[name="amount"]').value);
    var source = form.querySelector('[name="source"]').value.trim();

    if (!source) {
        showToast('Please enter an income source.', 'warning');
        return false;
    }
    if (isNaN(amount) || amount <= 0) {
        showToast('Please enter a valid amount.', 'warning');
        return false;
    }
    return true;
}


// ============================================================
// Toast Notification (Client-side)
// ============================================================
function showToast(message, type) {
    type = type || 'info';
    var container = document.querySelector('.flash-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-container';
        document.body.appendChild(container);
    }

    var icons = {
        success: 'bi-check-circle-fill',
        danger: 'bi-x-circle-fill',
        warning: 'bi-exclamation-circle-fill',
        info: 'bi-info-circle-fill',
    };

    var toast = document.createElement('div');
    toast.className = 'flash-message ' + type;
    toast.innerHTML = '<i class="bi ' + (icons[type] || icons.info) + '"></i> ' + message;
    container.appendChild(toast);

    setTimeout(function () {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        setTimeout(function () { toast.remove(); }, 400);
    }, 4000);
}


// ============================================================
// Confirm Delete
// ============================================================
function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this?');
}


// ============================================================
// Format Currency
// ============================================================
function formatCurrency(amount) {
    return '₹' + parseFloat(amount).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}
