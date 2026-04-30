/**
 * API client for Pipeline Prediction Service
 */
import { API_BASE_URL } from '../config.js';

const BASE_URL = `${API_BASE_URL}/api/pipeline-prediction`;

async function request(endpoint, method = 'GET', body = null) {
	// Use auth0_token from localStorage (standard for this app)
	const token =
		typeof window !== 'undefined'
			? localStorage.getItem('auth0_token') || localStorage.getItem('auth_token')
			: null;

	const headers = {
		'Content-Type': 'application/json'
	};

	if (token && token !== 'null') {
		headers['Authorization'] = `Bearer ${token}`;
	}

	const options = {
		method,
		headers
	};

	if (body) {
		options.body = JSON.stringify(body);
	}

	const response = await fetch(`${BASE_URL}${endpoint}`, options);

	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
		throw new Error(error.detail || `Request failed with status ${response.status}`);
	}

	return response.json();
}

export const pipelinePredictionApi = {
	/**
	 * Predict pipeline failure risk for a commit context
	 */
	async predict(params) {
		return request('/predict', 'POST', params);
	},

	/**
	 * Get prediction history for a repository
	 */
	async getHistory(org, repo, limit = 10) {
		return request(`/history/${org}/${repo}?limit=${limit}`);
	},

	/**
	 * Get feature importance for an organization
	 */
	async getFeatureImportance(org) {
		return request(`/feature-importance/${org}`);
	},

	/**
	 * Get training data stats
	 */
	async getStats(org) {
		return request(`/data/stats/${org}`);
	},

	/**
	 * Get info about the active model
	 */
	async getModelInfo(org) {
		return request(`/model/${org}`);
	}
};
