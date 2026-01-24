/**
 * Centralized API Configuration
 * All API URLs should use this configuration for environment-based switching
 */

/**
 * Get the API base URL based on environment
 * @returns {string} The API base URL (e.g., http://localhost:8000 or https://api.withops.com)
 */
export function getApiBaseUrl() {
	return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
}

/**
 * Get the frontend URL based on environment
 * @returns {string} The frontend URL (e.g., http://localhost:5173 or https://app.withops.com)
 */
export function getFrontendUrl() {
	if (typeof window !== 'undefined') {
		return window.location.origin;
	}
	return import.meta.env.VITE_FRONTEND_URL || 'http://localhost:5173';
}

/**
 * Build an API endpoint URL
 * @param {string} path - The API path (e.g., '/api/github/workspace')
 * @returns {string} The full API URL
 */
export function buildApiUrl(path) {
	const baseUrl = getApiBaseUrl();
	// Remove leading slash from path if present to avoid double slashes
	const cleanPath = path.startsWith('/') ? path : `/${path}`;
	return `${baseUrl}${cleanPath}`;
}

export const API_BASE_URL = getApiBaseUrl();
export const FRONTEND_URL = getFrontendUrl();
