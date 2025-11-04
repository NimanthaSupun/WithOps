/**
 * Real-Time AI Threat Analysis Store
 * Ultra-fast threat analysis using Groq AI
 * Fixed for SvelteKit compatibility
 */

import { writable, derived, get } from 'svelte/store';

// Simple toast notification function
function showToast(message, type = 'info') {
	console.log(`[${type.toUpperCase()}] ${message}`);
	// You can implement a custom toast system here if needed
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
	provider: 'groq', // 'groq', 'gemini', 'claude'
	autoAnalyze: true,
	realTimeMode: true,
	confidenceThreshold: 0.7,
	maxSuggestions: 5,
	analysisDelay: 200 // Reduced to 200ms for faster real-time analysis
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
		this.apiBase =
			typeof window !== 'undefined'
				? 'http://localhost:8000/api/ai-threats'
				: 'http://localhost:8000/api/ai-threats';
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

			// Add timeout to prevent hanging requests - optimized for real-time
			const controller = new AbortController();
			const timeoutId = setTimeout(() => controller.abort(), 6000); // 6 second timeout for faster response

			const response = await fetch(url, {
				...options,
				headers: {
					'Content-Type': 'application/json',
					...options.headers
				},
				signal: controller.signal
			});

			clearTimeout(timeoutId);

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}

			return await response.json();
		} catch (error) {
			if (error.name === 'AbortError') {
				console.error(`API call timeout: ${url}`);
				throw new Error('Request timeout - AI service taking too long');
			}
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
	 * Real-time data flow analysis
	 */
	async analyzeDataFlow(flow, sourceComponent, targetComponent) {
		if (!this.isHealthy || typeof window === 'undefined') return [];

		try {
			const result = await this.safeFetch(`${this.apiBase}/analyze/flow`, {
				method: 'POST',
				body: JSON.stringify({
					flow: flow,
					source_component: sourceComponent,
					target_component: targetComponent
				})
			});

			if (!result) return [];

			// Add flow threats to store
			aiThreats.update((current) => [
				...current,
				...result.threats.map((threat) => ({
					...threat,
					source: 'ai-flow',
					flow_id: `${flow.source}-${flow.target}`,
					timestamp: Date.now()
				}))
			]);

			return result.threats;
		} catch (error) {
			console.error('Flow analysis failed:', error);
			return [];
		}
	}

	/**
	 * Debounced real-time analysis
	 */
	scheduleAnalysis(component, canvasContext = null, delay = 500) {
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
	 * Get detailed mitigation for a threat
	 */
	async getMitigationDetails(threatTitle, componentType) {
		try {
			const response = await fetch(`${this.apiBase}/mitigation/details`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					threat_title: threatTitle,
					component_type: componentType
				})
			});

			const result = await response.json();
			return result.mitigation_details;
		} catch (error) {
			console.error('Mitigation details failed:', error);
			return null;
		}
	}

	/**
	 * Live analysis for real-time feedback
	 */
	async liveAnalysis(component) {
		if (!this.isHealthy) return [];

		try {
			const response = await fetch(`${this.apiBase}/analyze/live`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					component: component
				})
			});

			const result = await response.json();

			// Update with quick heuristic threats
			if (result.threats.length > 0) {
				aiThreats.update((current) => {
					const filtered = current.filter((t) => !t.id?.startsWith('quick-'));
					return [
						...filtered,
						...result.threats.map((t) => ({
							...t,
							source: 'ai-live',
							component_ids: [component.id],
							timestamp: Date.now()
						}))
					];
				});
			}

			return result.threats;
		} catch (error) {
			console.error('Live analysis failed:', error);
			return [];
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
		try {
			const response = await fetch(`${this.apiBase}/mitigation/detailed`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					threat_id: threatId,
					threat_title: threatTitle,
					component_type: componentType,
					canvas_context: canvasContext
				})
			});

			const result = await response.json();
			return result.mitigation;
		} catch (error) {
			console.error('Detailed mitigation failed:', error);
			return null;
		}
	}

	/**
	 * Create Jira task from threat
	 */
	async createJiraTask(threatData, mitigationData, jiraConfig) {
		try {
			const response = await fetch(`${this.apiBase}/jira/create-task`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					threat_data: threatData,
					mitigation_data: mitigationData,
					jira_config: jiraConfig
				})
			});

			const result = await response.json();

			if (result.jira_task.success) {
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
		try {
			const response = await fetch(`${this.apiBase}/canvas/refresh-check`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					old_canvas_hash: oldCanvasHash,
					canvas_context: canvasContext
				})
			});

			const result = await response.json();
			const refreshStatus = result.refresh_status;

			if (refreshStatus.canvas_changed) {
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
				hash: refreshStatus.new_hash
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
		try {
			const response = await fetch(`${this.apiBase}/threats/management/features`);
			const result = await response.json();
			return result.features;
		} catch (error) {
			console.error('Failed to get management features:', error);
			return {};
		}
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
