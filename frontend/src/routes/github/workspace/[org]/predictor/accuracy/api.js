/**
 * Pipeline Prediction Accuracy Dashboard API Client
 * Handles all API calls for Phase 3 Accuracy Dashboard
 * Uses JSDoc for type hints compatible with project standards
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';

/**
 * Get authentication token from localStorage
 * @returns {string|null} JWT token or null if not authenticated
 */
function getAuthToken() {
	return localStorage.getItem('auth0_token') || localStorage.getItem('auth_token') || null;
}

/**
 * Fetch with authentication header
 * @param {string} endpoint - API endpoint path
 * @param {Object} [options={}] - Fetch options
 * @returns {Promise<Object>} Parsed JSON response
 * @throws {Error} If not authenticated or request fails
 */
async function fetchWithAuth(endpoint, options = {}) {
	const token = getAuthToken();
	if (!token) {
		window.location.href = '/login';
		throw new Error('Not authenticated');
	}

	const response = await fetch(`${API_BASE_URL}${endpoint}`, {
		...options,
		headers: {
			...(options.headers || {}),
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		}
	});

	if (response.status === 401) {
		window.location.href = '/login';
		throw new Error('Unauthorized');
	}

	if (!response.ok) {
		const error = await response.json().catch(() => ({}));
		throw new Error(error.detail || `API error: ${response.status}`);
	}

	return response.json();
}

/**
 * Get organization accuracy metrics
 * @param {string} orgName - Organization name
 * @param {number} [days=7] - Time period in days
 * @returns {Promise<Object>} Metrics including overall accuracy, by risk level, by date
 */
export async function getAccuracyMetrics(orgName, days = 7) {
	return fetchWithAuth(`/api/pipeline-prediction/metrics/${orgName}?days=${days}`);
}

/**
 * Get prediction errors (false positives/negatives)
 * @param {string} orgName - Organization name
 * @param {number} [limit=50] - Maximum number of errors to return
 * @returns {Promise<Object>} Error analysis with false positives and false negatives
 */
export async function getPredictionErrors(orgName, limit = 50) {
	return fetchWithAuth(`/api/pipeline-prediction/errors/${orgName}?limit=${limit}`);
}

/**
 * Get model comparison (current vs previous model)
 * @param {string} orgName - Organization name
 * @returns {Promise<Object>} Model versions, training info, and comparison metrics
 */
export async function getModelComparison(orgName) {
	return fetchWithAuth(`/api/pipeline-prediction/model/${orgName}`);
}

/**
 * Get completion status (pending outcomes, completion rate, etc)
 * @param {string} orgName - Organization name
 * @returns {Promise<Object>} Completion metrics and status
 */
export async function getCompletionStatus(orgName) {
	return fetchWithAuth(`/api/pipeline-prediction/completion-status/${orgName}`);
}

/**
 * Get system health status
 * @returns {Promise<Object>} Health information (model status, sync status, etc)
 */
export async function getHealthStatus() {
	return fetchWithAuth('/api/pipeline-prediction/health');
}

/**
 * Get accuracy trends over time
 * @param {string} orgName - Organization name
 * @param {number} [days=7] - Time period in days
 * @returns {Promise<Array>} Daily accuracy data points
 */
export async function getAccuracyTrends(orgName, days = 7) {
	const metrics = await getAccuracyMetrics(orgName, days);
	return metrics.by_date || [];
}

/**
 * Get accuracy by risk level breakdown
 * @param {string} orgName - Organization name
 * @param {number} [days=7] - Time period in days
 * @returns {Promise<Object>} Accuracy metrics per risk level (low, medium, high, critical)
 */
export async function getAccuracyByRiskLevel(orgName, days = 7) {
	const metrics = await getAccuracyMetrics(orgName, days);
	return metrics.by_risk_level || {};
}

/**
 * Get feature importance data
 * @param {string} orgName - Organization name
 * @returns {Promise<Object>} Top N features and their importance scores
 */
export async function getFeatureImportance(orgName) {
	try {
		return await fetchWithAuth(`/api/pipeline-prediction/features/${orgName}`);
	} catch (error) {
		console.warn('Feature importance endpoint not available:', error);
		return { features: [] };
	}
}

/**
 * Export metrics report as CSV
 * @param {string} orgName - Organization name
 * @param {number} [days=7] - Time period in days
 * @returns {Promise<Blob>} CSV file blob
 */
export async function exportMetricsReport(orgName, days = 7) {
	const token = getAuthToken();
	if (!token) {
		window.location.href = '/login';
		throw new Error('Not authenticated');
	}

	const response = await fetch(
		`${API_BASE_URL}/api/pipeline-prediction/export/${orgName}?days=${days}&format=csv`,
		{
			headers: {
				Authorization: `Bearer ${token}`
			}
		}
	);

	if (!response.ok) {
		throw new Error(`Export failed: ${response.status}`);
	}

	return response.blob();
}

/**
 * Format accuracy percentage for display
 * @param {number} value - Accuracy value (0-1)
 * @returns {string} Formatted percentage string
 */
export function formatAccuracy(value) {
	return `${(value * 100).toFixed(1)}%`;
}

/**
 * Get status label based on accuracy value
 * @param {number} accuracy - Accuracy value (0-1)
 * @returns {string} Status label (HEALTHY, WARNING, CRITICAL)
 */
export function getStatusLabel(accuracy) {
	if (accuracy >= 0.75) return 'HEALTHY';
	if (accuracy >= 0.65) return 'WARNING';
	return 'CRITICAL';
}

/**
 * Get status color based on accuracy value
 * @param {number} accuracy - Accuracy value (0-1)
 * @returns {string} Hex color code
 */
export function getStatusColor(accuracy) {
	if (accuracy >= 0.75) return '#10b981';
	if (accuracy >= 0.65) return '#f59e0b';
	return '#ef4444';
}

/**
 * Get status background based on accuracy value
 * @param {number} accuracy - Accuracy value (0-1)
 * @returns {string} CSS background class
 */
export function getStatusClass(accuracy) {
	if (accuracy >= 0.75) return 'status-healthy';
	if (accuracy >= 0.65) return 'status-warning';
	return 'status-critical';
}

/**
 * Format time difference from now
 * @param {Date|string} date - Date to format
 * @returns {string} Relative time string (e.g., "2h ago")
 */
export function formatTimeAgo(date) {
	if (!date) return 'Never';
	const d = new Date(date);
	const now = new Date();
	const diffMs = now.getTime() - d.getTime();
	const diffMin = Math.floor(diffMs / 60000);
	const diffHr = Math.floor(diffMin / 60);
	const diffDays = Math.floor(diffHr / 24);

	if (diffMin < 1) return 'just now';
	if (diffMin < 60) return `${diffMin}m ago`;
	if (diffHr < 24) return `${diffHr}h ago`;
	return `${diffDays}d ago`;
}

/**
 * Calculate trend direction
 * @param {number} current - Current value
 * @param {number} previous - Previous value
 * @returns {Object} Trend info {direction: 'up'|'down'|'flat', magnitude: number}
 */
export function calculateTrend(current, previous) {
	if (!previous || previous === 0) return { direction: 'flat', magnitude: 0 };

	const change = current - previous;
	const magnitude = Math.abs(change);

	if (change > 0.01) return { direction: 'up', magnitude };
	if (change < -0.01) return { direction: 'down', magnitude };
	return { direction: 'flat', magnitude: 0 };
}
