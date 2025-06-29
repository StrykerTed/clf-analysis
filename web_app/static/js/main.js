// Basic JavaScript for CLF Analysis Tool

document.addEventListener('DOMContentLoaded', function() {
    console.log('CLF Analysis Tool loaded successfully!');
    
    // Add some interactive functionality
    const statusCard = document.querySelector('.status-card');
    
    if (statusCard) {
        statusCard.addEventListener('click', function() {
            // Simple health check
            fetch('/health')
                .then(response => response.json())
                .then(data => {
                    console.log('Health check:', data);
                    showNotification('System status: ' + data.message, 'success');
                })
                .catch(error => {
                    console.error('Health check failed:', error);
                    showNotification('Health check failed', 'error');
                });
        });
    }
});

// Utility function to show notifications
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Style the notification
    Object.assign(notification.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '1rem 2rem',
        borderRadius: '5px',
        color: 'white',
        fontSize: '14px',
        zIndex: '9999',
        animation: 'slideIn 0.3s ease-out',
        backgroundColor: type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#17a2b8'
    });
    
    // Add to page
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
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
    
    .status-card {
        cursor: pointer;
        transition: transform 0.2s ease;
    }
    
    .status-card:hover {
        transform: translateY(-2px);
    }
`;
document.head.appendChild(style);
