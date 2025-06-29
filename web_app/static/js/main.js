// CLF Analysis Tool JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('CLF Analysis Tool loaded successfully!');
    
    // Initialize real-time clock
    updateClock();
    setInterval(updateClock, 1000);
    
    // Add interactive functionality
    initializeFeatureCards();
    initializeUploadButton();
    
    // Health check functionality
    const statusGrid = document.querySelector('.status-grid');
    if (statusGrid) {
        statusGrid.addEventListener('click', function() {
            performHealthCheck();
        });
    }
});

// Real-time clock update
function updateClock() {
    const timeElement = document.getElementById('current-time');
    if (timeElement) {
        const now = new Date();
        const timeString = now.toISOString().slice(0, 19).replace('T', 'T');
        timeElement.textContent = timeString;
    }
}

// Initialize feature cards with hover effects and click handlers
function initializeFeatureCards() {
    const featureCards = document.querySelectorAll('.feature-card');
    
    featureCards.forEach(card => {
        card.addEventListener('click', function() {
            const title = this.querySelector('h3').textContent;
            showNotification(`${title} feature clicked!`, 'info');
            
            // Add specific handlers for each feature
            if (title.includes('REST API')) {
                window.open('/health', '_blank');
            } else if (title.includes('Processing')) {
                showNotification('Processing framework ready for integration', 'success');
            } else if (title.includes('CLF Analysis')) {
                showNotification('CLF Analysis tools coming soon!', 'info');
            } else if (title.includes('3D Platform')) {
                showNotification('3D Platform visualization in development', 'info');
            }
        });
    });
}

// Initialize upload button
function initializeUploadButton() {
    const uploadBtn = document.querySelector('.upload-btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', function() {
            // Create file input element
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = '.clf,.abp';
            fileInput.style.display = 'none';
            
            fileInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    showNotification(`Selected file: ${file.name}`, 'success');
                    // Here you would handle the file upload
                    simulateFileProcessing(file.name);
                }
                document.body.removeChild(fileInput);
            });
            
            document.body.appendChild(fileInput);
            fileInput.click();
        });
    }
}

// Simulate file processing
function simulateFileProcessing(filename) {
    showNotification('Processing CLF file...', 'info');
    
    setTimeout(() => {
        showNotification(`File ${filename} processed successfully!`, 'success');
        updateProcessingStatus();
    }, 2000);
}

// Update processing status
function updateProcessingStatus() {
    const clfStatus = document.querySelector('.status-grid .status-item:nth-child(3) .status-value');
    if (clfStatus) {
        clfStatus.textContent = 'PROCESSING';
        clfStatus.className = 'status-value status-running';
    }
}

// Health check functionality
function performHealthCheck() {
    showNotification('Running system health check...', 'info');
    
    fetch('/health')
        .then(response => response.json())
        .then(data => {
            console.log('Health check:', data);
            showNotification('System health check: ' + data.message, 'success');
            
            // Update status indicators
            const serverStatus = document.querySelector('.status-grid .status-item:first-child .status-value');
            if (serverStatus) {
                serverStatus.textContent = 'RUNNING';
                serverStatus.className = 'status-value status-running';
            }
        })
        .catch(error => {
            console.error('Health check failed:', error);
            showNotification('Health check failed - check console for details', 'error');
        });
}

// Enhanced notification system
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(n => n.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    // Add icon based on type
    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️',
        warning: '⚠️'
    };
    
    notification.innerHTML = `
        <span class="notification-icon">${icons[type] || icons.info}</span>
        <span class="notification-text">${message}</span>
        <button class="notification-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    // Style the notification
    Object.assign(notification.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '1rem 1.5rem',
        borderRadius: '8px',
        color: 'white',
        fontSize: '14px',
        fontWeight: '500',
        zIndex: '9999',
        maxWidth: '400px',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        animation: 'slideIn 0.3s ease-out',
        boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
        backgroundColor: getNotificationColor(type)
    });
    
    // Style close button
    const closeBtn = notification.querySelector('.notification-close');
    Object.assign(closeBtn.style, {
        background: 'none',
        border: 'none',
        color: 'white',
        fontSize: '18px',
        cursor: 'pointer',
        padding: '0',
        marginLeft: 'auto'
    });
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    }, 5000);
}

// Get notification color based on type
function getNotificationColor(type) {
    const colors = {
        success: '#28a745',
        error: '#dc3545',
        info: '#17a2b8',
        warning: '#ffc107'
    };
    return colors[type] || colors.info;
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .feature-card {
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .status-grid {
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .status-grid:hover {
        background: #e9ecef;
    }
    
    .upload-btn:active {
        transform: scale(0.98);
    }
`;
document.head.appendChild(style);
