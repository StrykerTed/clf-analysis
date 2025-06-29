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
    
    // Load available builds on page load (with small delay to ensure DOM is ready)
    setTimeout(() => {
        loadAvailableBuilds();
    }, 100);
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
    const heightInput = document.getElementById('height-input');
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            loadAvailableBuilds();
        });
    }
    
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', function() {
            if (selectedBuild) {
                const height = getValidatedHeight();
                if (height !== null) {
                    analyzeBuild(selectedBuild, height);
                }
            }
        });
    }
    
    if (heightInput) {
        // Add input validation and formatting
        heightInput.addEventListener('input', function() {
            validateHeightInput();
            updateAnalyzeButtonState();
        });
        
        heightInput.addEventListener('blur', function() {
            formatHeightInput();
        });
        
        // Allow Enter key to trigger analysis
        heightInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !analyzeBtn.disabled) {
                analyzeBtn.click();
            }
        });
    }
}

// Validate height input in real-time
function validateHeightInput() {
    const heightInput = document.getElementById('height-input');
    if (!heightInput) return;
    
    const value = heightInput.value;
    const numValue = parseFloat(value);
    
    // Remove invalid class first
    heightInput.classList.remove('invalid');
    
    // Check if value is valid
    if (value && (isNaN(numValue) || numValue < 0 || numValue > 9999.99)) {
        heightInput.classList.add('invalid');
        return false;
    }
    
    return true;
}

// Format height input on blur
function formatHeightInput() {
    const heightInput = document.getElementById('height-input');
    if (!heightInput) return;
    
    const value = heightInput.value.trim();
    if (value && !isNaN(parseFloat(value))) {
        const numValue = parseFloat(value);
        if (numValue >= 0 && numValue <= 9999.99) {
            heightInput.value = numValue.toFixed(2);
        }
    }
}

// Get validated height value
function getValidatedHeight() {
    const heightInput = document.getElementById('height-input');
    if (!heightInput) return null;
    
    const value = heightInput.value.trim();
    
    if (!value) {
        showNotification('Please enter a height value for analysis', 'warning');
        heightInput.focus();
        return null;
    }
    
    const numValue = parseFloat(value);
    
    if (isNaN(numValue)) {
        showNotification('Please enter a valid numeric height value', 'error');
        heightInput.focus();
        return null;
    }
    
    if (numValue < 0) {
        showNotification('Height cannot be negative', 'error');
        heightInput.focus();
        return null;
    }
    
    if (numValue > 9999.99) {
        showNotification('Height cannot exceed 9999.99 mm', 'error');
        heightInput.focus();
        return null;
    }
    
    return numValue;
}

// Update analyze button state based on inputs
function updateAnalyzeButtonState() {
    const analyzeBtn = document.getElementById('analyze-btn');
    const heightInput = document.getElementById('height-input');
    
    if (!analyzeBtn || !heightInput) return;
    
    const hasSelectedBuild = selectedBuild !== null;
    const hasValidHeight = heightInput.value.trim() !== '' && validateHeightInput();
    
    analyzeBtn.disabled = !(hasSelectedBuild && hasValidHeight);
}

// Load available builds from the API
function loadAvailableBuilds() {
    const container = document.getElementById('builds-grid');
    const actions = document.getElementById('build-actions');
    
    // Safety check for DOM elements
    if (!container) {
        console.error('builds-grid element not found');
        return;
    }
    
    if (!actions) {
        console.error('build-actions element not found');
        return;
    }
    
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
    const container = document.getElementById('builds-grid');
    
    // Safety check
    if (!container) {
        console.error('builds-grid element not found');
        return;
    }
    
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
    
    // Clear container and add builds directly (no nested grid)
    container.innerHTML = '';
    
    builds.forEach(build => {
        const buildCard = createBuildCard(build);
        container.appendChild(buildCard);
    });
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
    const heightInput = document.getElementById('height-input');
    
    if (buildName) buildName.textContent = `Build ${build.build_number}`;
    if (buildStatus) buildStatus.textContent = build.status;
    
    // Clear height input and focus it
    if (heightInput) {
        heightInput.value = '';
        setTimeout(() => heightInput.focus(), 100);
    }
    
    // Update analyze button state
    updateAnalyzeButtonState();
    
    actions.style.display = 'flex';
    
    showNotification(`Selected Build ${build.build_number} - Enter analysis height`, 'info');
}

// Analyze selected build
function analyzeBuild(build, height) {
    if (!build || height === null || height === undefined) return;
    
    showNotification(`Starting CLF analysis of Build ${build.build_number} at height ${height}mm...`, 'info');
    
    // Show loading state
    showAnalysisLoading(true);
    
    const requestData = {
        build_number: build.build_number,
        height_mm: height,
        build_folder: build.folder_name
    };
    
    fetch(`/api/builds/${build.build_number}/analyze`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    })
        .then(response => response.json())
        .then(data => {
            showAnalysisLoading(false);
            
            if (data.status === 'success') {
                showNotification(
                    `Analysis completed! Processed ${data.files_processed} files, excluded ${data.files_excluded} files.`, 
                    'success'
                );
                
                // Display the analysis results
                displayAnalysisResults(data);
                updateAnalysisStatus(build.build_number, height, true);
            } else {
                showNotification(`Analysis failed: ${data.message}`, 'error');
                updateAnalysisStatus(build.build_number, height, false);
            }
        })
        .catch(error => {
            showAnalysisLoading(false);
            console.error('Error analyzing build:', error);
            showNotification('Network error during analysis', 'error');
            updateAnalysisStatus(build.build_number, height, false);
        });
}

// Update analysis status
function updateAnalysisStatus(buildNumber, height, success) {
    const clfStatus = document.querySelector('.status-grid .status-item:nth-child(3) .status-value');
    if (clfStatus) {
        if (success) {
            clfStatus.textContent = 'COMPLETE';
            clfStatus.className = 'status-value status-complete';
        } else {
            clfStatus.textContent = 'ERROR';
            clfStatus.className = 'status-value status-error';
        }
    }
}

// Show/hide analysis loading state
function showAnalysisLoading(show) {
    const resultsSection = document.getElementById('results-section');
    const resultsContent = document.getElementById('results-content');
    
    if (show) {
        resultsContent.innerHTML = `
            <div class="analysis-loading">
                <div class="spinner"></div>
                <h3>Analyzing CLF Data...</h3>
                <p>Processing build files and generating visualization...</p>
                <p class="loading-details">This may take a few moments depending on the complexity of the build.</p>
            </div>
        `;
        resultsSection.style.display = 'block';
    } else if (!show && resultsSection.style.display === 'block') {
        // Only hide if we're currently showing loading
        // The displayAnalysisResults function will handle showing results
    }
}

// Display analysis results with visualization
function displayAnalysisResults(data) {
    const resultsSection = document.getElementById('results-section');
    const resultsContent = document.getElementById('results-content');
    
    let visualizationHtml = '';
    
    // Check if we have visualization data
    if (data.visualizations && data.visualizations.clean_platform) {
        const viz = data.visualizations.clean_platform;
        visualizationHtml = `
            <div class="visualization-container">
                <h4>Platform Visualization at ${data.height_mm}mm</h4>
                <div class="platform-image-container">
                    <img src="data:${viz.type};base64,${viz.base64_data}" 
                         alt="CLF Platform Analysis at ${data.height_mm}mm"
                         class="platform-visualization"
                         onclick="openImageModal(this)">
                </div>
                <p class="viz-caption">Click image to view full size</p>
            </div>
        `;
    } else if (data.visualizations && data.visualizations.error) {
        visualizationHtml = `
            <div class="visualization-error">
                <h4>Visualization Error</h4>
                <p class="error-message">${data.visualizations.error}</p>
            </div>
        `;
    } else {
        visualizationHtml = `
            <div class="visualization-placeholder">
                <h4>Analysis Complete</h4>
                <p>No visualization data available</p>
            </div>
        `;
    }
    
    resultsContent.innerHTML = `
        <div class="analysis-results">
            <div class="results-header">
                <h3>Analysis Results - Build ${data.build_number}</h3>
                <div class="analysis-metadata">
                    <span class="metadata-item">Height: ${data.height_mm}mm</span>
                    <span class="metadata-item">Files Processed: ${data.files_processed}</span>
                    <span class="metadata-item">Files Excluded: ${data.files_excluded}</span>
                    <span class="metadata-item">Total Files: ${data.total_files_found}</span>
                </div>
            </div>
            
            ${visualizationHtml}
            
            <div class="analysis-summary">
                <div class="summary-stats">
                    <div class="stat-card">
                        <div class="stat-number">${data.files_processed}</div>
                        <div class="stat-label">CLF Files Processed</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${data.files_excluded}</div>
                        <div class="stat-label">Files Excluded</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${data.height_mm}mm</div>
                        <div class="stat-label">Analysis Height</div>
                    </div>
                </div>
            </div>
            
            <div class="analysis-actions">
                <button class="btn btn-secondary" onclick="downloadResults('${data.analysis_id}')">
                    📥 Download Results
                </button>
                <button class="btn btn-primary" onclick="analyzeAnotherHeight()">
                    🔍 Analyze Another Height
                </button>
            </div>
        </div>
    `;
    
    resultsSection.style.display = 'block';
}

// Open image in modal for full-size viewing
function openImageModal(img) {
    const modal = document.createElement('div');
    modal.className = 'image-modal';
    modal.innerHTML = `
        <div class="modal-backdrop" onclick="closeImageModal()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h3>CLF Platform Analysis</h3>
                    <button class="modal-close" onclick="closeImageModal()">×</button>
                </div>
                <div class="modal-body">
                    <img src="${img.src}" alt="${img.alt}" class="modal-image">
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
}

// Close image modal
function closeImageModal() {
    const modal = document.querySelector('.image-modal');
    if (modal) {
        modal.remove();
        document.body.style.overflow = '';
    }
}

// Download analysis results
function downloadResults(analysisId) {
    showNotification('Download functionality coming soon!', 'info');
}

// Analyze another height - reset the form
function analyzeAnotherHeight() {
    const heightInput = document.getElementById('height-input');
    if (heightInput) {
        heightInput.value = '';
        heightInput.focus();
    }
    
    const resultsSection = document.getElementById('results-section');
    resultsSection.style.display = 'none';
    
    showNotification('Ready for another analysis', 'info');
}

// Display error message
function displayError(message) {
    const container = document.getElementById('builds-grid');
    
    // Safety check
    if (!container) {
        console.error('builds-grid element not found');
        return;
    }
    
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
