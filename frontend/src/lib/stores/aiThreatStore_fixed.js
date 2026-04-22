/**
 * Fixed AIThreatService with proper SvelteKit compatibility
 * This addresses the "Cannot use relative URL with global fetch" error
 */

import { writable, derived, get } from 'svelte/store';

// Simple toast notification function
function showToast(message, type = 'info') {
	console.log(`[${type.toUpperCase()}] ${message}`);
}

// AI Analysis State
export const aiAnalysisState = writable({
	isEnabled: true,
	isAnalyzing: false,
	lastAnalysis: null,
	analysisHistory: [],
	pendingComponents: new Set(),
	errorCount: 0,
	averageResponseTime: 0
});

// AI Configuration
export const aiConfig = writable({
	provider: 'groq',
	autoAnalyze: true,
	realTimeMode: true,
	confidenceThreshold: 0.7,
	maxSuggestions: 5,
	analysisDelay: 500
});

// Current AI Threats
export const aiThreats = writable([]);

// AI Chat Messages
export const aiChatMessages = writable([]);

/**
 * Real-Time AI Threat Analysis Service with SvelteKit compatibility
 */
class AIThreatService {
	constructor() {
		// Use absolute URL for API calls to avoid SvelteKit SSR issues
		const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9060';
		this.apiBase =
			typeof window !== 'undefined'
				? `${API_BASE_URL}/api/ai-threats`
				: `${API_BASE_URL}/api/ai-threats`;
		this.analysisQueue = new Map();
		this.debounceTimers = new Map();
		this.isHealthy = false;

		// Only check health on client side
		if (typeof window !== 'undefined') {
			this.checkHealth();
		}
	}

	/**
	 * Safe fetch wrapper that works in both client and server environments
	 */
	async safeFetch(url, options = {}) {
		try {
			// Only make API calls on the client side
			if (typeof window === 'undefined') {
				console.log('Skipping API call on server side:', url);
				return null;
			}

			const response = await fetch(url, {
				...options,
				headers: {
					'Content-Type': 'application/json',
					...options.headers
				}
			});

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}

			return await response.json();
		} catch (error) {
			console.error(`API call failed: ${url}`, error);
			throw error;
		}
	}

	/**
	 * Check AI service health
	 */
	async checkHealth() {
		// Skip health check on server side
		if (typeof window === 'undefined') {
			return false;
		}

		try {
			const health = await this.safeFetch(`${this.apiBase}/health`);

			if (!health) {
				this.isHealthy = false;
				return false;
			}

			this.isHealthy = health.status === 'healthy';

			if (this.isHealthy) {
				console.log('🤖 AI Threat Analysis: Ready');
				showToast('AI Threat Analysis Ready', 'success');
			} else {
				console.warn('🤖 AI Service unhealthy:', health.error);
				showToast('AI Service Issues', 'error');
			}

			return this.isHealthy;
		} catch (error) {
			console.error('AI health check failed:', error);
			this.isHealthy = false;
			return false;
		}
	}

	/**
	 * Real-time component threat analysis
	 */
	async analyzeComponent(component, canvasContext = null) {
		if (!this.isHealthy || typeof window === 'undefined') {
			console.log('AI service not healthy or running on server, skipping analysis');
			return [];
		}

		const config = get(aiConfig);
		if (!config.autoAnalyze) return [];

		// Update analysis state
		aiAnalysisState.update((state) => ({
			...state,
			isAnalyzing: true,
			pendingComponents: new Set([...state.pendingComponents, component.id])
		}));

		try {
			const startTime = Date.now();

			const result = await this.safeFetch(`${this.apiBase}/analyze/component`, {
				method: 'POST',
				body: JSON.stringify({
					component: component,
					canvas_context: canvasContext
				})
			});

			if (!result) {
				throw new Error('No result from API');
			}

			const responseTime = Date.now() - startTime;

			// Update threats store
			aiThreats.update((current) => {
				// Remove old threats for this component
				const filtered = current.filter((t) => !t.component_ids?.includes(component.id));

				// Add new threats
				const newThreats = result.threats.map((threat) => ({
					...threat,
					component_ids: [component.id],
					source: 'ai',
					timestamp: Date.now(),
					response_time: responseTime
				}));

				return [...filtered, ...newThreats];
			});

			// Update analysis state
			aiAnalysisState.update((state) => {
				const newPending = new Set(state.pendingComponents);
				newPending.delete(component.id);

				return {
					...state,
					isAnalyzing: newPending.size > 0,
					pendingComponents: newPending,
					lastAnalysis: {
						componentId: component.id,
						threatsFound: result.threats.length,
						responseTime,
						confidence: result.confidence,
						timestamp: Date.now()
					},
					averageResponseTime: (state.averageResponseTime + responseTime) / 2
				};
			});

			// Show success notification for fast analysis
			if (responseTime < 3000 && result.threats.length > 0) {
				showToast(`🤖 Found ${result.threats.length} threats`, 'success');
			}

			return result.threats;
		} catch (error) {
			console.error('Component analysis failed:', error);

			// Update error state
			aiAnalysisState.update((state) => {
				const newPending = new Set(state.pendingComponents);
				newPending.delete(component.id);

				return {
					...state,
					isAnalyzing: newPending.size > 0,
					pendingComponents: newPending,
					errorCount: state.errorCount + 1
				};
			});

			showToast('AI Analysis Failed', 'error');

			return [];
		}
	}

	/**
	 * Ask AI a threat modeling question
	 */
	async askQuestion(question, canvasContext) {
		if (!question.trim() || typeof window === 'undefined') return null;

		try {
			// Add user message to chat
			aiChatMessages.update((messages) => [
				...messages,
				{
					id: Date.now(),
					type: 'user',
					content: question,
					timestamp: Date.now()
				}
			]);

			const result = await this.safeFetch(`${this.apiBase}/ask`, {
				method: 'POST',
				body: JSON.stringify({
					question: question,
					canvas_context: canvasContext
				})
			});

			if (!result) {
				throw new Error('No response from AI service');
			}

			// Add AI response to chat
			aiChatMessages.update((messages) => [
				...messages,
				{
					id: Date.now() + 1,
					type: 'ai',
					content: result.answer,
					followup_suggestions: result.followup_suggestions,
					response_time: result.response_time_ms,
					timestamp: Date.now()
				}
			]);

			return result;
		} catch (error) {
			console.error('AI question failed:', error);

			// Add error message
			aiChatMessages.update((messages) => [
				...messages,
				{
					id: Date.now() + 1,
					type: 'error',
					content: "Sorry, I couldn't process your question right now.",
					timestamp: Date.now()
				}
			]);

			return null;
		}
	}

	/**
	 * Dismiss a threat suggestion
	 */
	async dismissThreat(threatId, componentId, reason = null) {
		if (typeof window === 'undefined') return false;

		try {
			const result = await this.safeFetch(`${this.apiBase}/threats/dismiss`, {
				method: 'POST',
				body: JSON.stringify({
					threat_id: threatId,
					component_id: componentId,
					reason: reason
				})
			});

			if (!result) return false;

			if (result.success) {
				// Remove threat from store
				aiThreats.update((current) => current.filter((threat) => threat.id !== threatId));

				showToast('Threat dismissed', 'success');
				return true;
			}

			return false;
		} catch (error) {
			console.error('Threat dismissal failed:', error);
			showToast('Failed to dismiss threat', 'error');
			return false;
		}
	}

	/**
	 * Get detailed mitigation with implementation steps
	 */
	async getDetailedMitigation(threatId, threatTitle, componentType, canvasContext = null) {
		if (typeof window === 'undefined') return null;

		try {
			const result = await this.safeFetch(`${this.apiBase}/mitigation/detailed`, {
				method: 'POST',
				body: JSON.stringify({
					threat_id: threatId,
					threat_title: threatTitle,
					component_type: componentType,
					canvas_context: canvasContext
				})
			});

			return result?.mitigation || null;
		} catch (error) {
			console.error('Detailed mitigation failed:', error);
			return null;
		}
	}

	/**
	 * Create Jira task from threat
	 */
	async createJiraTask(threatData, mitigationData, jiraConfig) {
		if (typeof window === 'undefined') return null;

		try {
			const result = await this.safeFetch(`${this.apiBase}/jira/create-task`, {
				method: 'POST',
				body: JSON.stringify({
					threat_data: threatData,
					mitigation_data: mitigationData,
					jira_config: jiraConfig
				})
			});

			if (!result) return null;

			if (result.jira_task?.success) {
				showToast(`Jira task created: ${result.jira_task.ticket_id}`, 'success');
				return result.jira_task;
			}

			return null;
		} catch (error) {
			console.error('Jira task creation failed:', error);
			showToast('Failed to create Jira task', 'error');
			return null;
		}
	}

	/**
	 * Check if canvas has changed and threats need refreshing
	 */
	async checkCanvasRefresh(oldCanvasHash, canvasContext) {
		if (typeof window === 'undefined') return { changed: false, error: 'Server side' };

		try {
			const result = await this.safeFetch(`${this.apiBase}/canvas/refresh-check`, {
				method: 'POST',
				body: JSON.stringify({
					old_canvas_hash: oldCanvasHash,
					canvas_context: canvasContext
				})
			});

			if (!result) return { changed: false, error: 'No response' };

			const refreshStatus = result.refresh_status;

			if (refreshStatus?.canvas_changed) {
				console.log('Canvas changed, refreshing threats:', refreshStatus.change_summary);

				// Clear old threats and trigger re-analysis
				aiThreats.update((current) => current.filter((threat) => threat.source !== 'ai'));

				showToast('Canvas changed - updating threats', 'info');

				return {
					changed: true,
					newHash: refreshStatus.new_hash,
					changeSummary: refreshStatus.change_summary
				};
			}

			return {
				changed: false,
				hash: refreshStatus?.new_hash
			};
		} catch (error) {
			console.error('Canvas refresh check failed:', error);
			return { changed: false, error: error.message };
		}
	}

	/**
	 * Get threat management features
	 */
	async getManagementFeatures() {
		if (typeof window === 'undefined') return {};

		try {
			const result = await this.safeFetch(`${this.apiBase}/threats/management/features`);
			return result?.features || {};
		} catch (error) {
			console.error('Failed to get management features:', error);
			return {};
		}
	}

	// Legacy methods for backward compatibility
	async analyzeDataFlow(flow, sourceComponent, targetComponent) {
		if (!this.isHealthy || typeof window === 'undefined') return [];
		// Implementation would use safeFetch here too
		return [];
	}

	async getMitigationDetails(threatTitle, componentType) {
		if (typeof window === 'undefined') return null;
		// Implementation would use safeFetch here too
		return null;
	}

	async liveAnalysis(component) {
		if (!this.isHealthy || typeof window === 'undefined') return [];
		// Implementation would use safeFetch here too
		return [];
	}

	scheduleAnalysis(component, canvasContext = null, delay = 500) {
		if (typeof window === 'undefined') return;

		const componentId = component.id;

		// Clear existing timer
		if (this.debounceTimers.has(componentId)) {
			clearTimeout(this.debounceTimers.get(componentId));
		}

		// Schedule new analysis
		const timer = setTimeout(() => {
			this.analyzeComponent(component, canvasContext);
			this.debounceTimers.delete(componentId);
		}, delay);

		this.debounceTimers.set(componentId, timer);
	}
}

// Create service instance
export const aiThreatService = new AIThreatService();

// Derived stores for UI
export const activeAIThreats = derived([aiThreats, aiConfig], ([threats, config]) =>
	threats
		.filter((threat) => threat.confidence >= config.confidenceThreshold)
		.slice(0, config.maxSuggestions)
);

export const aiAnalysisStats = derived(aiAnalysisState, (state) => ({
	isActive: state.isAnalyzing,
	pendingCount: state.pendingComponents.size,
	lastResponseTime: state.lastAnalysis?.responseTime || 0,
	averageResponseTime: Math.round(state.averageResponseTime),
	errorRate: state.errorCount / (state.analysisHistory.length || 1),
	isRealTime: state.averageResponseTime < 5000
}));

// AI Actions
export const aiActions = {
	// Enable/disable AI analysis
	toggleAI: () => {
		aiConfig.update((config) => ({
			...config,
			autoAnalyze: !config.autoAnalyze
		}));
	},

	// Toggle real-time mode
	toggleRealTime: () => {
		aiConfig.update((config) => ({
			...config,
			realTimeMode: !config.realTimeMode
		}));
	},

	// Clear all AI threats
	clearThreats: () => {
		aiThreats.set([]);
	},

	// Clear chat messages
	clearChat: () => {
		aiChatMessages.set([]);
	},

	// Manually trigger analysis
	analyzeNow: (component, canvasContext) => {
		return aiThreatService.analyzeComponent(component, canvasContext);
	},

	// Ask AI question
	askAI: (question, canvasContext) => {
		return aiThreatService.askQuestion(question, canvasContext);
	},

	// Dismiss threat
	dismissThreat: (threatId, componentId, reason) => {
		return aiThreatService.dismissThreat(threatId, componentId, reason);
	},

	// Get detailed mitigation
	getDetailedMitigation: (threatId, threatTitle, componentType, canvasContext) => {
		return aiThreatService.getDetailedMitigation(
			threatId,
			threatTitle,
			componentType,
			canvasContext
		);
	},

	// Create Jira task
	createJiraTask: (threatData, mitigationData, jiraConfig) => {
		return aiThreatService.createJiraTask(threatData, mitigationData, jiraConfig);
	},

	// Check canvas refresh
	checkCanvasRefresh: (oldHash, canvasContext) => {
		return aiThreatService.checkCanvasRefresh(oldHash, canvasContext);
	},

	// Get management features
	getManagementFeatures: () => {
		return aiThreatService.getManagementFeatures();
	}
};

export default aiThreatService;
