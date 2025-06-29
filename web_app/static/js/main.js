// CLF Analysis Tool JavaScript

let selectedBuild = null;

document.addEventListener('DOMContentLoaded', function() {
    console.log('CLF Analysis Tool loaded successfully!');
    
    // Initialize real-time clock
    updateClock();
    setInterval(updateClock, 1000);
    
    // Add interactive functionality
    initializeFeatureCards();
    initializeBuildSelection();
    
    // Health check functionality
    const statusGrid = document.querySelector('.status-grid');
    if (statusGrid) {
        statusGrid.addEventListener('click', function() {
            performHealthCheck();
        });
    }
    
    // Load available builds on page load
    loadAvailableBuilds();
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

// Initialize build selection functionality
function initializeBuildSelection() {
    const refreshBtn = document.getElementById('refresh-builds');
    const analyzeBtn = document.getElementById('analyze-btn');
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            loadAvailableBuilds();
        });
    }
    
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', function() {
            if (selectedBuild) {
                analyzeBuild(selectedBuild);
            }
        });
    }
}

// Load available builds from the API
function loadAvailableBuilds() {
    const container = document.getElementById('builds-container');
    const actions = document.getElementById('build-actions');
    
    // Show loading spinner
    container.innerHTML = `
        <div class="loading-spinner">
            <div class="spinner"></div>
            <p>Loading available builds...</p>
        </div>
    `;
    
    actions.style.display = 'none';
    selectedBuild = null;
    
    fetch('/api/builds')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayBuilds(data.builds);
                showNotification(`Found ${data.count} available builds`, 'success');
            } else {
                displayError(data.message || 'Failed to load builds');
                showNotification('Failed to load builds', 'error');
            }
        })
        .catch(error => {
            console.error('Error loading builds:', error);
            displayError('Network error: Could not connect to server');
            showNotification('Network error loading builds', 'error');
        });
}

// Display builds in the container
function displayBuilds(builds) {
    const container = document.getElementById('builds-container');
    
    if (builds.length === 0) {
        container.innerHTML = `
            <div class="no-builds-message">
                <h4>No ABP Builds Found</h4>
                <p>No build folders found in the abp_contents directory.</p>
                <p>Make sure you have unzipped ABP files with 'build-' in their folder names.</p>
            </div>
        `;
        return;
    }
    
    const buildsGrid = document.createElement('div');
    buildsGrid.className = 'builds-grid';
    
    builds.forEach(build => {
        const buildCard = createBuildCard(build);
        buildsGrid.appendChild(buildCard);
    });
    
    container.innerHTML = '';
    container.appendChild(buildsGrid);
}

// Create a build card element
function createBuildCard(build) {
    const card = document.createElement('div');
    card.className = 'build-card';
    card.dataset.buildNumber = build.build_number;
    card.dataset.buildData = JSON.stringify(build);
    
    const statusClass = build.status.toLowerCase() === 'complete' ? 'complete' : 'processing';
    
    card.innerHTML = `
        <div class="build-card-header">
            <div class="build-number">Build ${build.build_number}</div>
            <div class="build-status ${statusClass}">${build.status}</div>
        </div>
        <div class="build-folder-name">${build.folder_name}</div>
        <div class="build-features">
            <div class="build-feature ${build.has_complete ? 'available' : ''}">
                ${build.has_complete ? '✅' : '❌'} Complete
            </div>
            <div class="build-feature ${build.has_models ? 'available' : ''}">
                ${build.has_models ? '✅' : '❌'} Models
            </div>
        </div>
    `;
    
    card.addEventListener('click', function() {
        selectBuild(build, card);
    });
    
    return card;
}

// Select a build
function selectBuild(build, cardElement) {
    selectedBuild = build;
    
    // Remove previous selection
    document.querySelectorAll('.build-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Select current card
    cardElement.classList.add('selected');
    
    // Update build actions
    const actions = document.getElementById('build-actions');
    const buildName = document.getElementById('selected-build-name');
    const buildStatus = document.getElementById('selected-build-status');
    const analyzeBtn = document.getElementById('analyze-btn');
    
    if (buildName) buildName.textContent = `Build ${build.build_number}`;
    if (buildStatus) buildStatus.textContent = build.status;
    
    if (analyzeBtn) {
        analyzeBtn.disabled = false;
    }
    
    actions.style.display = 'flex';
    
    showNotification(`Selected Build ${build.build_number}`, 'info');
}

// Analyze selected build
function analyzeBuild(build) {
    if (!build) return;
    
    showNotification(`Starting analysis of Build ${build.build_number}...`, 'info');
    
    fetch(`/api/builds/${build.build_number}/analyze`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification(data.message, 'success');
                updateAnalysisStatus(build.build_number);
            } else {
                showNotification(`Analysis failed: ${data.message}`, 'error');
            }
        })
        .catch(error => {
            console.error('Error analyzing build:', error);
            showNotification('Network error during analysis', 'error');
        });
}

// Update analysis status
function updateAnalysisStatus(buildNumber) {
    const clfStatus = document.querySelector('.status-grid .status-item:nth-child(3) .status-value');
    if (clfStatus) {
        clfStatus.textContent = 'ANALYZING';
        clfStatus.className = 'status-value status-running';
    }
}

// Display error message
function displayError(message) {
    const container = document.getElementById('builds-container');
    container.innerHTML = `
        <div class="error-message">
            <h4>Error Loading Builds</h4>
            <p>${message}</p>
            <button onclick="loadAvailableBuilds()" class="refresh-btn">🔄 Try Again</button>
        </div>
    `;
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
    
    .build-card {
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .analyze-btn:active {
        transform: scale(0.98);
    }
    
    .refresh-btn:active {
        transform: scale(0.98);
    }
`;
document.head.appendChild(style);
