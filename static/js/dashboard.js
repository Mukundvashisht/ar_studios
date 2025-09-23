// Dashboard JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    
    // Sidebar toggle functionality
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('content');
    
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
    }
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 992) {
            if (!sidebar.contains(event.target) && !sidebarToggle.contains(event.target)) {
                sidebar.classList.remove('show');
            }
        }
    });
    
    // Search functionality
    const searchInput = document.getElementById('searchInput');
    let searchTimeout;
    
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            
            if (query.length > 2) {
                searchTimeout = setTimeout(() => {
                    performSearch(query);
                }, 300);
            }
        });
    }
    
    function performSearch(query) {
        fetch(`/search?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                console.log('Search results:', data);
                // Here you would typically display search results
                // For now, we just log them to console
            })
            .catch(error => {
                console.error('Search error:', error);
            });
    }
    
    // Dark mode toggle
    const darkmodeToggle = document.getElementById('darkmode');
    if (darkmodeToggle) {
        darkmodeToggle.addEventListener('change', function() {
            document.body.classList.toggle('dark-mode', this.checked);
            localStorage.setItem('darkMode', this.checked);
        });
        
        // Load saved dark mode preference
        const savedDarkMode = localStorage.getItem('darkMode') === 'true';
        darkmodeToggle.checked = savedDarkMode;
        document.body.classList.toggle('dark-mode', savedDarkMode);
    }
    
    // Animate numbers on page load
    animateNumbers();
    
    // Initialize tooltips if using Bootstrap
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Add hover effects to cards
    addCardHoverEffects();
    
    // Initialize progress bar animations
    animateProgressBars();
});

function animateNumbers() {
    const numberElements = document.querySelectorAll('.stat-number');
    
    numberElements.forEach(element => {
        const targetNumber = parseInt(element.textContent);
        if (isNaN(targetNumber)) return;
        
        let currentNumber = 0;
        const increment = targetNumber / 50;
        const duration = 1000; // 1 second
        const stepTime = duration / 50;
        
        const timer = setInterval(() => {
            currentNumber += increment;
            if (currentNumber >= targetNumber) {
                currentNumber = targetNumber;
                clearInterval(timer);
            }
            
            const numberText = Math.floor(currentNumber).toString();
            const changeSymbol = element.querySelector('.stat-change');
            if (changeSymbol) {
                element.innerHTML = numberText + changeSymbol.outerHTML;
            } else {
                element.textContent = numberText;
            }
        }, stepTime);
    });
}

function addCardHoverEffects() {
    const cards = document.querySelectorAll('.stat-card, .project-card, .chart-card, .activity-card, .progress-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

function animateProgressBars() {
    const progressBars = document.querySelectorAll('.progress-fill');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const progressBar = entry.target;
                const width = progressBar.style.width;
                progressBar.style.width = '0%';
                
                setTimeout(() => {
                    progressBar.style.width = width;
                }, 100);
                
                observer.unobserve(progressBar);
            }
        });
    });
    
    progressBars.forEach(bar => {
        observer.observe(bar);
    });
}

// Utility function to format numbers
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// Utility function to get relative time
function getRelativeTime(date) {
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) {
        return 'Just now';
    } else if (diffInSeconds < 3600) {
        const minutes = Math.floor(diffInSeconds / 60);
        return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 86400) {
        const hours = Math.floor(diffInSeconds / 3600);
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else {
        const days = Math.floor(diffInSeconds / 86400);
        return `${days} day${days > 1 ? 's' : ''} ago`;
    }
}

// Handle window resize
window.addEventListener('resize', function() {
    const sidebar = document.getElementById('sidebar');
    if (window.innerWidth > 992) {
        sidebar.classList.remove('show');
    }
});

// Smooth scroll for internal links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add loading states for interactive elements
function addLoadingState(element) {
    element.classList.add('loading');
    element.disabled = true;
    
    const originalText = element.textContent;
    element.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
    
    return function removeLoadingState() {
        element.classList.remove('loading');
        element.disabled = false;
        element.textContent = originalText;
    };
}

// Error handling for charts
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
    
    // Hide broken charts gracefully
    const chartContainers = document.querySelectorAll('.chart-container');
    chartContainers.forEach(container => {
        const canvas = container.querySelector('canvas');
        if (canvas && !canvas.getContext) {
            container.innerHTML = '<div class="chart-error">Chart failed to load</div>';
        }
    });
});

// Keyboard navigation support
document.addEventListener('keydown', function(e) {
    // Escape key closes sidebar on mobile
    if (e.key === 'Escape') {
        const sidebar = document.getElementById('sidebar');
        if (sidebar && sidebar.classList.contains('show')) {
            sidebar.classList.remove('show');
        }
    }
    
    // Ctrl/Cmd + K opens search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.focus();
        }
    }
});

// Performance optimization: Lazy load charts when visible
const chartObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const chartContainer = entry.target;
            const canvas = chartContainer.querySelector('canvas');
            if (canvas && !canvas.dataset.initialized) {
                // Initialize chart here if needed
                canvas.dataset.initialized = 'true';
            }
        }
    });
});

document.querySelectorAll('.chart-container').forEach(container => {
    chartObserver.observe(container);
});
