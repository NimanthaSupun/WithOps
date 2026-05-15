<script>
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { writable } from 'svelte/store';
	import { tick } from 'svelte';
	import * as d3 from 'd3';

	const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';

	// Import collaboration components and stores
	import CollaborationLayer from '$lib/components/CollaborationLayer.svelte';
	import CollaborationStats from '$lib/components/CollaborationStats.svelte';
	import ShareCollaboration from '$lib/components/ShareCollaboration.svelte';
	import {
		initializeCollaboration,
		disconnectCollaboration,
		liveElements,
		liveConnections,
		liveThreats,
		liveMetadata,
		updateLiveElement,
		updateLiveConnection,
		updateLiveMetadata,
		updatePresence,
		isConnected as collaborationConnected,
		onlineUsersCount
	} from '$lib/stores/collaboration-yjs.js';

	// Import auth for user data
	import { getAuthClient } from '$lib/auth.js';

	// Stores for canvas state
	const canvasData = writable({
		elements: [],
		connections: [],
		threats: [],
		metadata: { zoom: 1.0, panX: 0, panY: 0 }
	});

	const selectedElement = writable(null);
	const selectedConnection = writable(null);
	const canvasMode = writable('select'); // select, connect
	const showThreatDialog = writable(false);
	const currentElementForThreat = writable(null);

	// Store for editing threats
	const editingThreat = writable(null);
	const showEditThreatDialog = writable(false);

	// User feedback system
	let notification = '';
	let showNotification = false;

	function showUserNotification(message) {
		notification = message;
		showNotification = true;
		setTimeout(() => {
			showNotification = false;
		}, 3000);
	}

	// Reactive statements for real-time updates
	$: if ($canvasData) {
		// Trigger re-render when canvas data changes
		if (svg && g) {
			renderCanvas();
		}
	}

	$: if ($selectedElement) {
		// Force properties panel to update when selection changes
		console.log('🎯 Selected element changed:', $selectedElement.id);
	}

	$: if ($selectedConnection) {
		// Force properties panel to update when connection selection changes
		console.log('🔗 Selected connection changed:', $selectedConnection.id);
	}

	// Simple connection state (EASY TO UNDERSTAND!)
	let isConnecting = false;
	let connectionStart = null;
	let isDragging = false;
	let isResizing = false;

	// Component variables
	let orgName = '';
	let modelId = '';
	let modelData = null;
	let loading = true;
	let error = null;
	let saving = false;
	let lastSaved = null;
	let aiAnalyzing = false;
	let lastAnalysisRequest = 0;
	const ANALYSIS_DEBOUNCE_MS = 2000; // Prevent requests within 2 seconds

	// AI Analysis Panel Variables
	let showAIAnalysisPanel = false;
	let showDrawingToolsPanel = false; // Start hidden, user discovers via floating button
	let showAnalysisHistory = false; // Toggle for showing/hiding analysis history view
	let aiAnalysisResult = null;
	let uploadingDocument = false;
	let analysisHistory = []; // Store past analysis results
	let loadingHistory = false;
	let currentAIView = 'welcome'; // 'welcome' or 'result'

	// WebSocket for async threat analysis
	let ws = null;
	let wsReconnectAttempts = 0;
	let wsMaxReconnectAttempts = 5;
	let wsPingInterval = null; // Heartbeat interval
	let pendingTaskId = null; // Track the current async task
	let taskStatus = 'idle'; // 'idle', 'queued', 'processing', 'completed', 'failed'

	// Debug reactive statement to track aiAnalysisResult changes
	$: {
		console.log('🔍 aiAnalysisResult changed:', {
			isNull: aiAnalysisResult === null,
			isUndefined: aiAnalysisResult === undefined,
			exists: !!aiAnalysisResult,
			hasStructuredAnalysis: !!aiAnalysisResult?.structured_analysis,
			currentView: currentAIView,
			showPanel: showAIAnalysisPanel
		});
	}

	// Panel Resizing Variables
	let aiPanelWidth = 600; // Default width in pixels (w-150 = 600px)
	let isResizingAIPanel = false;
	let aiPanelMinWidth = 400; // Minimum width
	let aiPanelMaxWidth = 1000; // Maximum width

	// AI Review System Variables
	let reviewState = {}; // Track review state per threat category
	let showReviewDialog = false;
	let currentReviewCategory = null;
	let currentReviewThreat = null;
	let reviewFeedback = '';
	let reviewValid = null; // true for valid, false for invalid

	// Individual AI Threat Review Variables
	let showIndividualThreatReview = false;
	let currentThreatForReview = null;
	let currentThreatCategory = null;
	let currentThreatIndex = null;
	let threatReviewFeedback = '';
	let threatReviewValid = null;
	let reanalyzing = false;

	// UI State Management
	let expandedSections = {
		architecture: true,
		risk_dashboard: false,
		mitigation_plan: false
	};

	// Toggle section expansion
	function toggleSection(section) {
		expandedSections[section] = !expandedSections[section];
	}

	// Helper functions to parse AI analysis text into structured data
	function parseServiceOverview(content) {
		const lines = content.split('\n').filter((l) => l.trim());
		const result = {
			serviceName: '',
			description: '',
			architectureSummary: '',
			assetsToProtect: ''
		};

		for (const line of lines) {
			if (line.includes('Service Name:')) {
				result.serviceName = line.replace(/^\*\*Service Name:\*\*\s*/, '').trim();
			} else if (line.includes('Description:')) {
				result.description = line.replace(/^\*\*Description:\*\*\s*/, '').trim();
			} else if (line.includes('Architecture Summary:')) {
				result.architectureSummary = line.replace(/^\*\*Architecture Summary:\*\*\s*/, '').trim();
			} else if (line.includes('Assets to Protect:')) {
				result.assetsToProtect = line.replace(/^\*\*Assets to Protect:\*\*\s*/, '').trim();
			}
		}

		return result;
	}

	function parseThreatScope(content) {
		const lines = content.split('\n').filter((l) => l.trim());
		const result = {
			inScope: [],
			assumptions: []
		};

		let currentSection = '';
		for (const line of lines) {
			if (line.includes('In-Scope Components:')) {
				currentSection = 'inScope';
			} else if (line.includes('Assumptions:')) {
				currentSection = 'assumptions';
			} else if (line.startsWith('- ') && currentSection) {
				const item = line.replace(/^- /, '').trim();
				result[currentSection].push(item);
			}
		}

		return result;
	}

	function parseMethodologyContent(content, methodology = 'STRIDE') {
		const lines = content.split('\n').filter((l) => l.trim());
		const result = {
			userIdentified: [],
			aiSuggested: [],
			mitigations: []
		};

		let currentSection = '';
		for (const line of lines) {
			const trimmedLine = line.trim();

			// Check for new structured format section headers
			if (
				trimmedLine.includes('✓ User Identified Threats') ||
				trimmedLine.includes('User Identified Threats')
			) {
				currentSection = 'userIdentified';
				continue;
			} else if (
				trimmedLine.includes('🤖 AI Suggested Threats') ||
				trimmedLine.includes('AI Suggested Threats')
			) {
				currentSection = 'aiSuggested';
				continue;
			} else if (
				trimmedLine.includes('🛡️ Recommended Mitigations') ||
				trimmedLine.includes('Recommended Mitigations')
			) {
				currentSection = 'mitigations';
				continue;
			}

			// Legacy format compatibility
			else if (trimmedLine.includes('User Identified:')) {
				currentSection = 'userIdentified';
				// Extract the threat from the same line if it exists
				const threatMatch = trimmedLine.match(/User Identified:[^-]*-\s*(.+)/);
				if (threatMatch) {
					result.userIdentified.push(threatMatch[1].trim());
				}
				continue;
			} else if (trimmedLine.includes('AI Suggested:')) {
				currentSection = 'aiSuggested';
				continue;
			} else if (trimmedLine.includes('Mitigations:')) {
				currentSection = 'mitigations';
				continue;
			}

			// Extract bullet point items
			if ((trimmedLine.startsWith('• ') || trimmedLine.startsWith('- ')) && currentSection) {
				const item = trimmedLine.replace(/^[•-]\s*/, '').trim();
				if (item && !result[currentSection].includes(item)) {
					// Avoid duplicates
					result[currentSection].push(item);
				}
			}
		}

		return result;
	}

	// Initialize review state when analysis changes
	$: if (aiAnalysisResult?.structured_analysis?.threat_categories) {
		initializeReviewState(aiAnalysisResult.structured_analysis.threat_categories);
	}

	// Load analysis history when AI panel opens initially (not when user deletes items)
	let hasInitiallyLoadedHistory = false;
	$: if (
		showAIAnalysisPanel &&
		!loadingHistory &&
		analysisHistory.length === 0 &&
		!hasInitiallyLoadedHistory
	) {
		hasInitiallyLoadedHistory = true;

		// First try to load from localStorage (maintains multiple analyses)
		let loadedFromLocal = false;
		try {
			const localStorageKey = `analysis-history-${modelId}`;
			const localHistory = localStorage.getItem(localStorageKey);
			if (localHistory) {
				const parsedHistory = JSON.parse(localHistory);
				if (Array.isArray(parsedHistory) && parsedHistory.length > 0) {
					// Sort by timestamp (newest first) and ensure valid entries
					const validHistory = parsedHistory
						.filter((entry) => entry && entry.timestamp && entry.id)
						.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

					if (validHistory.length > 0) {
						analysisHistory = validHistory;
						console.log(`📊 Loaded ${validHistory.length} analyses from localStorage`);
						console.log(
							'🔍 Analysis IDs:',
							validHistory.map((h) => h.id)
						);
						loadedFromLocal = true;
					}
				}
			}
		} catch (e) {
			console.warn('⚠️ Failed to load from localStorage:', e);
			// Clear corrupted localStorage
			try {
				localStorage.removeItem(`analysis-history-${modelId}`);
			} catch (clearError) {
				console.warn('⚠️ Failed to clear corrupted localStorage:', clearError);
			}
		}

		// Always also try to load from database to merge any server-side analyses
		if (loadedFromLocal) {
			// Load database analyses and merge with local ones
			loadAnalysisHistory()
				.then(() => {
					console.log('📊 Merged database and localStorage analyses');
				})
				.catch((error) => {
					console.warn('⚠️ Failed to merge database analyses:', error);
				});
		} else {
			// No local history, load from database only
			loadAnalysisHistory();
		}
	}

	// Navigation functions for AI views
	function showAIWelcome() {
		currentAIView = 'welcome';
		aiAnalysisResult = null;
	}

	function showAIResult(analysisData) {
		aiAnalysisResult = analysisData;
		currentAIView = 'result';
	}

	// AI Panel Resize Functions
	function startAIPanelResize(event) {
		isResizingAIPanel = true;
		event.preventDefault();

		// Add global mouse move and mouse up listeners
		document.addEventListener('mousemove', handleAIPanelResize);
		document.addEventListener('mouseup', stopAIPanelResize);
		document.body.style.cursor = 'e-resize';
		document.body.style.userSelect = 'none'; // Prevent text selection during resize
	}

	function handleAIPanelResize(event) {
		if (!isResizingAIPanel) return;

		// Calculate new width based on mouse position from right edge of viewport
		const newWidth = window.innerWidth - event.clientX;

		// Constrain width within min/max bounds
		const constrainedWidth = Math.max(aiPanelMinWidth, Math.min(aiPanelMaxWidth, newWidth));
		aiPanelWidth = constrainedWidth;
	}

	function stopAIPanelResize() {
		isResizingAIPanel = false;
		document.removeEventListener('mousemove', handleAIPanelResize);
		document.removeEventListener('mouseup', stopAIPanelResize);
		document.body.style.cursor = '';
		document.body.style.userSelect = '';
	}

	function initializeReviewState(categories) {
		if (!categories) return;

		// Ensure categories is an array
		const categoryArray = Array.isArray(categories) ? categories : Object.keys(categories);
		if (categoryArray.length === 0) return;

		// Initialize review state for each threat category
		reviewState = {};
		categoryArray.forEach((category) => {
			if (!reviewState[category]) {
				reviewState[category] = {
					reviewed: false,
					valid: null,
					feedback: '',
					timestamp: null
				};
			}
		});
	}

	// Canvas references
	let svg;
	let g;
	let canvasContainer;

	// Canvas dimensions
	const canvasWidth = 2000;
	const canvasHeight = 1500;

	// Element Types Configuration - Generic Drawing Tools
	const ELEMENT_TYPES = {
		rectangle: {
			label: 'Rectangle',
			icon: '⬜',
			color: 'transparent',
			border: '#000000',
			borderWidth: 2,
			defaultSize: { width: 120, height: 80 },
			minSize: { width: 20, height: 20 },
			maxSize: { width: 2000, height: 1500 },
			resizable: true,
			shape: 'rectangle',
			description: 'A rectangular shape for general use'
		},
		circle: {
			label: 'Circle',
			icon: '⭕',
			color: 'transparent',
			border: '#000000',
			borderWidth: 2,
			defaultSize: { width: 80, height: 80 },
			minSize: { width: 20, height: 20 },
			maxSize: { width: 1000, height: 1000 },
			resizable: true,
			shape: 'circle',
			description: 'A circular shape for general use'
		},
		square: {
			label: 'Square',
			icon: '◻️',
			color: 'transparent',
			border: '#000000',
			borderWidth: 2,
			defaultSize: { width: 80, height: 80 },
			minSize: { width: 20, height: 20 },
			maxSize: { width: 1000, height: 1000 },
			resizable: true,
			shape: 'square',
			description: 'A square shape for general use'
		},
		triangle: {
			label: 'Triangle',
			icon: '�',
			color: 'transparent',
			border: '#000000',
			borderWidth: 2,
			defaultSize: { width: 80, height: 80 },
			minSize: { width: 20, height: 20 },
			maxSize: { width: 1000, height: 1000 },
			resizable: true,
			shape: 'triangle',
			description: 'A triangular shape for general use'
		},
		diamond: {
			label: 'Diamond',
			icon: '💎',
			color: 'transparent',
			border: '#000000',
			borderWidth: 2,
			defaultSize: { width: 80, height: 80 },
			minSize: { width: 20, height: 20 },
			maxSize: { width: 1000, height: 1000 },
			resizable: true,
			shape: 'diamond',
			description: 'A diamond shape for general use'
		},
		frame: {
			label: 'Frame',
			icon: '�️',
			color: '#FFFFFF', // Solid white background for sub-canvas behavior
			border: '#E5E7EB',
			borderWidth: 2, // Thicker border to emphasize container
			defaultSize: { width: 300, height: 200 },
			minSize: { width: 100, height: 80 },
			maxSize: { width: 2000, height: 1500 },
			resizable: true,
			shape: 'frame',
			description: 'A frame container for grouping other elements - acts like a sub-canvas'
		},
		dataflow: {
			label: 'Connection Line',
			icon: '➡️',
			color: '#000000',
			description: 'A connection line between elements'
		}
	};

	// Component counters for auto-numbering
	let componentCounters = {
		rectangle: 0,
		circle: 0,
		square: 0,
		triangle: 0,
		diamond: 0,
		frame: 0,
		dataflow: 0,
		connection: 0 // Add connection counter
	};

	// Text editing state
	let editingElement = null;
	let editingText = '';
	let textEditPosition = { x: 0, y: 0 };
	let showTextInput = false;

	// Function to get next component name with numbering
	function getNextComponentName(type) {
		componentCounters[type]++;
		const config = ELEMENT_TYPES[type];
		const newName = `${config.label} ${componentCounters[type]}`;
		console.log(`🔢 Generated name for ${type}: ${newName} (counter: ${componentCounters[type]})`);
		return newName;
	}

	// Text editing functions
	function startTextEditing(element, event) {
		if (event) {
			event.stopPropagation();
		}

		editingElement = element;
		editingText = element.name || '';

		// Calculate position for text input overlay
		const svgRect = svg.node().getBoundingClientRect();
		const transform = d3.zoomTransform(svg.node());

		textEditPosition = {
			x: svgRect.left + element.position.x * transform.k + transform.x - 50,
			y: svgRect.top + element.position.y * transform.k + transform.y - 10
		};

		showTextInput = true;

		// Focus the input after a small delay to ensure it's rendered
		setTimeout(() => {
			const textInput = document.getElementById('text-edit-input');
			if (textInput) {
				textInput.focus();
				textInput.select();
			}
		}, 10);

		console.log('📝 Started text editing for:', element.name);
	}

	function finishTextEditing() {
		if (!editingElement) return;

		const newText = editingText.trim();
		if (newText && newText !== editingElement.name) {
			// Update the element name
			canvasData.update((data) => {
				const elementIndex = data.elements.findIndex((el) => el.id === editingElement.id);
				if (elementIndex !== -1) {
					data.elements[elementIndex].name = newText;
				}
				return data;
			});

			// Update selected element if it's the one being edited
			if ($selectedElement && $selectedElement.id === editingElement.id) {
				selectedElement.update((el) => ({ ...el, name: newText }));
			}

			renderCanvas();
			autoSave();
			showUserNotification(`✅ Renamed to "${newText}"`);
		}

		// Clear editing state
		editingElement = null;
		editingText = '';
		showTextInput = false;

		console.log('✅ Finished text editing');
	}

	function cancelTextEditing() {
		editingElement = null;
		editingText = '';
		showTextInput = false;
		console.log('❌ Cancelled text editing');
	}

	function handleTextEditKeydown(event) {
		if (event.key === 'Enter') {
			event.preventDefault();
			finishTextEditing();
		} else if (event.key === 'Escape') {
			event.preventDefault();
			cancelTextEditing();
		}
	}

	// Function to initialize counters based on existing components
	function initializeComponentCounters() {
		// Reset counters
		componentCounters = {
			rectangle: 0,
			circle: 0,
			square: 0,
			triangle: 0,
			diamond: 0,
			frame: 0,
			dataflow: 0
		};

		// Count existing components to set proper starting numbers
		if ($canvasData && $canvasData.elements) {
			$canvasData.elements.forEach((element) => {
				if (componentCounters.hasOwnProperty(element.type)) {
					// Extract number from existing component name
					const match = element.name.match(/(\d+)$/);
					if (match) {
						const num = parseInt(match[1]);
						if (num > componentCounters[element.type]) {
							componentCounters[element.type] = num;
						}
					} else {
						// If no number found, increment counter
						componentCounters[element.type]++;
					}
				}
			});
		}

		console.log('🔢 Initialized component counters:', componentCounters);
	}

	// Collaboration state
	let collaborationInitialized = false;
	let currentUser = null; // Will be loaded from Auth0

	// Load current user from Auth0
	async function loadCurrentUser() {
		try {
			const auth0 = await getAuthClient();
			const user = await auth0.getUser();
			if (user) {
				currentUser = {
					sub: user.sub,
					name: user.name || user.email || 'Anonymous User',
					email: user.email,
					avatar: user.picture || '',
					color: '#3B82F6'
				};
			} else {
				// Fallback for non-authenticated users
				currentUser = {
					sub: 'anonymous',
					name: 'Anonymous User',
					avatar: '',
					color: '#3B82F6'
				};
			}
		} catch (error) {
			console.error('Failed to load user:', error);
			currentUser = {
				sub: 'anonymous',
				name: 'Anonymous User',
				avatar: '',
				color: '#3B82F6'
			};
		}
	}

	// WebSocket initialization for async threat analysis
	function initWebSocket() {
		if (!currentUser || !currentUser.sub) {
			console.warn('⚠️ Cannot initialize WebSocket: no user ID');
			return;
		}

		try {
			const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
			// URL encode user ID to handle special characters like | in Auth0 IDs
			const encodedUserId = encodeURIComponent(currentUser.sub);
			// Connect to Events Hub (backend) for WebSocket on port 9100
			const wsBase = import.meta.env.VITE_WS_BASE_URL || 'http://localhost:9100';
			const wsHost = wsBase.replace(/^https?:\/\//, '');
			const wsUrl = `${wsProtocol}//${wsHost}/ws/${encodedUserId}`;

			console.log('🔌 Connecting to WebSocket:', wsUrl);
			ws = new WebSocket(wsUrl);

			ws.onopen = () => {
				console.log('✅ WebSocket connected');
				wsReconnectAttempts = 0;
				showUserNotification('🔌 Real-time updates connected');

				// Start heartbeat to keep connection alive
				wsPingInterval = setInterval(() => {
					if (ws && ws.readyState === WebSocket.OPEN) {
						ws.send(JSON.stringify({ type: 'ping' }));
					}
				}, 30000); // Ping every 30 seconds
			};

			ws.onmessage = (event) => {
				try {
					const message = JSON.parse(event.data);
					console.log('📨 WebSocket message received:', message);

					if (message.event === 'threat.analysis.completed') {
						handleThreatAnalysisCompleted(message.data);
					} else if (message.event === 'threat.analysis.failed') {
						handleThreatAnalysisFailed(message.data);
					}
				} catch (error) {
					console.error('❌ Failed to parse WebSocket message:', error);
				}
			};

			ws.onerror = (error) => {
				console.error('❌ WebSocket error:', error);
			};

			ws.onclose = () => {
				console.log('🔌 WebSocket disconnected');
				ws = null;

				// Clear ping interval
				if (wsPingInterval) {
					clearInterval(wsPingInterval);
					wsPingInterval = null;
				}

				// Attempt to reconnect
				if (wsReconnectAttempts < wsMaxReconnectAttempts) {
					wsReconnectAttempts++;
					const delay = Math.min(1000 * Math.pow(2, wsReconnectAttempts), 30000);
					console.log(
						`🔄 Reconnecting in ${delay}ms (attempt ${wsReconnectAttempts}/${wsMaxReconnectAttempts})`
					);
					setTimeout(initWebSocket, delay);
				}
			};
		} catch (error) {
			console.error('❌ Failed to initialize WebSocket:', error);
		}
	}

	// Cleanup WebSocket on component destroy
	function cleanupWebSocket() {
		if (wsPingInterval) {
			clearInterval(wsPingInterval);
			wsPingInterval = null;
		}
		if (ws) {
			console.log('🔌 Closing WebSocket connection');
			ws.close();
			ws = null;
		}
	}

	// Handle completed threat analysis from WebSocket
	function handleThreatAnalysisCompleted(data) {
		console.log('✅ Threat analysis completed:', data);

		// Stop polling if active
		if (pollIntervalId) {
			clearInterval(pollIntervalId);
			pollIntervalId = null;
			console.log('🛑 Stopped polling - result received via WebSocket');
		}

		taskStatus = 'completed';
		aiAnalyzing = false;

		if (data.success) {
			// Process the result same way as synchronous analysis
			const result = data;

			// Parse if needed
			if (!result.structured_analysis && result.analysis) {
				console.log('📝 Backend provided raw text, parsing into structured format...');
				result.structured_analysis = parseRawAnalysisToStructured(
					result.analysis,
					result.methodology || 'STRIDE'
				);
			}

			// Store and display
			aiAnalysisResult = result;
			showAIAnalysisPanel = true;
			currentAIView = 'result';

			showUserNotification('✅ AI analysis completed!');

			// Save to history (same logic as synchronous)
			saveAnalysisToHistory(result);
		} else {
			showUserNotification('❌ Analysis failed: ' + (data.error || 'Unknown error'));
		}

		pendingTaskId = null;
	}

	// Handle failed threat analysis from WebSocket
	function handleThreatAnalysisFailed(data) {
		console.error('❌ Threat analysis failed:', data);

		taskStatus = 'failed';
		aiAnalyzing = false;
		pendingTaskId = null;

		showUserNotification('❌ Analysis failed: ' + (data.error || 'Unknown error'));
	}

	// Methodology state
	let currentMethodology = 'STRIDE'; // Default methodology

	// Methodology change handler
	function handleMethodologyChange(event) {
		const newMethodology = event.target.value;
		console.log(`🔄 Methodology changed from ${currentMethodology} to ${newMethodology}`);
		currentMethodology = newMethodology;

		// Update model metadata
		canvasData.update((data) => {
			if (!data.metadata) data.metadata = {};
			data.metadata.methodology = newMethodology;
			return data;
		});

		autoSave();
		showUserNotification(`✅ Switched to ${newMethodology} methodology`);
	}

	// Sync local canvas data with live collaboration data
	$: if ($collaborationConnected && $liveElements.length > 0) {
		canvasData.update((current) => ({
			...current,
			elements: $liveElements,
			connections: $liveConnections,
			threats: $liveThreats,
			metadata: $liveMetadata
		}));
	}

	// Debug: Log collaboration state changes
	$: console.log('🔍 Collaboration state changed:', {
		collaborationInitialized,
		currentUser: currentUser ? currentUser.name : 'null'
	});

	// Track analyzed components to avoid duplicate analysis
	let analyzedComponents = new Set();
	let analysisQueue = [];
	let isProcessingQueue = false;

	// Throttled AI analysis to prevent rate limiting
	async function processAnalysisQueue() {
		if (isProcessingQueue || analysisQueue.length === 0) return;

		isProcessingQueue = true;
		console.log(`🚦 Processing analysis queue: ${analysisQueue.length} items`);

		while (analysisQueue.length > 0) {
			const element = analysisQueue.shift();

			try {
				console.log(`🔍 Analyzing ${element.name} (${element.type})`);
				await aiActions.analyzeNow(element, canvasStateWithMethodology);
				console.log(`✅ Analysis completed for: ${element.name}`);

				// Wait between requests to avoid rate limiting
				if (analysisQueue.length > 0) {
					console.log('⏱️ Waiting 3 seconds before next analysis to avoid rate limits...');
					await new Promise((resolve) => setTimeout(resolve, 3000));
				}
			} catch (error) {
				console.error(`❌ Analysis failed for ${element.name}:`, error);
				if (error.message.includes('429') || error.message.includes('rate limit')) {
					console.log('🚨 Rate limit detected, pausing analysis queue for 60 seconds...');
					showUserNotification(
						'⏸️ AI analysis paused due to rate limits. Resuming in 60 seconds...'
					);
					await new Promise((resolve) => setTimeout(resolve, 60000));
				}
				// Remove from analyzed set if failed, so it can be retried
				analyzedComponents.delete(element.id);
			}
		}

		isProcessingQueue = false;
		console.log('✅ Analysis queue processing completed');
	}

	// Function to queue element for analysis instead of immediate processing
	function queueElementForAnalysis(element) {
		if (analyzedComponents.has(element.id)) return;

		analyzedComponents.add(element.id);
		analysisQueue.push(element);
		console.log(`📝 Queued ${element.name} for AI analysis (queue size: ${analysisQueue.length})`);

		// Start processing if not already running
		processAnalysisQueue();
	}

	// Initialize canvas when both container and model data are available
	$: if (canvasContainer && modelData && !loading) {
		console.log('🎨 Canvas container and model data ready, initializing canvas...');
		initializeCanvas();
	}

	// Re-render canvas when canvas data changes (for imported data)
	$: if (
		g &&
		$canvasData &&
		($canvasData.elements.length > 0 || $canvasData.connections.length > 0)
	) {
		console.log('🔄 Canvas data changed, re-rendering...', $canvasData);
		console.log('🔄 Elements to render:', $canvasData.elements.length);
		console.log('🔄 Connections to render:', $canvasData.connections.length);
		console.log('🔄 g (SVG group) exists:', !!g);
		renderCanvas();
	}

	// Lifecycle functions
	onMount(async () => {
		// Extract URL parameters
		orgName = $page.params.org;
		modelId = $page.params.model_id;

		try {
			// Load current user first
			await loadCurrentUser();

			// Load threat model data
			await loadThreatModel();

			// Load past AI analysis history
			await loadAnalysisHistory();

			// Load last AI analysis if it exists
			if (modelData?.ai_analysis) {
				aiAnalysisResult = modelData.ai_analysis;
				console.log('📊 Loaded existing AI analysis from database');
			}

			// Note: Canvas initialization is now handled by reactive statement
			// when both canvasContainer and modelData are available

			// Initialize collaboration
			await initializeCollaborationFeatures();
			console.log('✅ Final collaboration state:', { collaborationInitialized, currentUser });

			// Initialize WebSocket for async threat analysis
			if (currentUser && currentUser.sub) {
				initWebSocket();
			}
		} catch (error) {
			console.error('❌ Failed to initialize component:', error);
			showUserNotification('❌ Failed to load threat model');
		}
	});

	onDestroy(() => {
		console.log('🧹 Component unmounting, cleaning up...');
		disconnectCollaboration();
		cleanupWebSocket();

		// Clean up polling
		if (pollIntervalId) {
			clearInterval(pollIntervalId);
			pollIntervalId = null;
		}

		// Clean up panel resize listeners
		if (isResizingAIPanel) {
			stopAIPanelResize();
		}
	});

	// Initialize collaboration features
	async function initializeCollaborationFeatures() {
		if (!modelId) return;

		try {
			console.log('🤝 Initializing collaboration for model:', modelId);

			// Get user info from URL parameters or Auth0 user info
			const urlParams = new URLSearchParams(window.location.search);
			const urlUser = urlParams.get('user');
			const isJoining = urlParams.get('join') === 'true';

			// Generate a unique session ID for this browser session
			let sessionId = sessionStorage.getItem('collaboration-session-id');
			if (!sessionId) {
				sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
				sessionStorage.setItem('collaboration-session-id', sessionId);
			}

			// Try to get user info from Auth0 if available, otherwise use URL parameter
			let userName = urlUser || 'Anonymous User';
			let userEmail = '';

			// Use currentUser if already loaded from Auth0, otherwise try to load from storage
			if (currentUser) {
				userName = currentUser.name;
				userEmail = currentUser.email || '';
				console.log('🔐 Using authenticated user:', userName);
			} else {
				// Check if Auth0 user info is available in browser storage or context
				try {
					const auth0User = localStorage.getItem('auth0User');
					if (auth0User) {
						const user = JSON.parse(auth0User);
						userName = user.name || user.email || userName;
						userEmail = user.email || '';
					}
				} catch (e) {
					console.log('No Auth0 user found, using URL parameter or anonymous');
				}

				// If URL user is provided, append session info to make it unique
				if (urlUser && !userEmail) {
					userName = `${urlUser} (Browser ${sessionId.slice(-4)})`;
				}
			}

			// Generate unique user ID combining session and time
			const uniqueUserId = currentUser?.sub
				? `auth-${currentUser.sub}`
				: `user-${sessionId}-${Date.now()}`;

			// Initialize or enhance current user with collaboration information
			if (!currentUser) {
				currentUser = {
					sub: 'anonymous',
					name: userName,
					email: userEmail,
					avatar: '',
					color: generateUserColor(userName)
				};
			}

			// Add collaboration-specific data
			const collaborationUser = {
				...currentUser,
				isJoining: isJoining,
				id: uniqueUserId,
				sessionId: sessionId
			};

			console.log('👤 Current user:', currentUser);
			console.log('🤝 Collaboration user:', collaborationUser);

			// Initialize collaboration room
			await initializeCollaboration(modelId, collaborationUser);
			collaborationInitialized = true;

			console.log('✅ Collaboration initialized successfully');
			showUserNotification(`🤝 ${collaborationUser.name} joined the collaboration`);
		} catch (error) {
			console.error('❌ Failed to initialize collaboration:', error);
			showUserNotification('⚠️ Collaboration unavailable - working offline');
		}
	}

	// Generate a consistent color for user identification based on name
	function generateUserColor(userName = '') {
		const colors = [
			'#FF6B6B',
			'#4ECDC4',
			'#45B7D1',
			'#96CEB4',
			'#FFEAA7',
			'#DDA0DD',
			'#98D8C8',
			'#F7DC6F',
			'#BB8FCE',
			'#85C1E9'
		];

		// Generate a hash from the username for consistent colors
		let hash = 0;
		for (let i = 0; i < userName.length; i++) {
			const char = userName.charCodeAt(i);
			hash = (hash << 5) - hash + char;
			hash = hash & hash; // Convert to 32bit integer
		}

		return colors[Math.abs(hash) % colors.length];
	}

	// Enhanced element operations with collaboration sync
	function addElementWithSync(type, x, y) {
		const newElement = {
			id: `${type}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
			type: type,
			name: `${ELEMENT_TYPES[type].label} ${Date.now().toString().slice(-4)}`,
			position: { x, y },
			size: { ...ELEMENT_TYPES[type].defaultSize },
			properties: {
				description: '',
				outOfScope: false,
				reasonOutOfScope: ''
			},
			threats: []
		};

		// Add to local state
		canvasData.update((data) => {
			data.elements.push(newElement);
			return data;
		});

		// Sync with collaboration
		if ($collaborationConnected) {
			updateLiveElement(newElement);
			updatePresence({ selection: newElement.id });
		}

		renderCanvas();
		selectedElement.set(newElement);

		console.log(`✅ Added ${type} element with collaboration sync:`, newElement);
		return newElement;
	}

	// Enhanced element update with collaboration sync
	function updateElementWithSync(element) {
		// Update local state
		canvasData.update((data) => {
			const index = data.elements.findIndex((el) => el.id === element.id);
			if (index >= 0) {
				data.elements[index] = element;
			}
			return data;
		});

		// Sync with collaboration
		if ($collaborationConnected) {
			updateLiveElement(element);
		}

		renderCanvas();
	}

	// Risk Assessment Matrix
	const RISK_MATRIX = {
		likelihood: {
			'Very Low': { value: 1, description: 'Extremely unlikely to occur' },
			Low: { value: 2, description: 'Unlikely to occur' },
			Medium: { value: 3, description: 'Possible to occur' },
			High: { value: 4, description: 'Likely to occur' },
			'Very High': { value: 5, description: 'Almost certain to occur' }
		},
		impact: {
			'Very Low': { value: 1, description: 'Minimal impact on operations' },
			Low: { value: 2, description: 'Minor impact on operations' },
			Medium: { value: 3, description: 'Moderate impact on operations' },
			High: { value: 4, description: 'Significant impact on operations' },
			'Very High': { value: 5, description: 'Severe impact on operations' }
		}
	};

	// Risk Level Calculation
	function calculateRiskLevel(likelihood, impact) {
		const score = likelihood * impact;
		if (score <= 5) return { level: 'Low', color: '#22C55E', score };
		if (score <= 12) return { level: 'Medium', color: '#EAB308', score };
		if (score <= 20) return { level: 'High', color: '#F97316', score };
		return { level: 'Critical', color: '#EF4444', score };
	}

	// Get highest risk level for an element
	function getElementHighestRisk(element) {
		if (!element.threats || element.threats.length === 0) {
			return { level: 'None', color: '#6B7280', score: 0 };
		}

		let highestRisk = { level: 'Low', color: '#22C55E', score: 0 };

		element.threats.forEach((threatId) => {
			const threat = $canvasData.threats.find((t) => t.id === threatId);
			if (threat && threat.riskScore > highestRisk.score) {
				highestRisk = {
					level: threat.riskLevel || 'Medium',
					color: threat.riskColor || '#EAB308',
					score: threat.riskScore || 9
				};
			}
		});

		return highestRisk;
	}

	// Threat Methodologies and their threat types
	const THREAT_METHODOLOGIES = {
		STRIDE: {
			name: 'STRIDE',
			description: 'Microsoft STRIDE threat modeling methodology',
			elementThreats: {
				rectangle: [
					'Spoofing',
					'Tampering',
					'Repudiation',
					'Information Disclosure',
					'Denial of Service',
					'Elevation of Privilege'
				],
				circle: [
					'Spoofing',
					'Tampering',
					'Repudiation',
					'Information Disclosure',
					'Denial of Service',
					'Elevation of Privilege'
				],
				square: [
					'Spoofing',
					'Tampering',
					'Repudiation',
					'Information Disclosure',
					'Denial of Service',
					'Elevation of Privilege'
				],
				triangle: [
					'Spoofing',
					'Tampering',
					'Repudiation',
					'Information Disclosure',
					'Denial of Service',
					'Elevation of Privilege'
				],
				diamond: [
					'Spoofing',
					'Tampering',
					'Repudiation',
					'Information Disclosure',
					'Denial of Service',
					'Elevation of Privilege'
				],
				frame: [
					'Spoofing',
					'Tampering',
					'Repudiation',
					'Information Disclosure',
					'Denial of Service',
					'Elevation of Privilege'
				],
				dataflow: [
					'Spoofing',
					'Tampering',
					'Repudiation',
					'Information Disclosure',
					'Denial of Service',
					'Elevation of Privilege'
				]
			},
			threats: {
				Spoofing: {
					color: '#EF4444',
					description: 'Impersonating something or someone else',
					defaultLikelihood: 3,
					defaultImpact: 4
				},
				Tampering: {
					color: '#F97316',
					description: 'Modifying data or code',
					defaultLikelihood: 3,
					defaultImpact: 4
				},
				Repudiation: {
					color: '#EAB308',
					description: 'Claiming to have not performed an action',
					defaultLikelihood: 2,
					defaultImpact: 3
				},
				'Information Disclosure': {
					color: '#22C55E',
					description: 'Exposing information to unauthorized individuals',
					defaultLikelihood: 4,
					defaultImpact: 5
				},
				'Denial of Service': {
					color: '#3B82F6',
					description: 'Denying service to valid users',
					defaultLikelihood: 3,
					defaultImpact: 4
				},
				'Elevation of Privilege': {
					color: '#8B5CF6',
					description: 'Gaining capabilities without proper authorization',
					defaultLikelihood: 2,
					defaultImpact: 5
				}
			}
		},
		LINDDUN: {
			name: 'LINDDUN',
			description: 'LINDDUN privacy threat modeling methodology',
			elementThreats: {
				rectangle: [
					'Linkability',
					'Identifiability',
					'Non-repudiation',
					'Detectability',
					'Disclosure of Information',
					'Unawareness',
					'Non-compliance'
				],
				circle: [
					'Linkability',
					'Identifiability',
					'Non-repudiation',
					'Detectability',
					'Disclosure of Information',
					'Unawareness',
					'Non-compliance'
				],
				square: [
					'Linkability',
					'Identifiability',
					'Non-repudiation',
					'Detectability',
					'Disclosure of Information',
					'Unawareness',
					'Non-compliance'
				],
				triangle: [
					'Linkability',
					'Identifiability',
					'Non-repudiation',
					'Detectability',
					'Disclosure of Information',
					'Unawareness',
					'Non-compliance'
				],
				diamond: [
					'Linkability',
					'Identifiability',
					'Non-repudiation',
					'Detectability',
					'Disclosure of Information',
					'Unawareness',
					'Non-compliance'
				],
				frame: [
					'Linkability',
					'Identifiability',
					'Non-repudiation',
					'Detectability',
					'Disclosure of Information',
					'Unawareness',
					'Non-compliance'
				],
				dataflow: [
					'Linkability',
					'Identifiability',
					'Non-repudiation',
					'Detectability',
					'Disclosure of Information',
					'Unawareness',
					'Non-compliance'
				]
			},
			threats: {
				Linkability: {
					color: '#EF4444',
					description: 'Ability to link two or more data items',
					defaultLikelihood: 4,
					defaultImpact: 3
				},
				Identifiability: {
					color: '#F97316',
					description: 'Ability to identify a person from data',
					defaultLikelihood: 4,
					defaultImpact: 4
				},
				'Non-repudiation': {
					color: '#EAB308',
					description: 'Inability to deny an action',
					defaultLikelihood: 2,
					defaultImpact: 3
				},
				Detectability: {
					color: '#22C55E',
					description: "Ability to detect someone's presence or actions",
					defaultLikelihood: 3,
					defaultImpact: 3
				},
				'Disclosure of Information': {
					color: '#3B82F6',
					description: 'Exposing personal information',
					defaultLikelihood: 4,
					defaultImpact: 5
				},
				Unawareness: {
					color: '#8B5CF6',
					description: 'Lack of awareness about data processing',
					defaultLikelihood: 5,
					defaultImpact: 2
				},
				'Non-compliance': {
					color: '#EC4899',
					description: 'Violation of privacy regulations',
					defaultLikelihood: 3,
					defaultImpact: 5
				}
			}
		},
		CIA: {
			name: 'CIA Triad',
			description: 'Confidentiality, Integrity, Availability security model',
			elementThreats: {
				process: ['Confidentiality Breach', 'Integrity Violation', 'Availability Disruption'],
				datastore: ['Confidentiality Breach', 'Integrity Violation', 'Availability Disruption'],
				actor: ['Confidentiality Breach', 'Integrity Violation', 'Availability Disruption'],
				diamond: ['Confidentiality Breach', 'Integrity Violation', 'Availability Disruption'],
				database: ['Confidentiality Breach', 'Integrity Violation', 'Availability Disruption'],
				cloud_service: ['Confidentiality Breach', 'Integrity Violation', 'Availability Disruption'],
				trust_boundary: [
					'Confidentiality Breach',
					'Integrity Violation',
					'Availability Disruption'
				],
				dataflow: ['Confidentiality Breach', 'Integrity Violation', 'Availability Disruption']
			},
			threats: {
				'Confidentiality Breach': {
					color: '#EF4444',
					description: 'Unauthorized access to sensitive information',
					defaultLikelihood: 3,
					defaultImpact: 5
				},
				'Integrity Violation': {
					color: '#F97316',
					description: 'Unauthorized modification of data',
					defaultLikelihood: 3,
					defaultImpact: 4
				},
				'Availability Disruption': {
					color: '#3B82F6',
					description: 'Prevention of access to resources',
					defaultLikelihood: 4,
					defaultImpact: 4
				}
			}
		}
	};

	// Canvas event handlers
	function onStencilDragStart(event, elementType) {
		console.log('🖱️ Drag start for element type:', elementType);
		event.dataTransfer.setData('text/plain', elementType);
		event.dataTransfer.effectAllowed = 'copy';
	}

	function onDataflowDragStart(event) {
		console.log('🖱️ Drag start for dataflow');
		event.dataTransfer.setData('text/plain', 'dataflow');
		event.dataTransfer.effectAllowed = 'copy';
	}

	function onCanvasDrop(event) {
		event.preventDefault();
		console.log('🎯 Canvas drop event');

		const elementType = event.dataTransfer.getData('text/plain');
		if (!elementType || !ELEMENT_TYPES[elementType]) {
			console.log('❌ Invalid element type:', elementType);
			return;
		}

		const rect = event.currentTarget.getBoundingClientRect();
		const x = event.clientX - rect.left;
		const y = event.clientY - rect.top;

		console.log(`🎨 Creating ${elementType} at position:`, { x, y });

		if (elementType === 'dataflow') {
			// Handle dataflow creation differently
			console.log('🔗 Dataflow creation not implemented yet');
			return;
		}

		// Create new element
		const newElement = {
			id: `${elementType}-${Date.now()}`,
			type: elementType,
			name: getNextComponentName(elementType),
			position: { x, y },
			size: ELEMENT_TYPES[elementType].defaultSize || { width: 80, height: 60 },
			properties: {
				description: '',
				outOfScope: false,
				reasonOutOfScope: ''
			},
			threats: []
		};

		// Add to canvas data
		canvasData.update((data) => {
			data.elements.push(newElement);
			return data;
		});

		renderCanvas();
		autoSave();
	}

	function onCanvasDragOver(event) {
		event.preventDefault();
		event.dataTransfer.dropEffect = 'copy';
	}

	function onCanvasDragLeave(event) {
		event.preventDefault();
	}

	onMount(async () => {
		orgName = $page.params.org;
		modelId = $page.params.model_id;
		console.log(`🎨 Opening threat model canvas: ${modelId} for ${orgName}`);

		await loadThreatModel();
		initializeCanvas();
	});

	onDestroy(() => {
		// Cleanup D3 event listeners
		if (svg) {
			svg.selectAll('*').remove();
		}
	});

	async function loadThreatModel() {
		try {
			loading = true;
			error = null;

			console.log(`📄 Loading threat model: ${modelId}`);

			// For now, use the simplified API to get model info
			const response = await fetch(`${API_BASE_URL}/api/threat-modeling/models/${modelId}`, {
				headers: { 'Content-Type': 'application/json' }
			});

			if (!response.ok) {
				if (response.status === 404) {
					throw new Error('Threat model not found');
				}
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}

			modelData = await response.json();
			console.log('✅ Threat model loaded:', modelData);
			console.log('🔍 Raw canvas_data from API:', modelData.canvas_data);
			console.log('🔍 Canvas data type:', typeof modelData.canvas_data);
			console.log(
				'🔍 Canvas data keys:',
				modelData.canvas_data ? Object.keys(modelData.canvas_data) : 'null'
			);

			// Set methodology based on model's actual methodology
			if (modelData.methodology && THREAT_METHODOLOGIES[modelData.methodology]) {
				currentMethodology = modelData.methodology;
				console.log(`🎯 Loaded methodology from model: ${currentMethodology}`);
			} else if (
				modelData.canvas_data?.metadata?.methodology &&
				THREAT_METHODOLOGIES[modelData.canvas_data.metadata.methodology]
			) {
				currentMethodology = modelData.canvas_data.metadata.methodology;
				console.log(`🎯 Loaded methodology from canvas metadata: ${currentMethodology}`);
			} else {
				// If no methodology is specified, default to STRIDE but log a warning
				console.warn(`⚠️ No methodology specified for model ${modelId}, defaulting to STRIDE`);
				currentMethodology = 'STRIDE';
			}

			console.log(`🎯 Using ${currentMethodology} methodology for threat model: ${modelData.name}`);

			// Load canvas data if it exists
			if (modelData.canvas_data && Object.keys(modelData.canvas_data).length > 0) {
				console.log('🎨 Found canvas data, processing...', modelData.canvas_data);
				console.log('🎨 Elements found:', modelData.canvas_data.elements?.length || 0);
				console.log('🎨 Connections found:', modelData.canvas_data.connections?.length || 0);
				console.log('🎨 Threats found:', modelData.canvas_data.threats?.length || 0);

				const canvasDataToLoad = {
					elements: (modelData.canvas_data.elements || []).map((element) => ({
						...element,
						// Ensure size property exists for existing elements
						size: element.size || {
							width: ELEMENT_TYPES[element.type]?.defaultSize?.width || 80,
							height: ELEMENT_TYPES[element.type]?.defaultSize?.height || 80
						}
					})),
					connections: modelData.canvas_data.connections || [],
					threats: modelData.canvas_data.threats || [],
					metadata: {
						zoom: 1.0,
						panX: 0,
						panY: 0,
						methodology: currentMethodology,
						...(modelData.canvas_data.metadata || {})
					}
				};
				canvasData.set(canvasDataToLoad);

				// Initialize component counters based on loaded data
				initializeComponentCounters();

				console.log(`🎨 Loaded ${canvasDataToLoad.elements?.length || 0} elements from canvas`);
				console.log('🎨 Canvas data set:', canvasDataToLoad);
				console.log('🎨 Current canvasData store value:', $canvasData);
			} else {
				console.log('❌ No canvas data found or canvas data is empty');
				console.log('❌ modelData.canvas_data:', modelData.canvas_data);
				console.log(
					'❌ Object.keys(modelData.canvas_data):',
					modelData.canvas_data ? Object.keys(modelData.canvas_data) : 'null'
				);

				// Initialize counters for empty canvas
				initializeComponentCounters();
			}
		} catch (err) {
			console.error('Failed to load threat model:', err);
			error = err.message;
		} finally {
			loading = false;
		}
	}

	function initializeCanvas() {
		if (!canvasContainer) return;

		console.log('🎨 Initializing D3.js canvas...');

		try {
			// Clear any existing SVG
			d3.select(canvasContainer).selectAll('*').remove();

			// Create SVG
			svg = d3
				.select(canvasContainer)
				.append('svg')
				.attr('width', '100%')
				.attr('height', '100%')
				.attr('viewBox', `0 0 ${canvasWidth} ${canvasHeight}`)
				.style('border', '1px solid #e5e7eb')
				.style('background-color', '#fafafa');

			// Add grid pattern
			const defs = svg.append('defs');
			const pattern = defs
				.append('pattern')
				.attr('id', 'grid')
				.attr('width', 20)
				.attr('height', 20)
				.attr('patternUnits', 'userSpaceOnUse');

			pattern
				.append('path')
				.attr('d', 'M 20 0 L 0 0 0 20')
				.attr('fill', 'none')
				.attr('stroke', '#e5e7eb')
				.attr('stroke-width', 0.5);

			// Add grid background
			svg.append('rect').attr('width', '100%').attr('height', '100%').attr('fill', 'url(#grid)');

			// Create main group for zoom/pan
			g = svg.append('g').attr('class', 'main-group');
			console.log('🎨 Main group (g) created:', g.node());

			// Add zoom behavior
			const zoom = d3.zoom().scaleExtent([0.1, 3]).on('zoom', handleZoom);

			svg.call(zoom);

			// Add click handler for canvas
			svg.on('click', handleCanvasClick);

			// Note: Drag and drop handlers are now handled via Svelte template events (on:drop, on:dragover, on:dragleave)
			// to avoid duplicate event handling that was causing double element creation

			console.log('✅ Canvas initialized successfully');

			// Render existing elements
			renderCanvas();
		} catch (error) {
			console.error('❌ Error initializing canvas:', error);
		}
	}

	function handleZoom(event) {
		const { transform } = event;
		g.attr('transform', transform);

		// Update metadata
		canvasData.update((data) => {
			data.metadata.zoom = transform.k;
			data.metadata.panX = transform.x;
			data.metadata.panY = transform.y;
			return data;
		});
	}

	function handleCanvasClick(event) {
		// Only handle clicks on the canvas background
		if (event.target === svg.node() || event.target.tagName === 'rect') {
			if (isConnecting) {
				// Cancel connection drawing
				cancelConnection();
			} else {
				selectedElement.set(null);
				selectedConnection.set(null);
			}
		}
	}

	function addElement(type, x, y) {
		console.log(`🎯 addElement called with type: ${type}, position: (${x}, ${y})`);

		const elementType = ELEMENT_TYPES[type];
		if (!elementType) {
			console.error(`❌ Unknown element type: ${type}`);
			return;
		}

		console.log(`📦 Element type found:`, elementType);

		const newElement = {
			id: `${type}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
			type,
			name: `${elementType.label} ${$canvasData.elements.filter((e) => e.type === type).length + 1}`,
			position: { x, y },
			size: {
				width: elementType.defaultSize.width,
				height: elementType.defaultSize.height
			},
			properties: {
				description: '',
				outOfScope: false,
				reasonOutOfScope: '',
				...(type === 'dataflow' && {
					protocol: '',
					encrypted: false,
					publicNetwork: false,
					bidirectional: false
				})
			},
			threats: []
		};

		console.log(`🔧 Created new element:`, newElement);

		canvasData.update((data) => {
			console.log(`📝 Current canvas data before update:`, data);
			data.elements.push(newElement);
			console.log(`📝 Canvas data after adding element:`, data);
			return data;
		});

		console.log(`🎨 Calling renderCanvas...`);
		renderCanvas();
		selectedElement.set(newElement);

		// 🚀 TRIGGER AI THREAT ANALYSIS with current methodology
		console.log(`🤖 Triggering AI analysis for ${type} using ${currentMethodology} methodology`);
		aiThreatService.analyzeComponent(
			{
				type: type,
				name: newElement.name,
				description: newElement.properties.description || `A ${elementType.label} component`,
				technology: 'Unknown',
				dataTypes: 'Unknown'
			},
			{
				methodology: currentMethodology,
				components: $canvasData.elements,
				connections: $canvasData.connections
			}
		);

		console.log(`✅ Added ${type} element with AI analysis:`, newElement);
		showUserNotification(`✅ Added ${elementType.label} - AI analyzing threats...`);
	}

	// � UPDATE CONNECTIONS IN REAL-TIME when elements move
	function updateConnectionsForElement(elementId) {
		const data = $canvasData;

		// Find all connections that involve this element
		const relatedConnections = data.connections.filter(
			(conn) => conn.source === elementId || conn.target === elementId
		);

		// Update each connection line position
		relatedConnections.forEach((connection) => {
			const sourceElement = data.elements.find((el) => el.id === connection.source);
			const targetElement = data.elements.find((el) => el.id === connection.target);

			if (sourceElement && targetElement) {
				// Calculate proper connection points at borders
				const connectionPoints = calculateConnectionPoints(sourceElement, targetElement);

				// Update connection line position
				g.select(`.connection-${connection.id}.connection-line`)
					.attr('x1', connectionPoints.source.x)
					.attr('y1', connectionPoints.source.y)
					.attr('x2', connectionPoints.target.x)
					.attr('y2', connectionPoints.target.y);

				// Update connection label position
				const midX = (connectionPoints.source.x + connectionPoints.target.x) / 2;
				const midY = (connectionPoints.source.y + connectionPoints.target.y) / 2;

				g.select(`.connection-${connection.id}.connection-label`)
					.attr('x', midX)
					.attr('y', midY - 5);

				// Update threat indicators if they exist
				g.select(`.connection-${connection.id}.connection-threat`)
					.attr('cx', midX)
					.attr('cy', midY + 15);

				g.select(`.connection-${connection.id}.connection-threat-text`)
					.attr('x', midX)
					.attr('y', midY + 19);
			}
		});
	}

	// �🔗 SIMPLE CONNECTION SYSTEM (WORKING VERSION)
	function startConnection(elementId) {
		connectionStart = elementId;
		isConnecting = true;
		console.log('🔗 STEP 1: Started connection from:', elementId);
		console.log('✅ Click the green 🔗 button on another element to complete connection!');
		renderCanvas(); // Re-render to show visual feedback
	}

	function completeConnection(targetId) {
		if (isConnecting && connectionStart && connectionStart !== targetId) {
			canvasData.update((data) => {
				componentCounters.connection++;
				const newConnection = {
					id: `connection_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
					source: connectionStart,
					target: targetId,
					type: 'connection',
					name: `Connection ${componentCounters.connection}`,
					threats: []
				};

				data.connections.push(newConnection);
				console.log('✅ STEP 2: Connection created!', newConnection);
				return data;
			});

			// Reset connection state
			isConnecting = false;
			connectionStart = null;
			autoSave();
			renderCanvas();
		} else {
			console.log('❌ Cannot connect to same element or no connection started');
		}
	}

	function cancelConnection() {
		isConnecting = false;
		connectionStart = null;
		console.log('❌ Connection cancelled');
		renderCanvas();
	}

	function handleStencilDragStart(event, elementType) {
		console.log('🚀 Drag started for element type:', elementType);
		event.dataTransfer.setData('text/plain', elementType);
		event.dataTransfer.effectAllowed = 'copy';
		console.log('📋 Data transfer set with:', elementType);
	}

	// 🚀 ThreatDragon-style dataflow drag start
	function handleDataflowDragStart(event) {
		event.dataTransfer.setData('text/plain', 'dataflow-mode');
		event.dataTransfer.effectAllowed = 'copy';
		console.log('🔗 Started dragging dataflow line - drop on canvas to enter connection mode!');
	}

	function handleCanvasDrop(event) {
		event.preventDefault();
		const dragData = event.dataTransfer.getData('text/plain');

		console.log('🎯 Canvas drop event received:', dragData);

		if (dragData === 'dataflow-mode') {
			// User dropped the dataflow line - enter connection mode
			console.log('🔗 Entering connection mode! Click elements to connect them.');
			return;
		}

		if (ELEMENT_TYPES[dragData]) {
			console.log('📦 Valid element type dropped:', dragData);

			// Calculate proper coordinates from mouse position
			const canvasRect = canvasContainer.getBoundingClientRect();
			const mouseX = event.clientX - canvasRect.left;
			const mouseY = event.clientY - canvasRect.top;

			// Convert to SVG coordinates accounting for zoom/pan
			const svgElement = svg.node();
			const point = svgElement.createSVGPoint();
			point.x = mouseX;
			point.y = mouseY;

			// Transform to canvas coordinate space
			const transform = g.node().getScreenCTM().inverse();
			const svgPoint = point.matrixTransform(transform);

			addElement(dragData, svgPoint.x, svgPoint.y);
		} else {
			console.warn('❌ Unknown drag data:', dragData);
		}

		// Remove visual feedback
		canvasContainer.style.backgroundColor = '';
	}

	function handleCanvasDragOver(event) {
		event.preventDefault();
		event.dataTransfer.dropEffect = 'copy';

		// Add visual feedback for drag over (can't read data during dragover)
		canvasContainer.style.backgroundColor = '#f0f9ff';
	}

	function handleCanvasDragLeave(event) {
		// Remove visual feedback
		canvasContainer.style.backgroundColor = '';
	}

	function openThreatDialog(element) {
		console.log('🔵 openThreatDialog called with element:', element);
		console.log('🔵 Element type:', element?.type, 'Element name:', element?.name);

		// Validate inputs (same pattern as editThreat)
		if (!element) {
			console.error('❌ No element provided to openThreatDialog');
			showUserNotification('⚠️ Please select an element first');
			return;
		}

		// Direct store setting (same pattern as editThreat - NO setTimeout, NO async)
		currentElementForThreat.set(element);
		showThreatDialog.set(true);

		console.log(
			'🔵 Final state - showThreatDialog:',
			$showThreatDialog,
			'currentElementForThreat:',
			$currentElementForThreat
		);
		showUserNotification(`🛡️ Ready to add threats to ${element.name || element.type}`);
	}

	function addThreat(threatData) {
		const element = $currentElementForThreat;
		if (!element) return;

		// Get default risk values from methodology
		const threatInfo = THREAT_METHODOLOGIES[currentMethodology]?.threats[threatData.type] || {};
		const defaultLikelihood = threatInfo.defaultLikelihood || 3;
		const defaultImpact = threatInfo.defaultImpact || 3;

		// Calculate initial risk level
		const likelihood = threatData.likelihood || defaultLikelihood;
		const impact = threatData.impact || defaultImpact;
		const riskLevel = calculateRiskLevel(likelihood, impact);

		const newThreat = {
			id: `threat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
			elementId: element.id,
			title: threatData.title,
			type: threatData.type,
			status: threatData.status || 'Open',
			severity: threatData.severity || 'Medium',

			// Risk Assessment Fields
			likelihood: likelihood,
			impact: impact,
			riskLevel: riskLevel.level,
			riskScore: riskLevel.score,
			riskColor: riskLevel.color,

			description: threatData.description || '',
			mitigation: threatData.mitigation || '',

			// Additional tracking
			createdAt: new Date().toISOString(),
			updatedAt: new Date().toISOString()
		};

		canvasData.update((data) => {
			// Add threat to threats array
			data.threats.push(newThreat);

			// Add threat to element (check both elements and connections)
			const elementIndex = data.elements.findIndex((el) => el.id === element.id);
			if (elementIndex !== -1) {
				if (!data.elements[elementIndex].threats) {
					data.elements[elementIndex].threats = [];
				}
				data.elements[elementIndex].threats.push(newThreat.id);
			} else {
				// Check if it's a connection
				const connectionIndex = data.connections.findIndex((conn) => conn.id === element.id);
				if (connectionIndex !== -1) {
					if (!data.connections[connectionIndex].threats) {
						data.connections[connectionIndex].threats = [];
					}
					data.connections[connectionIndex].threats.push(newThreat.id);
				}
			}

			return data;
		});

		showThreatDialog.set(false);
		currentElementForThreat.set(null);

		// Force immediate visual updates
		renderCanvas(); // 🚀 IMPORTANT: Re-render to show RED border!
		autoSave();

		// Force properties panel refresh by re-selecting
		const currentElement = $selectedElement;
		const currentConnection = $selectedConnection;
		if (currentElement) {
			selectedElement.set(null);
			setTimeout(() => selectedElement.set(currentElement), 10);
		}
		if (currentConnection) {
			selectedConnection.set(null);
			setTimeout(() => selectedConnection.set(currentConnection), 10);
		}

		showUserNotification('✅ Threat added successfully!');
	}

	function editThreat(threat, element) {
		// Validate inputs
		if (!threat || !element) {
			console.error('❌ Missing threat or element data');
			alert('Error: Missing threat or element data');
			return;
		}

		// Pre-populate the form with existing data
		editingThreat.set(threat);
		currentElementForThreat.set(element);
		showEditThreatDialog.set(true);
	}

	function updateThreat(threatData) {
		const threat = $editingThreat;
		if (!threat) {
			console.error('❌ No threat being edited');
			return;
		}

		// Recalculate risk level based on new likelihood and impact
		const likelihood = threatData.likelihood || threat.likelihood || 3;
		const impact = threatData.impact || threat.impact || 3;
		const riskLevel = calculateRiskLevel(likelihood, impact);

		canvasData.update((data) => {
			// Find and update the threat in the threats array
			const threatIndex = data.threats.findIndex((t) => t.id === threat.id);
			if (threatIndex !== -1) {
				data.threats[threatIndex] = {
					...data.threats[threatIndex],
					title: threatData.title,
					type: threatData.type,
					status: threatData.status,
					severity: threatData.severity,

					// Update risk assessment
					likelihood: likelihood,
					impact: impact,
					riskLevel: riskLevel.level,
					riskScore: riskLevel.score,
					riskColor: riskLevel.color,

					description: threatData.description,
					mitigation: threatData.mitigation,
					updatedAt: new Date().toISOString()
				};
				console.log('✅ Threat updated with new risk score:', riskLevel.score);
			} else {
				console.error('❌ Threat not found in data store');
			}
			return data;
		});

		// Close dialog and clean up
		showEditThreatDialog.set(false);
		editingThreat.set(null);
		currentElementForThreat.set(null);

		// Force immediate updates
		renderCanvas();
		autoSave();

		// Force properties panel refresh by re-selecting
		const currentElement = $selectedElement;
		const currentConnection = $selectedConnection;
		if (currentElement) {
			selectedElement.set(null);
			setTimeout(() => selectedElement.set(currentElement), 10);
		}
		if (currentConnection) {
			selectedConnection.set(null);
			setTimeout(() => selectedConnection.set(currentConnection), 10);
		}

		console.log('✅ Threat update completed with UI refresh');
		showUserNotification('✅ Threat updated successfully!');
	}

	function deleteThreat(threatId, element) {
		if (!confirm('Are you sure you want to delete this threat?')) {
			return;
		}

		canvasData.update((data) => {
			// Remove threat from threats array
			data.threats = data.threats.filter((t) => t.id !== threatId);

			// Remove threat from element (check both elements and connections)
			data.elements.forEach((el) => {
				if (el.threats) {
					el.threats = el.threats.filter((id) => id !== threatId);
				}
			});

			data.connections.forEach((conn) => {
				if (conn.threats) {
					conn.threats = conn.threats.filter((id) => id !== threatId);
				}
			});

			return data;
		});

		renderCanvas();
		autoSave();

		// Force properties panel refresh by re-selecting
		const currentElement = $selectedElement;
		const currentConnection = $selectedConnection;
		if (currentElement) {
			selectedElement.set(null);
			setTimeout(() => selectedElement.set(currentElement), 10);
		}
		if (currentConnection) {
			selectedConnection.set(null);
			setTimeout(() => selectedConnection.set(currentConnection), 10);
		}

		console.log('✅ Deleted threat successfully');
		showUserNotification('✅ Threat deleted successfully!');
	}

	// Function to open the threat dialog for a selected element
	function openElementThreatDialog(element) {
		if (!element) {
			showUserNotification('⚠️ Please select an element first');
			return;
		}

		// Clear any previous state
		showThreatDialog.set(false);
		currentElementForThreat.set(null);

		// Small delay to ensure state is cleared
		setTimeout(() => {
			// Set the current element for threat creation
			currentElementForThreat.set(element);

			// Show the threat dialog
			showThreatDialog.set(true);

			showUserNotification(`🛡️ Ready to add threats to ${element.name || element.type}`);
		}, 10);
	}

	// 🎨 COLLABORATIVE THREAT DISPLAY HELPERS
	// Helper functions for displaying collaborative threat analysis results

	function getCategoryIcon(category) {
		const iconMap = {
			// STRIDE methodology icons
			Spoofing: '👤',
			spoofing: '👤',
			Tampering: '⚠️',
			tampering: '⚠️',
			Repudiation: '📝',
			repudiation: '📝',
			'Information Disclosure': '🔍',
			information_disclosure: '🔍',
			'Denial of Service': '🚫',
			denial_of_service: '🚫',
			'Elevation of Privilege': '⬆️',
			elevation_of_privilege: '⬆️',

			// CIA methodology icons
			'Confidentiality Breach': '🔒',
			confidentiality_breach: '🔒',
			'Integrity Violation': '⚖️',
			integrity_violation: '⚖️',
			'Availability Disruption': '💔',
			availability_disruption: '💔',

			// LINDDUN methodology icons
			Linkability: '🔗',
			linkability: '🔗',
			Identifiability: '🆔',
			identifiability: '🆔',
			'Non-repudiation': '📋',
			non_repudiation: '📋',
			Detectability: '👁️',
			detectability: '👁️',
			'Disclosure of Information': '💡',
			disclosure_of_information: '💡',
			Unawareness: '❓',
			unawareness: '❓',
			'Non-compliance': '⚖️',
			non_compliance: '⚖️'
		};
		return iconMap[category] || '🛡️';
	}

	function getMethodologyDescription(methodology) {
		const descriptions = {
			STRIDE:
				'Microsoft STRIDE methodology focusing on Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation of Privilege threats',
			CIA: 'CIA Triad methodology focusing on Confidentiality, Integrity, and Availability of information assets',
			LINDDUN:
				'LINDDUN privacy methodology focusing on Linkability, Identifiability, Non-repudiation, Detectability, Disclosure, Unawareness, and Non-compliance threats'
		};
		return descriptions[methodology] || 'Comprehensive threat modeling analysis';
	}

	function getCategoryDescription(category, methodology) {
		const descriptions = {
			// STRIDE descriptions
			Spoofing:
				'Identity spoofing attacks where attackers impersonate legitimate users, services, or systems',
			spoofing:
				'Identity spoofing attacks where attackers impersonate legitimate users, services, or systems',
			Tampering: 'Unauthorized modification of data, code, or system configurations',
			tampering: 'Unauthorized modification of data, code, or system configurations',
			Repudiation: 'Denial of actions performed, lack of audit trails and accountability',
			repudiation: 'Denial of actions performed, lack of audit trails and accountability',
			'Information Disclosure': 'Unauthorized access to sensitive information and data breaches',
			information_disclosure: 'Unauthorized access to sensitive information and data breaches',
			'Denial of Service': 'Attacks that make systems or services unavailable to legitimate users',
			denial_of_service: 'Attacks that make systems or services unavailable to legitimate users',
			'Elevation of Privilege': 'Unauthorized privilege escalation and access control bypasses',
			elevation_of_privilege: 'Unauthorized privilege escalation and access control bypasses',

			// CIA descriptions
			'Confidentiality Breach': 'Unauthorized disclosure of sensitive information and data',
			confidentiality_breach: 'Unauthorized disclosure of sensitive information and data',
			'Integrity Violation': 'Unauthorized modification or corruption of data and systems',
			integrity_violation: 'Unauthorized modification or corruption of data and systems',
			'Availability Disruption': 'Service interruptions and system unavailability issues',
			availability_disruption: 'Service interruptions and system unavailability issues',

			// LINDDUN descriptions
			Linkability: 'Correlation of user activities and data across different contexts',
			linkability: 'Correlation of user activities and data across different contexts',
			Identifiability: 'Re-identification of individuals from anonymized or pseudonymized data',
			identifiability: 'Re-identification of individuals from anonymized or pseudonymized data',
			'Non-repudiation': 'Inability to deny actions or accountability challenges',
			non_repudiation: 'Inability to deny actions or accountability challenges',
			Detectability: 'Detection of user presence, activities, or behavioral patterns',
			detectability: 'Detection of user presence, activities, or behavioral patterns',
			'Disclosure of Information': 'Unintended privacy leakage and information exposure',
			disclosure_of_information: 'Unintended privacy leakage and information exposure',
			Unawareness: 'Lack of transparency about data collection and processing',
			unawareness: 'Lack of transparency about data collection and processing',
			'Non-compliance': 'Violations of privacy regulations and compliance requirements',
			non_compliance: 'Violations of privacy regulations and compliance requirements'
		};
		return descriptions[category] || 'Security or privacy threat analysis';
	}

	function getThreatTypeStyle(threat) {
		if (threat.source === 'user') {
			return 'border-green-200 bg-green-50';
		} else if (threat.source === 'ai') {
			return 'border-blue-200 bg-blue-50';
		} else if (threat.source === 'enhanced') {
			return 'border-purple-200 bg-purple-50';
		}
		return 'border-gray-200 bg-gray-50';
	}

	// Add AI-suggested threat to the user's threat model
	function addAISuggestedThreat(aiThreat, category) {
		console.log('➕ Adding AI-suggested threat:', aiThreat);

		// Find which component this threat relates to
		let targetComponent = null;
		if (aiThreat.component_id) {
			targetComponent = $canvasData.elements.find((el) => el.id === aiThreat.component_id);
		}

		if (!targetComponent && $canvasData.elements.length > 0) {
			// Default to first component if no specific target
			targetComponent = $canvasData.elements[0];
			console.log('⚠️ No specific component found, using first component:', targetComponent.name);
		}

		if (!targetComponent) {
			showUserNotification('❌ No components available to add threat to');
			return;
		}

		// Create threat data from AI suggestion
		const threatData = {
			title: aiThreat.title || aiThreat.what_can_be_spoofed || 'AI Suggested Threat',
			type: category,
			description: aiThreat.possible_scenarios || aiThreat.description || '',
			mitigation: aiThreat.mitigations_recommendations || aiThreat.mitigation || '',
			severity: aiThreat.severity || 'Medium',
			likelihood: aiThreat.likelihood || 'Medium',
			impact: aiThreat.impact || 'Medium'
		};

		// Use existing addThreat function
		currentElementForThreat.set(targetComponent);
		addThreat(threatData);

		showUserNotification(`✅ Added AI-suggested ${category} threat to ${targetComponent.name}`);

		// Mark the threat as added in the AI analysis result
		aiThreat.source = 'user'; // Update source to reflect it's now user-added
	}

	function renderCanvas() {
		if (!g) {
			console.error('❌ renderCanvas called but g is not defined!');
			return;
		}

		try {
			const data = $canvasData;
			console.log('🎨 Rendering canvas with data:', data);
			console.log('🎨 Number of elements to render:', data.elements.length);

			// Clear everything first - BUT ONLY if not during resize/drag
			if (!isDragging && !isResizing) {
				console.log('🧹 Clearing all canvas elements');
				g.selectAll('*').remove();
			} else {
				// During drag/resize, only clear specific elements that need updates
				console.log('🧹 Selective clearing during drag/resize operation');
				if (!isResizing) {
					// Only clear elements during drag, not during resize
					g.selectAll('.element').remove();
				}
				g.selectAll('.connection-line').remove();
				g.selectAll('.connection-label').remove();
				g.selectAll('.connection-threat').remove();
				g.selectAll('.connection-selection').remove();
			}

			// Render elements in proper layering order for frame sub-canvas behavior:
			// 1. Frames (background layer)
			// 2. Connections (middle layer - on top of frames, behind elements)
			// 3. Other elements (foreground layer)
			console.log('📦 Starting to render elements...');

			// First pass: Render all Frame elements (background layer)
			console.log('🖼️ Rendering Frame elements first (background layer)...');
			data.elements
				.filter((d) => d.type === 'frame')
				.forEach((d, index) => {
					renderElement(d, index, data.elements.length);
				});

			// Second pass: Render connections (middle layer - on top of frames)
			console.log('🔗 Rendering connections on top of frames...');
			renderConnections();

			// Third pass: Render all non-Frame elements (foreground layer)
			// This ensures all components placed on frames appear on top
			console.log('📋 Rendering other elements on top...');
			data.elements
				.filter((d) => d.type !== 'frame')
				.forEach((d, index) => {
					renderElement(d, index, data.elements.length);
				});
		} catch (error) {
			console.error('❌ Error rendering canvas:', error);
		}
	}

	// Helper function to render individual elements
	function renderElement(d, index, totalElements) {
		console.log(`🔄 Processing element ${index + 1}/${totalElements}:`, d);

		const elementType = ELEMENT_TYPES[d.type];
		if (!elementType) {
			console.error(`❌ Unknown element type: ${d.type}`);
			return;
		}

		const hasThreats = d.threats && d.threats.length > 0;
		const isSelected = $selectedElement && $selectedElement.id === d.id;

		console.log('🔄 Rendering element:', {
			type: d.type,
			position: d.position,
			size: d.size,
			hasThreats,
			isSelected
		});

		// Create element group
		const group = g
			.append('g')
			.attr('class', 'element')
			.attr('transform', `translate(${d.position.x}, ${d.position.y})`)
			.style('cursor', 'move')
			.datum(d);

		console.log(`✅ Created group for ${d.type} at (${d.position.x}, ${d.position.y})`);

		// Determine border color and style
		const borderColor = hasThreats ? '#DC2626' : elementType.border || '#000000';
		const borderWidth = hasThreats ? 3 : elementType.borderWidth || 2;
		const fillColor = elementType.color || 'transparent';

		// Render shape based on type
		if (d.type === 'rectangle') {
			const halfWidth = d.size.width / 2;
			const halfHeight = d.size.height / 2;
			group
				.append('rect')
				.attr('x', -halfWidth)
				.attr('y', -halfHeight)
				.attr('width', d.size.width)
				.attr('height', d.size.height)
				.attr('fill', fillColor)
				.attr('stroke', borderColor)
				.attr('stroke-width', borderWidth)
				.attr('stroke-dasharray', isSelected ? '8,4' : 'none');
		} else if (d.type === 'circle') {
			const radius = Math.min(d.size.width, d.size.height) / 2;
			group
				.append('circle')
				.attr('r', radius)
				.attr('fill', fillColor)
				.attr('stroke', borderColor)
				.attr('stroke-width', borderWidth)
				.attr('stroke-dasharray', isSelected ? '8,4' : 'none');
		} else if (d.type === 'square') {
			const size = Math.min(d.size.width, d.size.height);
			const halfSize = size / 2;
			group
				.append('rect')
				.attr('x', -halfSize)
				.attr('y', -halfSize)
				.attr('width', size)
				.attr('height', size)
				.attr('fill', fillColor)
				.attr('stroke', borderColor)
				.attr('stroke-width', borderWidth)
				.attr('stroke-dasharray', isSelected ? '8,4' : 'none');
		} else if (d.type === 'triangle') {
			const halfWidth = d.size.width / 2;
			const halfHeight = d.size.height / 2;
			const trianglePath = `M 0,${-halfHeight} L ${halfWidth},${halfHeight} L ${-halfWidth},${halfHeight} Z`;
			group
				.append('path')
				.attr('d', trianglePath)
				.attr('fill', fillColor)
				.attr('stroke', borderColor)
				.attr('stroke-width', borderWidth)
				.attr('stroke-dasharray', isSelected ? '8,4' : 'none');
		} else if (d.type === 'diamond') {
			const halfWidth = d.size.width / 2;
			const halfHeight = d.size.height / 2;
			const diamondPath = `M 0,${-halfHeight} L ${halfWidth},0 L 0,${halfHeight} L ${-halfWidth},0 Z`;
			group
				.append('path')
				.attr('d', diamondPath)
				.attr('fill', fillColor)
				.attr('stroke', borderColor)
				.attr('stroke-width', borderWidth)
				.attr('stroke-dasharray', isSelected ? '8,4' : 'none');
		} else if (d.type === 'frame') {
			const halfWidth = d.size.width / 2;
			const halfHeight = d.size.height / 2;

			// Frame background (light gray like in Figma)
			group
				.append('rect')
				.attr('x', -halfWidth)
				.attr('y', -halfHeight)
				.attr('width', d.size.width)
				.attr('height', d.size.height)
				.attr('fill', fillColor)
				.attr('stroke', borderColor)
				.attr('stroke-width', borderWidth)
				.attr('stroke-dasharray', isSelected ? '8,4' : 'none')
				.attr('rx', 8)
				.attr('ry', 8);

			// Frame label at top-left corner (like Figma)
			group
				.append('text')
				.attr('x', -halfWidth + 8)
				.attr('y', -halfHeight + 16)
				.attr('font-family', 'Inter, system-ui, sans-serif')
				.attr('font-size', '12px')
				.attr('font-weight', '500')
				.attr('fill', '#6B7280')
				.text(d.name || 'Frame');
		} else {
			// Default rectangle for unknown types
			const halfWidth = d.size.width / 2;
			const halfHeight = d.size.height / 2;
			group
				.append('rect')
				.attr('x', -halfWidth)
				.attr('y', -halfHeight)
				.attr('width', d.size.width)
				.attr('height', d.size.height)
				.attr('fill', 'transparent')
				.attr('stroke', borderColor)
				.attr('stroke-width', borderWidth)
				.attr('stroke-dasharray', isSelected ? '8,4' : 'none');
		}

		// Add element label (skip for frames as they have their own label)
		if (d.type !== 'frame') {
			const labelText = d.name || elementType.label;
			const maxWidth = Math.max(60, d.size.width - 20);

			// Split long text into multiple lines
			const words = labelText.split(' ');
			const lines = [];
			let currentLine = '';

			words.forEach((word) => {
				const testLine = currentLine ? `${currentLine} ${word}` : word;
				if (testLine.length * 8 > maxWidth && currentLine) {
					lines.push(currentLine);
					currentLine = word;
				} else {
					currentLine = testLine;
				}
			});
			if (currentLine) lines.push(currentLine);

			// Render each line
			const lineHeight = 16;
			const totalHeight = lines.length * lineHeight;
			const startY = -(totalHeight / 2) + lineHeight / 2;

			lines.forEach((line, index) => {
				group
					.append('text')
					.attr('x', 0)
					.attr('y', startY + index * lineHeight)
					.attr('text-anchor', 'middle')
					.attr('dominant-baseline', 'middle')
					.style('font-size', '12px')
					.style('font-weight', '600')
					.style('fill', '#1F2937')
					.style('pointer-events', 'none')
					.style('user-select', 'none')
					.text(line);
			});

			// Add element type icon
			group
				.append('text')
				.attr('x', -(d.size.width / 2) + 12)
				.attr('y', -(d.size.height / 2) + 12)
				.attr('text-anchor', 'middle')
				.attr('dominant-baseline', 'middle')
				.style('font-size', '14px')
				.style('pointer-events', 'none')
				.text(elementType.icon);
		}

		// Add interaction handlers
		group
			.on('click', function (event, d) {
				handleElementClick(event, d);
			})
			.on('dblclick', function (event, d) {
				event.stopPropagation();
				startTextEditing(d, event);
			});
		group.call(
			d3
				.drag()
				.on('start', function (event) {
					isDragging = true;
					// Only raise non-frame elements to preserve frame layering
					// Frames should stay in background layer
					if (d.type !== 'frame') {
						d3.select(this).raise();
					}
				})
				.on('drag', function (event) {
					d.position.x += event.dx;
					d.position.y += event.dy;
					d3.select(this).attr('transform', `translate(${d.position.x}, ${d.position.y})`);

					// 🚀 UPDATE CONNECTIONS IN REAL-TIME while dragging
					updateConnectionsForElement(d.id);
				})
				.on('end', function (event) {
					isDragging = false;
					autoSave();
				})
		);

		// Add click handler for selection
		group.on('click', function (event) {
			event.stopPropagation();
			selectedElement.set(d);
			renderCanvas(); // Re-render to show selection
		});

		// 🚀 ADD CONNECTION BUTTON when selected
		if (isSelected) {
			const connectionY =
				d.type === 'process'
					? -Math.min(d.size.width, d.size.height) / 2 - 25
					: -d.size.height / 2 - 25;

			// Green connection button
			group
				.append('circle')
				.attr('cx', 0)
				.attr('cy', connectionY)
				.attr('r', 15)
				.attr('fill', isConnecting ? '#EF4444' : '#22C55E') // Red if connecting, green otherwise
				.attr('stroke', '#FFFFFF')
				.attr('stroke-width', 3)
				.attr('class', 'connection-button')
				.style('cursor', 'pointer')
				.on('click', function (event) {
					event.stopPropagation();
					if (isConnecting && connectionStart === d.id) {
						// Cancel connection
						cancelConnection();
					} else if (isConnecting) {
						// Complete connection
						completeConnection(d.id);
					} else {
						// Start connection
						startConnection(d.id);
					}
				});

			// Connection button icon
			group
				.append('text')
				.attr('x', 0)
				.attr('y', connectionY + 2)
				.attr('text-anchor', 'middle')
				.attr('dominant-baseline', 'middle')
				.style('font-size', '16px')
				.style('font-weight', 'bold')
				.style('fill', '#FFFFFF')
				.style('pointer-events', 'none')
				.text(isConnecting ? '✕' : '🔗');
		}

		// 🚀 ADD RESIZE HANDLE when selected
		if (isSelected && elementType.resizable) {
			// Position handle at ACTUAL bottom-right corner (not relative to center)
			const handleX = d.size.width / 2 - 8; // This puts it at the right edge
			const handleY = d.size.height / 2 - 8; // This puts it at the bottom edge

			// Blue resize handle (larger and more responsive)
			const resizeHandle = group
				.append('rect')
				.attr('x', handleX)
				.attr('y', handleY)
				.attr('width', 16)
				.attr('height', 16)
				.attr('fill', '#3B82F6')
				.attr('stroke', '#FFFFFF')
				.attr('stroke-width', 2)
				.attr('rx', 3)
				.attr('class', 'resize-handle')
				.style('cursor', 'se-resize')
				.style('pointer-events', 'all')
				.on('mousedown', function (event) {
					event.preventDefault();
					event.stopPropagation();

					console.log('🔧 Resize mousedown for:', d.id);
					isResizing = true;

					const startX = event.clientX;
					const startY = event.clientY;
					const startWidth = d.size.width;
					const startHeight = d.size.height;

					function handleMouseMove(moveEvent) {
						moveEvent.preventDefault();

						const deltaX = moveEvent.clientX - startX;
						const deltaY = moveEvent.clientY - startY;

						// Calculate new size with only minimum constraints
						const newWidth = Math.max(elementType.minSize.width, startWidth + deltaX);
						const newHeight = Math.max(elementType.minSize.height, startHeight + deltaY);

						// Update size
						d.size.width = newWidth;
						d.size.height = newHeight;

						console.log('🔧 Resizing to:', newWidth, 'x', newHeight);

						// Force immediate re-render
						renderCanvas();
					}

					function handleMouseUp(upEvent) {
						upEvent.preventDefault();
						console.log('🔧 Resize ended for:', d.id);

						isResizing = false;

						// Remove event listeners
						document.removeEventListener('mousemove', handleMouseMove);
						document.removeEventListener('mouseup', handleMouseUp);

						// Update data store
						canvasData.update((data) => {
							const elementIndex = data.elements.findIndex((el) => el.id === d.id);
							if (elementIndex !== -1) {
								data.elements[elementIndex].size = { ...d.size };
							}
							return data;
						});

						autoSave();
						showUserNotification('✅ Resized successfully!');
					}

					// Add event listeners to document
					document.addEventListener('mousemove', handleMouseMove);
					document.addEventListener('mouseup', handleMouseUp);
				});

			// Resize icon (better visibility)
			group
				.append('text')
				.attr('x', handleX + 8)
				.attr('y', handleY + 11)
				.attr('text-anchor', 'middle')
				.attr('dominant-baseline', 'middle')
				.style('font-size', '10px')
				.style('font-weight', 'bold')
				.style('fill', '#FFFFFF')
				.style('pointer-events', 'none')
				.attr('class', 'resize-icon')
				.text('⤡');
		}

		// 🚀 ADD RISK-BASED THREAT INDICATOR if element has threats
		if (hasThreats) {
			const elementRisk = getElementHighestRisk(d);
			const indicatorX = d.size.width / 2 - 10;
			const indicatorY = -d.size.height / 2 + 10;

			// Risk indicator circle with color-coded risk level
			group
				.append('circle')
				.attr('cx', indicatorX)
				.attr('cy', indicatorY)
				.attr('r', 12)
				.attr('fill', elementRisk.color)
				.attr('stroke', '#FFFFFF')
				.attr('stroke-width', 2)
				.attr('class', 'threat-risk-indicator');

			// Threat count
			group
				.append('text')
				.attr('x', indicatorX)
				.attr('y', indicatorY + 3)
				.attr('text-anchor', 'middle')
				.style('font-size', '11px')
				.style('font-weight', 'bold')
				.style('fill', '#FFFFFF')
				.text(d.threats.length);

			// Risk level badge
			group
				.append('rect')
				.attr('x', indicatorX - 20)
				.attr('y', indicatorY + 15)
				.attr('width', 40)
				.attr('height', 14)
				.attr('rx', 7)
				.attr('fill', elementRisk.color)
				.attr('opacity', 0.9);

			group
				.append('text')
				.attr('x', indicatorX)
				.attr('y', indicatorY + 24)
				.attr('text-anchor', 'middle')
				.style('font-size', '9px')
				.style('font-weight', 'bold')
				.style('fill', '#FFFFFF')
				.text(elementRisk.level.toUpperCase());
		}
	}

	// 🚀 CALCULATE CONNECTION POINTS AT ELEMENT BORDERS
	function calculateConnectionPoints(sourceElement, targetElement) {
		const sourceType = ELEMENT_TYPES[sourceElement.type];
		const targetType = ELEMENT_TYPES[targetElement.type];

		// Calculate direction vector from source to target
		const dx = targetElement.position.x - sourceElement.position.x;
		const dy = targetElement.position.y - sourceElement.position.y;
		const distance = Math.sqrt(dx * dx + dy * dy);

		if (distance === 0) {
			return {
				source: { x: sourceElement.position.x, y: sourceElement.position.y },
				target: { x: targetElement.position.x, y: targetElement.position.y }
			};
		}

		// Normalize direction
		const unitX = dx / distance;
		const unitY = dy / distance;

		// Calculate source connection point
		let sourceConnectionPoint;
		if (sourceType.shape === 'circle') {
			// For circles, use radius
			const radius = sourceElement.size.width / 2;
			sourceConnectionPoint = {
				x: sourceElement.position.x + unitX * radius,
				y: sourceElement.position.y + unitY * radius
			};
		} else {
			// For rectangles, find intersection with border
			const halfWidth = sourceElement.size.width / 2;
			const halfHeight = sourceElement.size.height / 2;

			// Calculate intersection point with rectangle border
			const absUnitX = Math.abs(unitX);
			const absUnitY = Math.abs(unitY);

			if (absUnitX * halfHeight > absUnitY * halfWidth) {
				// Intersection with left/right side
				sourceConnectionPoint = {
					x: sourceElement.position.x + (unitX > 0 ? halfWidth : -halfWidth),
					y: sourceElement.position.y + (unitY * halfWidth) / absUnitX
				};
			} else {
				// Intersection with top/bottom side
				sourceConnectionPoint = {
					x: sourceElement.position.x + (unitX * halfHeight) / absUnitY,
					y: sourceElement.position.y + (unitY > 0 ? halfHeight : -halfHeight)
				};
			}
		}

		// Calculate target connection point (reverse direction)
		let targetConnectionPoint;
		if (targetType.shape === 'circle') {
			// For circles, use radius
			const radius = targetElement.size.width / 2;
			targetConnectionPoint = {
				x: targetElement.position.x - unitX * radius,
				y: targetElement.position.y - unitY * radius
			};
		} else {
			// For rectangles, find intersection with border
			const halfWidth = targetElement.size.width / 2;
			const halfHeight = targetElement.size.height / 2;

			// Calculate intersection point with rectangle border (reverse direction)
			const absUnitX = Math.abs(unitX);
			const absUnitY = Math.abs(unitY);

			if (absUnitX * halfHeight > absUnitY * halfWidth) {
				// Intersection with left/right side
				targetConnectionPoint = {
					x: targetElement.position.x - (unitX > 0 ? halfWidth : -halfWidth),
					y: targetElement.position.y - (unitY * halfWidth) / absUnitX
				};
			} else {
				// Intersection with top/bottom side
				targetConnectionPoint = {
					x: targetElement.position.x - (unitX * halfHeight) / absUnitY,
					y: targetElement.position.y - (unitY > 0 ? halfHeight : -halfHeight)
				};
			}
		}

		return {
			source: sourceConnectionPoint,
			target: targetConnectionPoint
		};
	}

	function renderConnections() {
		const data = $canvasData;

		// Add arrow marker definition
		if (!g.select('defs').node()) {
			const defs = g.append('defs');
			defs
				.append('marker')
				.attr('id', 'arrowhead')
				.attr('viewBox', '0 -5 10 10')
				.attr('refX', 8)
				.attr('refY', 0)
				.attr('markerWidth', 6)
				.attr('markerHeight', 6)
				.attr('orient', 'auto')
				.append('path')
				.attr('d', 'M0,-5L10,0L0,5')
				.attr('fill', '#000000');
		}

		// 🚀 RENDER ALL CONNECTIONS with border-to-border positioning
		data.connections.forEach((connection, index) => {
			const sourceElement = data.elements.find((el) => el.id === connection.source);
			const targetElement = data.elements.find((el) => el.id === connection.target);

			if (sourceElement && targetElement) {
				const hasThreats = connection.threats && connection.threats.length > 0;
				const isSelected = $selectedConnection && $selectedConnection.id === connection.id;

				// Calculate proper connection points at borders
				const connectionPoints = calculateConnectionPoints(sourceElement, targetElement);

				// Draw connection line with unique class
				g.append('line')
					.datum(connection)
					.attr('x1', connectionPoints.source.x)
					.attr('y1', connectionPoints.source.y)
					.attr('x2', connectionPoints.target.x)
					.attr('y2', connectionPoints.target.y)
					.attr('stroke', hasThreats ? '#DC2626' : '#000000')
					.attr('stroke-width', isSelected ? 4 : hasThreats ? 3 : 2)
					.attr('stroke-dasharray', isSelected ? '8,4' : 'none')
					.attr('marker-end', 'url(#arrowhead)')
					.attr('class', `connection-line connection-${connection.id}`)
					.style('cursor', 'pointer')
					.on('click', function (event, d) {
						event.stopPropagation();
						handleConnectionClick(event, d);
					});

				// Add connection label at midpoint
				const midX = (connectionPoints.source.x + connectionPoints.target.x) / 2;
				const midY = (connectionPoints.source.y + connectionPoints.target.y) / 2;

				g.append('text')
					.datum(connection)
					.attr('x', midX)
					.attr('y', midY - 5)
					.attr('text-anchor', 'middle')
					.attr('font-size', '12px')
					.attr('fill', '#666')
					.attr('class', `connection-label connection-${connection.id}`)
					.text(connection.name || 'Data Flow');

				// Add threat indicator for connections
				if (hasThreats) {
					g.append('circle')
						.datum(connection)
						.attr('cx', midX)
						.attr('cy', midY + 15)
						.attr('r', 8)
						.attr('fill', '#DC2626')
						.attr('stroke', '#FFFFFF')
						.attr('stroke-width', 2)
						.attr('class', `connection-threat connection-${connection.id}`);

					g.append('text')
						.datum(connection)
						.attr('x', midX)
						.attr('y', midY + 19)
						.attr('text-anchor', 'middle')
						.style('font-size', '10px')
						.style('font-weight', 'bold')
						.style('fill', '#FFFFFF')
						.attr('class', `connection-threat-text connection-${connection.id}`)
						.text(connection.threats.length);
				}

				// Add selection indicator for connections
				if (isSelected) {
					g.append('circle')
						.datum(connection)
						.attr('cx', midX)
						.attr('cy', midY)
						.attr('r', 12)
						.attr('fill', '#3B82F6')
						.attr('stroke', '#FFFFFF')
						.attr('stroke-width', 2)
						.attr('class', `connection-selection connection-${connection.id}`)
						.style('cursor', 'pointer');

					g.append('text')
						.datum(connection)
						.attr('x', midX)
						.attr('y', midY + 3)
						.attr('text-anchor', 'middle')
						.style('font-size', '12px')
						.style('font-weight', 'bold')
						.style('fill', '#FFFFFF')
						.attr('class', `connection-selection-text connection-${connection.id}`)
						.text('⚡')
						.style('pointer-events', 'none');
				}
			}
		});
	}

	function handleElementClick(event, d) {
		event.stopPropagation();
		selectedElement.set(d);
		selectedConnection.set(null);
		console.log('Selected element:', d);
		// Force re-render to show selection handles and connection points
		renderCanvas();
	}

	function handleElementDoubleClick(event, d) {
		event.stopPropagation();
		openThreatDialog(d);
	}

	function handleConnectionClick(event, d) {
		event.stopPropagation();
		selectedConnection.set(d);
		selectedElement.set(null);
		console.log('Selected connection:', d);
		renderCanvas(); // Re-render to show selection feedback
	}

	function handleDragStart(event, d) {
		// Only raise non-frame elements to preserve frame layering
		// Frames should stay in background layer
		if (d.type !== 'frame') {
			d3.select(this).raise();
		}
	}

	function handleDrag(event, d) {
		d.position.x = event.x;
		d.position.y = event.y;
		d3.select(this).attr('transform', `translate(${d.position.x}, ${d.position.y})`);
	}

	function handleDragEnd(event, d) {
		canvasData.update((data) => data); // Trigger reactivity
		autoSave();
	}

	// IMPROVED RESIZE SYSTEM
	function handleResize(event, element) {
		const elementType = ELEMENT_TYPES[element.type];
		if (!elementType) return;

		// Calculate new size based on drag movement with minimum size constraints
		element.size.width = Math.max(elementType.minSize.width, element.size.width + event.dx);
		element.size.height = Math.max(elementType.minSize.height, element.size.height + event.dy);

		renderCanvas();
		console.log('📏 Resized', element.type, 'to:', element.size.width + 'x' + element.size.height);
	}

	function deleteSelectedElement() {
		const selected = $selectedElement;
		if (!selected) return;

		canvasData.update((data) => {
			data.elements = data.elements.filter((e) => e.id !== selected.id);
			data.connections = data.connections.filter(
				(c) => c.source !== selected.id && c.target !== selected.id
			);
			return data;
		});

		selectedElement.set(null);
		renderCanvas();
		autoSave();
	}

	function deleteSelectedConnection() {
		const selected = $selectedConnection;
		if (!selected) return;

		canvasData.update((data) => {
			data.connections = data.connections.filter((c) => c.id !== selected.id);
			return data;
		});

		selectedConnection.set(null);
		renderCanvas();
		autoSave();
		showUserNotification('✅ Connection deleted successfully!');
	}

	let autoSaveTimeout;
	function autoSave() {
		// Skip auto-save if AI analysis is in progress to prevent conflicts
		if (aiAnalyzing) {
			console.log('⚠️ Skipping auto-save during AI analysis');
			return;
		}

		clearTimeout(autoSaveTimeout);
		autoSaveTimeout = setTimeout(saveCanvas, 3000); // Auto-save after 3 seconds
	}

	async function saveCanvas() {
		if (!modelData) return;

		// Skip save if AI analysis is in progress to prevent conflicts
		if (aiAnalyzing) {
			console.log('⚠️ Skipping canvas save during AI analysis');
			return;
		}

		try {
			saving = true;
			const data = $canvasData;

			console.log('💾 Saving canvas data...');

			// For now, we'll use the simplified PUT endpoint with timeout handling
			const controller = new AbortController();
			const timeoutId = setTimeout(() => controller.abort(), 35000); // 35 second timeout to match backend

			const response = await fetch(`${API_BASE_URL}/api/threat-modeling/models/${modelId}`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					canvas_data: data
				}),
				signal: controller.signal
			});

			clearTimeout(timeoutId);

			if (response.ok) {
				lastSaved = new Date();
				console.log('✅ Canvas saved successfully');
			} else {
				console.error('❌ Failed to save canvas:', response.statusText);
				if (response.status === 504) {
					showUserNotification('⚠️ Save timeout - your work is safe locally');
				}
			}
		} catch (err) {
			if (err.name === 'AbortError') {
				console.error('❌ Save timeout after 20 seconds');
				showUserNotification('⚠️ Save timeout - your work is safe locally');
			} else {
				console.error('❌ Save error:', err);
			}
		} finally {
			saving = false;
		}
	}

	function handleKeydown(event) {
		if (event.key === 'Delete' && $selectedElement) {
			deleteSelectedElement();
		} else if (event.key === 'Escape') {
			selectedElement.set(null);
			canvasMode.set('select');
		}
	}

	function exportDiagram(format) {
		if (format === 'png') {
			// Convert SVG to PNG
			const svgElement = svg.node();
			const svgData = new XMLSerializer().serializeToString(svgElement);
			const canvas = document.createElement('canvas');
			const ctx = canvas.getContext('2d');
			const img = new Image();

			img.onload = function () {
				canvas.width = img.width;
				canvas.height = img.height;
				ctx.drawImage(img, 0, 0);

				const pngFile = canvas.toDataURL('image/png');
				const downloadLink = document.createElement('a');
				downloadLink.download = `${modelData.name}_diagram.png`;
				downloadLink.href = pngFile;
				downloadLink.click();
			};

			img.src = 'data:image/svg+xml;base64,' + btoa(svgData);
		} else if (format === 'svg') {
			const svgData = new XMLSerializer().serializeToString(svg.node());
			const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
			const svgUrl = URL.createObjectURL(svgBlob);
			const downloadLink = document.createElement('a');
			downloadLink.href = svgUrl;
			downloadLink.download = `${modelData.name}_diagram.svg`;
			downloadLink.click();
		}
	}

	// 🤖 AI-OPTIMIZED CANVAS EXPORT
	// Creates high-quality image specifically for Claude AI vision analysis
	function exportCanvasForAI() {
		return new Promise((resolve, reject) => {
			try {
				console.log('📸 Creating AI-optimized canvas image...');

				if (!svg || !g) {
					reject(new Error('Canvas not initialized'));
					return;
				}

				// Get current canvas bounds with some padding
				const padding = 50;
				const bounds = g.node().getBBox();
				const width = Math.max(800, bounds.width + padding * 2); // Minimum 800px width
				const height = Math.max(600, bounds.height + padding * 2); // Minimum 600px height

				// Create a clean SVG for AI analysis
				const aiSvg = d3
					.create('svg')
					.attr('width', width)
					.attr('height', height)
					.attr('viewBox', `${bounds.x - padding} ${bounds.y - padding} ${width} ${height}`)
					.style('background-color', '#ffffff'); // White background for better AI analysis

				// Copy the current canvas content
				const canvasGroup = aiSvg.append('g');
				const originalContent = g.node().cloneNode(true);
				canvasGroup.node().appendChild(originalContent);

				// Add title and labels for better AI understanding
				const titleGroup = aiSvg
					.append('g')
					.attr('transform', `translate(${bounds.x - padding + 10}, ${bounds.y - padding + 20})`);

				titleGroup
					.append('text')
					.attr('x', 0)
					.attr('y', 0)
					.attr('font-family', 'Arial, sans-serif')
					.attr('font-size', '16')
					.attr('font-weight', 'bold')
					.attr('fill', '#000000')
					.text(`${modelData?.name || 'Threat Model'} - ${currentMethodology} Analysis`);

				// Add methodology info
				titleGroup
					.append('text')
					.attr('x', 0)
					.attr('y', 20)
					.attr('font-family', 'Arial, sans-serif')
					.attr('font-size', '12')
					.attr('fill', '#666666')
					.text(
						`Components: ${$canvasData.elements.length} | Connections: ${$canvasData.connections.length} | Threats: ${$canvasData.threats.length}`
					);

				// Convert to PNG with high quality for AI analysis
				const svgData = new XMLSerializer().serializeToString(aiSvg.node());
				const canvas = document.createElement('canvas');
				const ctx = canvas.getContext('2d');

				// High-resolution canvas for better AI analysis
				const scaleFactor = 2; // 2x resolution for crispy image
				canvas.width = width * scaleFactor;
				canvas.height = height * scaleFactor;
				ctx.scale(scaleFactor, scaleFactor);

				const img = new Image();

				img.onload = function () {
					// Fill white background
					ctx.fillStyle = '#ffffff';
					ctx.fillRect(0, 0, width, height);

					// Draw the SVG
					ctx.drawImage(img, 0, 0);

					// Convert to base64 string (removing data:image/png;base64, prefix)
					const base64Image = canvas.toDataURL('image/png', 1.0).split(',')[1];

					console.log('✅ AI-optimized image created:', {
						width: canvas.width,
						height: canvas.height,
						dataSize: base64Image.length,
						components: $canvasData.elements.length
					});

					resolve(base64Image);
				};

				img.onerror = function (error) {
					console.error('❌ Failed to create AI image:', error);
					reject(new Error('Failed to generate AI image'));
				};

				// Fix: Use proper UTF-8 encoding for SVG with Unicode characters
				try {
					// Convert string to UTF-8 bytes then to base64
					const utf8Bytes = new TextEncoder().encode(svgData);
					const base64String = btoa(String.fromCharCode(...utf8Bytes));
					img.src = 'data:image/svg+xml;base64,' + base64String;
				} catch (encodingError) {
					// Fallback: URL encode the SVG instead of base64
					console.warn('⚠️ Base64 encoding failed, using URL encoding fallback');
					const encodedSvg = encodeURIComponent(svgData);
					img.src = 'data:image/svg+xml;charset=utf-8,' + encodedSvg;
				}
			} catch (error) {
				console.error('❌ Error in exportCanvasForAI:', error);
				reject(error);
			}
		});
	}

	// 🏷️ THREAT CATEGORIZATION HELPER
	// Categorizes user threats by framework for intelligent AI analysis
	function categorizeUserThreatsByFramework(threats, methodology) {
		console.log(`🔍 Categorizing ${threats.length} user threats for ${methodology} framework`);

		const frameworkCategories = {
			STRIDE: [
				'Spoofing',
				'Tampering',
				'Repudiation',
				'Information Disclosure',
				'Denial of Service',
				'Elevation of Privilege'
			],
			CIA: ['Confidentiality Breach', 'Integrity Violation', 'Availability Loss'],
			LINDDUN: [
				'Linkability',
				'Identifiability',
				'Non-repudiation',
				'Detectability',
				'Disclosure of Information',
				'Unawareness',
				'Non-compliance'
			]
		};

		const categories = frameworkCategories[methodology] || [];
		const categorizedThreats = {};

		// Initialize categories
		categories.forEach((category) => {
			categorizedThreats[category] = [];
		});

		// Categorize threats based on type/title
		threats.forEach((threat) => {
			let assigned = false;

			// Try to match by threat type first
			for (const category of categories) {
				if (
					threat.type &&
					threat.type.toLowerCase().includes(category.toLowerCase().replace(/\s+/g, ''))
				) {
					categorizedThreats[category].push(threat);
					assigned = true;
					break;
				}
			}

			// If not assigned by type, try by title content
			if (!assigned) {
				for (const category of categories) {
					const keywords = getKeywordsForCategory(category);
					if (
						keywords.some(
							(keyword) =>
								threat.title?.toLowerCase().includes(keyword) ||
								threat.description?.toLowerCase().includes(keyword)
						)
					) {
						categorizedThreats[category].push(threat);
						assigned = true;
						break;
					}
				}
			}

			// If still not assigned, put in first category as fallback
			if (!assigned && categories.length > 0) {
				categorizedThreats[categories[0]].push(threat);
			}
		});

		console.log(
			'✅ Threat categorization complete:',
			Object.entries(categorizedThreats)
				.map(([cat, threats]) => `${cat}: ${threats.length}`)
				.join(', ')
		);
		return categorizedThreats;
	}

	// Get keywords for automatic threat categorization
	function getKeywordsForCategory(category) {
		const keywordMap = {
			Spoofing: ['spoof', 'impersonat', 'fake', 'masquerade', 'identity theft'],
			Tampering: ['tamper', 'modify', 'alter', 'corrupt', 'inject', 'manipulat'],
			Repudiation: ['repudiat', 'deny', 'log', 'audit', 'trace', 'evidence'],
			'Information Disclosure': ['disclosure', 'leak', 'expose', 'reveal', 'unauthorized access'],
			'Denial of Service': ['dos', 'denial', 'unavailable', 'overload', 'flood', 'exhaust'],
			'Elevation of Privilege': [
				'privilege',
				'escalat',
				'unauthorized',
				'admin',
				'root',
				'permission'
			],
			'Confidentiality Breach': ['confidential', 'secret', 'private', 'sensitive', 'classified'],
			'Integrity Violation': ['integrity', 'corrupt', 'tamper', 'modify', 'authentic'],
			'Availability Loss': ['availability', 'downtime', 'outage', 'accessible', 'service'],
			Linkability: ['link', 'correlat', 'connect', 'associate', 'track'],
			Identifiability: ['identif', 'recogniz', 'distinguish', 'single out'],
			'Non-repudiation': ['non-repudiat', 'undeniable', 'proof', 'signature'],
			Detectability: ['detect', 'observable', 'monitor', 'surveil'],
			'Disclosure of Information': ['disclosure', 'leak', 'expose', 'reveal'],
			Unawareness: ['unaware', 'unknow', 'hidden', 'transparent'],
			'Non-compliance': ['compliance', 'regulation', 'policy', 'standard', 'legal']
		};

		return keywordMap[category] || [];
	}

	// 🧠 AI ANALYSIS DATA PREPARATION
	// Creates comprehensive data payload for Claude AI analysis
	async function prepareAIAnalysisData(analysisType = 'comprehensive') {
		try {
			console.log('🔄 Preparing AI analysis data...');

			// 1. Get current canvas state
			const elements = $canvasData.elements;
			const connections = $canvasData.connections;
			const threats = $canvasData.threats;

			// 2. Determine analysis type based on current state
			let actualAnalysisType = analysisType;
			if (elements.length === 0 && connections.length === 0) {
				actualAnalysisType = 'document_only';
			} else if (elements.length < 3 || connections.length < 2) {
				actualAnalysisType = 'partial';
			}

			console.log(
				`📊 Analysis type: ${actualAnalysisType} (${elements.length} components, ${connections.length} connections)`
			);

			// 3. Get document context if available
			let documentText = '';
			try {
				if (modelData?.document_analysis?.extracted_text) {
					documentText = modelData.document_analysis.extracted_text;
					console.log('📄 Document found:', documentText.substring(0, 100) + '...');
				}
			} catch (error) {
				console.warn('⚠️ No document context available:', error);
			}

			// 4. Generate high-quality diagram image for Claude vision analysis
			let diagramImage = '';
			if (elements.length > 0) {
				try {
					diagramImage = await exportCanvasForAI();
					console.log('📸 Diagram image generated for AI analysis');
				} catch (error) {
					console.warn('⚠️ Failed to generate diagram image:', error);
				}
			}

			// 5. 🎯 PREPARE USER THREAT CONTEXT (COLLABORATIVE INTELLIGENCE!)
			// Analyze existing user threats to provide AI with context
			let userThreatContext = null;
			if (threats && threats.length > 0) {
				// Categorize threats by current methodology
				const categorizedThreats = categorizeUserThreatsByFramework(threats, currentMethodology);

				// Get threat details for each category
				const threatsByCategory = {};
				for (const [category, categoryThreats] of Object.entries(categorizedThreats)) {
					if (categoryThreats.length > 0) {
						threatsByCategory[category] = categoryThreats.map((threat) => ({
							id: threat.id,
							title: threat.title,
							type: threat.type,
							description: threat.description || '',
							mitigation: threat.mitigation || '',
							severity: threat.severity || 'Medium',
							likelihood: threat.likelihood || 'Medium',
							impact: threat.impact || 'Medium',
							riskLevel: threat.riskLevel || 'Medium',
							componentId: threat.componentId,
							// Find component name for context
							componentName:
								elements.find((el) => el.id === threat.componentId)?.name || 'Unknown Component',
							createdAt: threat.createdAt || 'Unknown'
						}));
					}
				}

				userThreatContext = {
					methodology: currentMethodology,
					total_threats: threats.length,
					threats_by_category: threatsByCategory,
					coverage_summary: Object.entries(threatsByCategory)
						.map(([category, categoryThreats]) => `${category}: ${categoryThreats.length} threats`)
						.join(', '),
					// Analysis hints for AI
					analysis_notes: {
						existing_coverage: Object.keys(threatsByCategory),
						gaps_to_analyze: Object.keys(categorizedThreats).filter(
							(cat) => !threatsByCategory[cat] || threatsByCategory[cat].length === 0
						),
						components_with_threats: [...new Set(threats.map((t) => t.componentId))].length,
						components_without_threats:
							elements.length - [...new Set(threats.map((t) => t.componentId))].length
					}
				};
			}

			// 6. Prepare component data with user labels (KEY FEATURE!)
			const componentsData = elements.map((element) => ({
				id: element.id,
				type: element.type,
				name: element.name, // This is the user-customized label!
				user_label: element.name, // Explicit user label for Claude
				position: element.position,
				size: element.size,
				properties: element.properties || {},
				threats: element.threats || [],
				threat_count: element.threats?.length || 0,
				// Add user threat details for this component
				user_threats: threats
					.filter((threat) => threat.componentId === element.id)
					.map((threat) => ({
						id: threat.id,
						title: threat.title,
						type: threat.type,
						severity: threat.severity || 'Medium'
					}))
			}));

			// 7. Prepare connections data
			const connectionsData = connections.map((conn) => ({
				id: conn.id,
				source: conn.source,
				target: conn.target,
				label: conn.label || '',
				// Add source/target component names for context
				source_name: elements.find((el) => el.id === conn.source)?.name || 'Unknown',
				target_name: elements.find((el) => el.id === conn.target)?.name || 'Unknown'
			}));

			// 8. Create comprehensive analysis payload
			const analysisPayload = {
				// Core canvas data
				components: componentsData,
				connections: connectionsData,
				methodology: currentMethodology,

				// 🛡️ USER THREAT CONTEXT FOR COLLABORATIVE ANALYSIS
				user_threat_context: userThreatContext,

				// Context data
				document_text: documentText,
				diagram_image: diagramImage,
				analysis_type: actualAnalysisType,

				// Model metadata
				model_id: modelId,
				model_name: modelData?.name || 'Unnamed Threat Model',

				// Analysis metadata
				timestamp: new Date().toISOString(),
				canvas_state: {
					has_elements: elements.length > 0,
					has_connections: connections.length > 0,
					has_threats: threats.length > 0,
					has_document: !!documentText,
					has_diagram: !!diagramImage,
					complexity_score: Math.min(elements.length + connections.length, 10)
				}
			};

			return analysisPayload;
		} catch (error) {
			console.error('❌ Error preparing AI analysis data:', error);
			throw error;
		}
	}

	// 🚀 TRIGGER AI ANALYSIS
	// Main function to request AI analysis from Claude
	async function performAIAnalysis(analysisType = 'comprehensive') {
		if (!modelData) {
			showUserNotification('❌ Model not loaded');
			return;
		}

		// Prevent multiple concurrent requests
		if (aiAnalyzing) {
			console.log('⚠️ AI analysis already in progress, ignoring duplicate request');
			showUserNotification('⚠️ AI analysis already in progress...');
			return;
		}

		// Debounce rapid requests
		const now = Date.now();
		if (now - lastAnalysisRequest < ANALYSIS_DEBOUNCE_MS) {
			console.log('⚠️ Request too soon after last attempt, ignoring');
			showUserNotification('⚠️ Please wait before starting another analysis');
			return;
		}
		lastAnalysisRequest = now;

		try {
			// Set analyzing state immediately
			aiAnalyzing = true;
			taskStatus = 'queued';
			console.log('🤖 Starting async AI threat analysis...');

			// Show immediate feedback to user
			showUserNotification('🚀 Queueing AI analysis task...');

			// Prepare comprehensive data payload
			const analysisData = await prepareAIAnalysisData(analysisType);

			// Get user ID for async tracking
			const userId = currentUser?.sub || 'anonymous';

			// Send to async Claude API endpoint with user_id parameter
			const response = await fetch(
				`${API_BASE_URL}/api/ai/claude/analyze-threats-async?user_id=${encodeURIComponent(userId)}`,
				{
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify(analysisData)
				}
			);

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || `HTTP ${response.status}`);
			}

			const result = await response.json();

			// Async endpoint returns task_id immediately
			if (result.task_id) {
				pendingTaskId = result.task_id;
				taskStatus = 'processing';
				console.log(`✅ Analysis task queued: ${result.task_id}`);
				showUserNotification("⏳ Analysis in progress... You'll be notified when complete!");

				// Start polling as fallback in case WebSocket doesn't deliver
				// This ensures results are shown even if WebSocket fails
				pollTaskStatus(result.task_id);
			} else {
				throw new Error('No task_id received from async endpoint');
			}
		} catch (error) {
			console.error('❌ AI analysis failed:', error);
			taskStatus = 'failed';
			showUserNotification(`❌ AI analysis failed: ${error.message}`);
			throw error;
		} finally {
			// Don't reset aiAnalyzing here - it will be reset when WebSocket delivers the result
			// aiAnalyzing = false;
		}
	}

	// 💾 Save AI analysis to database
	async function saveAIAnalysisToModel(result) {
		try {
			console.log('💾 Saving AI analysis to database...', result);

			// Prepare analysis data in the format expected by backend
			const analysisData = {
				id: result.id || result.task_id || `analysis-${Date.now()}-${modelId.substring(0, 8)}`,
				task_id: result.task_id,
				analysis_type: result.analysis_type || 'comprehensive',
				methodology: result.methodology || currentMethodology,
				analysis: result.analysis,
				structured_analysis: result.structured_analysis || result.parsed_sections,
				timestamp: result.timestamp || new Date().toISOString(),
				diagram_elements_count: result.diagram_elements_count || $canvasData.elements.length,
				diagram_connections_count:
					result.diagram_connections_count || $canvasData.connections.length,
				has_document: !!modelData?.document_analysis,
				has_diagram: $canvasData.elements.length > 0
			};

			// Send to backend API
			const response = await fetch(
				`${API_BASE_URL}/api/threat-modeling/models/${modelId}/analyses`,
				{
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({ analysis_data: analysisData })
				}
			);

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || `Save failed: ${response.status}`);
			}

			const responseData = await response.json();
			console.log('✅ Analysis saved to database:', responseData);

			return analysisData;
		} catch (error) {
			console.error('❌ Failed to save analysis to database:', error);
			throw error;
		}
	}

	// Helper function to save analysis to history (used by WebSocket handler)
	async function saveAnalysisToHistory(result) {
		try {
			// Save to database first
			const savedAnalysis = await saveAIAnalysisToModel(result);
			console.log('✅ Saved analysis to database successfully');

			// Load existing history from localStorage
			let existingHistory = [];
			try {
				const localStorageKey = `analysis-history-${modelId}`;
				const localHistory = localStorage.getItem(localStorageKey);
				if (localHistory) {
					const parsedHistory = JSON.parse(localHistory);
					if (Array.isArray(parsedHistory)) {
						existingHistory = parsedHistory.filter((entry) => entry && entry.id && entry.timestamp);
						console.log(`📚 Found ${existingHistory.length} existing analyses in localStorage`);
					}
				}
			} catch (storageError) {
				console.warn('⚠️ Failed to load existing localStorage history:', storageError);
			}

			// Create new history entry
			const historyEntry = {
				id: savedAnalysis.id || `analysis-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
				timestamp: savedAnalysis.timestamp || new Date().toISOString(),
				methodology: savedAnalysis.methodology || 'STRIDE',
				analysis_type: savedAnalysis.analysis_type || 'comprehensive',
				diagram_elements_count: savedAnalysis.diagram_elements_count || $canvasData.elements.length,
				diagram_connections_count:
					savedAnalysis.diagram_connections_count || $canvasData.connections.length,
				result: savedAnalysis,
				analysis: savedAnalysis.analysis || 'No analysis content',
				success: true
			};

			// Check for duplicates
			const allHistory = [...existingHistory, ...analysisHistory];
			const existingIndex = allHistory.findIndex(
				(entry) =>
					entry.id === historyEntry.id ||
					Math.abs(new Date(entry.timestamp) - new Date(historyEntry.timestamp)) < 1000
			);

			if (existingIndex === -1) {
				// Add to the beginning of history
				const newHistory = [historyEntry, ...existingHistory];
				analysisHistory = newHistory;

				console.log(`📈 Added new analysis to history. Total: ${newHistory.length}`);

				// Save to localStorage
				try {
					localStorage.setItem(`analysis-history-${modelId}`, JSON.stringify(newHistory));
					console.log('💾 Saved analysis history to localStorage');
				} catch (e) {
					console.warn('⚠️ Failed to save to localStorage:', e);
				}
			} else {
				console.log('⚠️ Duplicate analysis detected, not adding to history');
			}
		} catch (saveError) {
			console.warn('⚠️ Failed to save AI analysis:', saveError);
		}
	}

	/**
	 * Poll task status as fallback mechanism
	 * This ensures results are displayed even if WebSocket doesn't deliver
	 */
	let pollIntervalId = null;

	function pollTaskStatus(taskId) {
		// Clear any existing polling
		if (pollIntervalId) {
			clearInterval(pollIntervalId);
		}

		let pollAttempts = 0;
		const MAX_POLL_ATTEMPTS = 60; // 5 minutes at 5-second intervals

		console.log(`🔄 Starting polling for task: ${taskId}`);

		pollIntervalId = setInterval(async () => {
			pollAttempts++;

			try {
				// Get auth token
				const authClient = await getAuthClient();
				const token = await authClient.getTokenSilently();

				// Poll the task status endpoint
				const response = await fetch(`${API_BASE_URL}/api/ai/task/${taskId}/status`, {
					headers: {
						Authorization: `Bearer ${token}`
					}
				});

				if (!response.ok) {
					console.warn(`⚠️ Poll attempt ${pollAttempts}: Status ${response.status}`);

					// Stop polling if max attempts reached
					if (pollAttempts >= MAX_POLL_ATTEMPTS) {
						clearInterval(pollIntervalId);
						pollIntervalId = null;
						aiAnalyzing = false;
						taskStatus = 'failed';
						showUserNotification('❌ Analysis timeout. Please try again.');
						console.error('❌ Polling timeout after 5 minutes');
					}
					return;
				}

				const status = await response.json();
				console.log(`📊 Poll attempt ${pollAttempts}: Status = ${status.status}`);

				if (status.status === 'completed' && status.result) {
					// Task completed! Stop polling and handle the result
					clearInterval(pollIntervalId);
					pollIntervalId = null;

					console.log('✅ Task completed via polling fallback');

					// Call the same handler that WebSocket would call
					handleThreatAnalysisCompleted(status.result);
				} else if (status.status === 'failed') {
					// Task failed
					clearInterval(pollIntervalId);
					pollIntervalId = null;
					aiAnalyzing = false;
					taskStatus = 'failed';
					showUserNotification('❌ Analysis failed. Please try again.');
					console.error('❌ Task failed:', status.error);
				} else if (pollAttempts >= MAX_POLL_ATTEMPTS) {
					// Timeout
					clearInterval(pollIntervalId);
					pollIntervalId = null;
					aiAnalyzing = false;
					taskStatus = 'failed';
					showUserNotification('❌ Analysis timeout. Please try again.');
					console.error('❌ Polling timeout after 5 minutes');
				}
			} catch (pollError) {
				console.error('❌ Polling error:', pollError);

				// Stop polling on error if max attempts reached
				if (pollAttempts >= MAX_POLL_ATTEMPTS) {
					clearInterval(pollIntervalId);
					pollIntervalId = null;
					aiAnalyzing = false;
					taskStatus = 'failed';
					showUserNotification('❌ Failed to check analysis status.');
				}
			}
		}, 5000); // Poll every 5 seconds
	}
	// Load analysis history for this threat model from DATABASE
	async function loadAnalysisHistory() {
		try {
			loadingHistory = true;
			console.log('📚 Loading analysis history from DATABASE...');

			const response = await fetch(
				`${API_BASE_URL}/api/threat-modeling/models/${modelId}/analyses`
			);

			if (response.ok) {
				const history = await response.json();

				if (Array.isArray(history)) {
					// Backend now returns FULL analysis_data - no transformation needed!
					analysisHistory = history;

					console.log(`✅ Loaded ${analysisHistory.length} analyses from DATABASE`);
					console.log('📊 First analysis structure:', analysisHistory[0]);
				} else {
					console.warn('⚠️ API returned non-array history');
					analysisHistory = [];
				}
			} else {
				console.warn(`⚠️ Failed to load history: ${response.status}`);
				analysisHistory = [];
			}
		} catch (error) {
			console.error('❌ Failed to load analysis history from database:', error);
			analysisHistory = [];
		} finally {
			loadingHistory = false;
		}
	}

	// Load a specific past analysis
	function loadPastAnalysis(analysis) {
		console.log('📊 Loading past analysis:', analysis);
		console.log('🔍 Analysis structure check:', {
			hasStructuredAnalysis: !!analysis.structured_analysis,
			hasParsedSections: !!analysis.structured_analysis?.parsed_sections,
			hasServiceOverview: !!analysis.structured_analysis?.parsed_sections?.service_overview,
			hasThreatCategories: !!analysis.structured_analysis?.threat_categories
		});

		// ✅ DON'T use spread operator - assign directly to preserve object reference
		aiAnalysisResult = analysis;
		currentAIView = 'result'; // ✅ Set view to 'result' to show the analysis
		showAIAnalysisPanel = true;
		showAnalysisHistory = false;

		// Force a tick to ensure UI updates
		tick().then(() => {
			console.log('✅ UI should be updated now');
			console.log('✅ currentAIView:', currentAIView);
			console.log('✅ aiAnalysisResult exists:', !!aiAnalysisResult);
			console.log(
				'✅ aiAnalysisResult.structured_analysis:',
				aiAnalysisResult?.structured_analysis
			);
		});

		showUserNotification(
			`📊 Loaded analysis from ${new Date(analysis.timestamp).toLocaleDateString()}`
		);
	}

	// Export threat model as JSON
	function exportToJSON() {
		try {
			const threatModelData = {
				metadata: {
					name: modelData?.name || 'Untitled Threat Model',
					description: modelData?.description || '',
					methodology: currentMethodology,
					exportDate: new Date().toISOString(),
					version: '1.0',
					tool: 'WithOps DevSecOps Threat Modeling'
				},
				canvas: {
					elements: $canvasData.elements,
					connections: $canvasData.connections,
					threats: $canvasData.threats,
					metadata: $canvasData.metadata
				}
			};

			const jsonString = JSON.stringify(threatModelData, null, 2);
			const jsonBlob = new Blob([jsonString], { type: 'application/json' });
			const jsonUrl = URL.createObjectURL(jsonBlob);

			const downloadLink = document.createElement('a');
			downloadLink.href = jsonUrl;
			downloadLink.download = `${modelData?.name || 'threat_model'}_${new Date().toISOString().split('T')[0]}.json`;
			downloadLink.click();

			// Clean up
			URL.revokeObjectURL(jsonUrl);

			showUserNotification('✅ Threat model exported successfully');
			console.log('💾 Threat model exported as JSON');
		} catch (error) {
			console.error('❌ Export failed:', error);
			showUserNotification('❌ Failed to export threat model');
		}
	}

	// AI Review System Functions
	function openReviewDialog(category) {
		currentReviewCategory = category;
		reviewFeedback = reviewState[category]?.feedback || '';
		reviewValid = reviewState[category]?.valid;
		showReviewDialog = true;
	}

	function closeReviewDialog() {
		showReviewDialog = false;
		currentReviewCategory = null;
		reviewFeedback = '';
		reviewValid = null;
	}

	async function submitReview() {
		if (!currentReviewCategory || reviewValid === null) {
			showUserNotification('⚠️ Please select valid/invalid and provide feedback');
			return;
		}

		try {
			// Update review state
			reviewState[currentReviewCategory] = {
				reviewed: true,
				valid: reviewValid,
				feedback: reviewFeedback,
				timestamp: new Date().toISOString()
			};

			// Close dialog
			closeReviewDialog();

			// Trigger re-analysis with review feedback
			await reanalyzeWithReview(currentReviewCategory);

			showUserNotification('✅ Review submitted and analysis updated');
		} catch (error) {
			console.error('❌ Review submission failed:', error);
			showUserNotification('❌ Review submission failed');
		}
	}

	async function reanalyzeWithReview(category) {
		if (reanalyzing) return;

		try {
			reanalyzing = true;
			showUserNotification('🔄 Re-analyzing based on your review...');

			// Build review context for AI
			const reviewContext = {
				category: category,
				user_feedback: reviewState[category].feedback,
				is_valid: reviewState[category].valid,
				methodology: currentMethodology,
				previous_analysis:
					aiAnalysisResult.structured_analysis?.parsed_sections?.[getCategoryKey(category)]
			};

			// Prepare re-analysis request with review context
			const analysisData = await prepareAIAnalysisData('incremental_review');
			analysisData.review_context = reviewContext;
			analysisData.incremental_update = true;

			// Get user ID for async tracking
			const userId = currentUser?.sub || 'anonymous';

			// Send to async Claude API for re-analysis with user_id parameter
			const response = await fetch(
				`/api/ai/claude/analyze-threats-async?user_id=${encodeURIComponent(userId)}`,
				{
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify(analysisData)
				}
			);

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || `HTTP ${response.status}`);
			}

			const result = await response.json();

			// Async endpoint - just notify user
			if (result.task_id) {
				showUserNotification('⏳ Re-analysis in progress... Results will update automatically');
				// Results will come via WebSocket
			} else {
				throw new Error('No task_id received from async endpoint');
			}
		} catch (error) {
			console.error('❌ Re-analysis failed:', error);
			showUserNotification(`❌ Re-analysis failed: ${error.message}`);
		} finally {
			reanalyzing = false;
		}
	}

	function updateAnalysisWithReview(newResult, category) {
		if (!aiAnalysisResult?.structured_analysis) return;

		// Update the specific category with new analysis
		const categoryKey = getCategoryKey(category);
		if (newResult.structured_analysis?.parsed_sections?.[categoryKey]) {
			aiAnalysisResult.structured_analysis.parsed_sections[categoryKey] =
				newResult.structured_analysis.parsed_sections[categoryKey];
		}

		// Update overall analysis text with changes
		if (newResult.analysis) {
			// Merge new analysis with existing (this could be more sophisticated)
			aiAnalysisResult.analysis = newResult.analysis;
		}

		// Force reactivity
		aiAnalysisResult = { ...aiAnalysisResult };
	}

	function getCategoryKey(category) {
		// Map display names to structured analysis keys
		const keyMapping = {
			Spoofing: 'spoofing',
			Tampering: 'tampering',
			Repudiation: 'repudiation',
			'Information Disclosure': 'information_disclosure',
			'Denial of Service': 'denial_of_service',
			'Elevation of Privilege': 'elevation_of_privilege',
			'Confidentiality Breach': 'confidentiality_breach',
			'Integrity Violation': 'integrity_violation',
			'Availability Disruption': 'availability_disruption',
			Linkability: 'linkability',
			Identifiability: 'identifiability',
			'Non-repudiation': 'non_repudiation',
			Detectability: 'detectability',
			'Disclosure of Information': 'disclosure_of_information',
			Unawareness: 'unawareness',
			'Non-compliance': 'non_compliance'
		};
		return keyMapping[category] || category.toLowerCase().replace(/\s+/g, '_');
	}

	// Open individual threat review dialog
	function openThreatReviewDialog(threat, category) {
		currentReviewThreat = threat;
		currentReviewCategory = category;
		reviewFeedback = threat.review_feedback || '';
		reviewValid = threat.review_valid || null;
		showReviewDialog = true;
	}

	// Review individual threat (quick action)
	async function reviewIndividualThreat(threat, category, isValid) {
		try {
			// Update the threat with review data
			threat.reviewed = true;
			threat.review_valid = isValid;
			threat.review_timestamp = new Date().toISOString();
			threat.reviewer = currentUser?.name || 'Anonymous';

			// Update in AI analysis result
			if (aiAnalysisResult?.structured_analysis?.threat_categories[category]) {
				const threats = aiAnalysisResult.structured_analysis.threat_categories[category].threats;
				const threatIndex = threats.findIndex(
					(t) => t.title === threat.title || t.what_can_be_spoofed === threat.what_can_be_spoofed
				);
				if (threatIndex !== -1) {
					threats[threatIndex] = threat;
				}
			}

			showUserNotification(`✅ Threat marked as ${isValid ? 'valid' : 'invalid'}`);
			autoSave();
		} catch (error) {
			console.error('Error reviewing threat:', error);
			showUserNotification('❌ Failed to review threat');
		}
	}

	// Submit detailed threat review from dialog
	async function submitThreatReview() {
		if (!currentReviewThreat || !currentReviewCategory || reviewValid === null) {
			showUserNotification('❌ Please select if the threat is valid or invalid');
			return;
		}

		try {
			// Update the threat with detailed review data
			currentReviewThreat.reviewed = true;
			currentReviewThreat.review_valid = reviewValid;
			currentReviewThreat.review_feedback = reviewFeedback.trim();
			currentReviewThreat.review_timestamp = new Date().toISOString();
			currentReviewThreat.reviewer = currentUser?.name || 'Anonymous';

			// Update in AI analysis result
			if (aiAnalysisResult?.structured_analysis?.threat_categories[currentReviewCategory]) {
				const threats =
					aiAnalysisResult.structured_analysis.threat_categories[currentReviewCategory].threats;
				const threatIndex = threats.findIndex(
					(t) =>
						t.title === currentReviewThreat.title ||
						t.what_can_be_spoofed === currentReviewThreat.what_can_be_spoofed
				);
				if (threatIndex !== -1) {
					threats[threatIndex] = currentReviewThreat;
				}
			}

			// Close dialog and reset state
			showReviewDialog = false;
			currentReviewThreat = null;
			currentReviewCategory = null;
			reviewFeedback = '';
			reviewValid = null;

			showUserNotification(`✅ Threat review submitted as ${reviewValid ? 'valid' : 'invalid'}`);
			autoSave();
		} catch (error) {
			console.error('Error submitting threat review:', error);
			showUserNotification('❌ Failed to submit review');
		}
	}

	// Individual AI Threat Review Functions
	function openIndividualThreatReview(threat, category, threatIndex) {
		currentThreatForReview = {
			text: threat,
			index: threatIndex,
			category: category
		};
		currentThreatCategory = category;
		threatReviewFeedback = '';
		threatReviewValid = null;
		showIndividualThreatReview = true;
	}

	function closeIndividualThreatReview() {
		showIndividualThreatReview = false;
		currentThreatForReview = null;
		currentThreatCategory = null;
		threatReviewFeedback = '';
		threatReviewValid = null;
	}

	async function submitIndividualThreatReview() {
		if (!currentThreatForReview || threatReviewValid === null) {
			showUserNotification('⚠️ Please mark the threat as valid or invalid');
			return;
		}

		try {
			// Update the threat in the analysis result
			if (aiAnalysisResult?.structured_analysis?.threat_categories?.[currentThreatCategory]) {
				const categoryData =
					aiAnalysisResult.structured_analysis.threat_categories[currentThreatCategory];

				// Initialize reviews array if it doesn't exist
				if (!categoryData.threat_reviews) {
					categoryData.threat_reviews = [];
				}

				// Add or update the review for this specific threat
				const reviewData = {
					threat_index: currentThreatForReview.index,
					threat_text: currentThreatForReview.text,
					is_valid: threatReviewValid,
					feedback: threatReviewFeedback,
					reviewed_at: new Date().toISOString(),
					reviewer: currentUser?.name || 'Anonymous'
				};

				// Remove any existing review for this threat and add the new one
				categoryData.threat_reviews = categoryData.threat_reviews.filter(
					(r) => r.threat_index !== currentThreatForReview.index
				);
				categoryData.threat_reviews.push(reviewData);

				console.log('✅ Individual threat review submitted:', reviewData);
				showUserNotification(`✅ Threat marked as ${threatReviewValid ? 'valid' : 'invalid'}`);

				// Close the review dialog
				closeIndividualThreatReview();

				// Save to database
				autoSave();
			}
		} catch (error) {
			console.error('Error submitting individual threat review:', error);
			showUserNotification('❌ Failed to submit threat review');
		}
	}

	// Helper function to get existing review for a threat
	function getThreatReview(category, threatIndex) {
		const categoryData = aiAnalysisResult?.structured_analysis?.threat_categories?.[category];
		if (!categoryData?.threat_reviews) return null;
		return categoryData.threat_reviews.find((r) => r.threat_index === threatIndex);
	}

	// Helper function to parse AI threats into individual items
	function parseAIThreats(aiThreatsText) {
		if (!aiThreatsText) return [];

		// Split only by bullet points at the start of lines (not hyphens within text!)
		const threats = aiThreatsText
			.split(/\n/) // Split by newlines first
			.map((line) => line.trim())
			.filter((line) => {
				// Only keep lines that start with bullet points
				return line.startsWith('•') || line.startsWith('-') || line.startsWith('*');
			})
			.map((line) => {
				// Remove the bullet point from the start
				return line.replace(/^[•\-\*]\s*/, '').trim();
			})
			.filter((threat) => threat.length > 10); // Filter out short/empty lines

		return threats;
	}

	// 🧠 ENHANCED PARSE RAW AI ANALYSIS INTO STRUCTURED FORMAT
	// Converts backend structured analysis or raw AI text response into frontend display format
	function parseRawAnalysisToStructured(analysisResult, methodology = 'STRIDE') {
		console.log('🔍 Parsing backend analysis data:', analysisResult);

		// Handle case where analysisResult is a complete backend response
		if (analysisResult && typeof analysisResult === 'object' && analysisResult.success) {
			console.log('✅ Backend provided structured analysis response');

			// Check if backend already parsed it with claude_ai_client.py
			if (analysisResult.parsed_sections) {
				console.log('🚀 Using rich backend parsed sections');
				return {
					// Service Overview Section
					service_overview: analysisResult.parsed_sections.service_overview || null,

					// Threat Modeling Scope Section
					scope: analysisResult.parsed_sections.scope || null,

					// Risk Rating Section
					risk_rating: analysisResult.parsed_sections.risk_rating || null,

					// Mitigation Plan Section
					mitigation_plan: analysisResult.parsed_sections.mitigation_plan || null,

					// Threat Categories (Enhanced from backend parsing)
					threat_categories:
						analysisResult.parsed_sections.threat_categories ||
						analysisResult.threat_categories ||
						{},

					// Framework-specific analysis (STRIDE/CIA/LINDDUN)
					framework_analysis:
						analysisResult.parsed_sections.stride_analysis ||
						analysisResult.parsed_sections.cia_analysis ||
						analysisResult.parsed_sections.linddun_analysis ||
						{},

					// Raw sections for fallback
					parsed_sections: analysisResult.parsed_sections
				};
			}

			// If no parsed_sections but has raw analysis, parse it
			if (analysisResult.analysis) {
				console.log('📝 Parsing raw analysis text from backend response');
				return parseRawAnalysisText(analysisResult.analysis, methodology);
			}
		}

		// Handle case where analysisResult is just raw text
		if (typeof analysisResult === 'string') {
			console.log('📝 Parsing raw analysis text string');
			return parseRawAnalysisText(analysisResult, methodology);
		}

		// Fallback for unexpected format
		console.warn('⚠️ Unexpected analysis result format, using fallback');
		return {
			threat_categories: {},
			parsed_sections: {
				raw_content: JSON.stringify(analysisResult)
			}
		};
	}

	// Helper function to parse raw text analysis
	function parseRawAnalysisText(rawAnalysis, methodology = 'STRIDE') {
		const structured = {
			threat_categories: {},
			parsed_sections: {}
		};

		// 🔍 EXTRACT SERVICE OVERVIEW SECTION
		const serviceOverviewMatch = rawAnalysis.match(/## 1\. Service Overview(.*?)(?=## 2\.|$)/s);
		if (serviceOverviewMatch) {
			const overviewText = serviceOverviewMatch[1];
			structured.parsed_sections.service_overview = {
				service_name: extractField(overviewText, /\*\*Service Name:\*\*\s*(.+?)(?=\n|$)/),
				description: extractField(overviewText, /\*\*Description:\*\*\s*(.+?)(?=\n|$)/),
				architecture_summary: extractField(
					overviewText,
					/\*\*Architecture Summary:\*\*\s*(.+?)(?=\n|$)/
				),
				assets_to_protect: extractField(overviewText, /\*\*Assets to Protect:\*\*\s*(.+?)(?=\n|$)/)
			};
		}

		// 🎯 EXTRACT THREAT MODELING SCOPE SECTION
		const scopeMatch = rawAnalysis.match(/## 2\. Threat Modeling Scope(.*?)(?=## 3\.|$)/s);
		if (scopeMatch) {
			const scopeText = scopeMatch[1];
			structured.parsed_sections.scope = {
				in_scope: extractField(scopeText, /\*\*In-Scope Components:\*\*\s*(.*?)(?=\*\*|$)/s),
				out_of_scope: extractField(
					scopeText,
					/\*\*Out-of-Scope Components:\*\*\s*(.*?)(?=\*\*|$)/s
				),
				assumptions: extractField(scopeText, /\*\*Assumptions:\*\*\s*(.*?)(?=\*\*|$)/s)
			};
		}

		// 📊 EXTRACT RISK RATING SECTION
		const riskMatch = rawAnalysis.match(/## 4\. Risk Rating(.*?)(?=## 5\.|$)/s);
		if (riskMatch) {
			const riskText = riskMatch[1];
			structured.parsed_sections.risk_rating = {
				methodology: extractField(riskText, /\*\*Methodology:\*\*\s*(.+?)(?=\n|$)/),
				top_risks: extractListItems(riskText, /\*\*Top Risks Identified:\*\*\s*((?:\d+\..*?)+)/s)
			};
		}

		// 🛡️ EXTRACT MITIGATION PLAN SECTION
		const mitigationMatch = rawAnalysis.match(
			/## 5\. (?:Privacy )?Mitigation Plan(.*?)(?=## 6\.|$)/s
		);
		if (mitigationMatch) {
			const mitigationText = mitigationMatch[1];
			structured.parsed_sections.mitigation_plan = {
				short_term: extractField(
					mitigationText,
					/\*\*Short-Term Actions.*?:\*\*\s*(.*?)(?=\*\*|$)/s
				),
				long_term: extractField(mitigationText, /\*\*Long-Term Actions.*?:\*\*\s*(.*?)(?=\*\*|$)/s)
			};
		}

		// Define category patterns based on methodology
		const categoryPatterns = {
			STRIDE: [
				'Spoofing Identity',
				'Spoofing',
				'Tampering with Data',
				'Tampering',
				'Repudiation',
				'Information Disclosure',
				'Denial of Service',
				'Elevation of Privilege'
			],
			CIA: ['Confidentiality', 'Integrity', 'Availability'],
			LINDDUN: [
				'Linkability',
				'Identifiability',
				'Non-repudiation',
				'Detectability',
				'Disclosure of Information',
				'Unawareness',
				'Non-compliance'
			]
		};

		const categories = categoryPatterns[methodology] || categoryPatterns['STRIDE'];

		try {
			// Split analysis into sections
			const sections = rawAnalysis.split(/(?=###?\s*\d+\.\d+\s*|###?\s*[A-Z])/);

			for (const section of sections) {
				if (!section.trim()) continue;

				// Find which category this section belongs to
				const categoryMatch = categories.find(
					(cat) =>
						section.toLowerCase().includes(cat.toLowerCase()) ||
						section.toLowerCase().includes(cat.replace(/\s+/g, '').toLowerCase())
				);

				if (categoryMatch) {
					const categoryKey = categoryMatch.replace(/\s+/g, '_').toLowerCase();

					// Extract different threat types from the section
					const threatData = {
						threat_assessment: '',
						user_threats: '',
						ai_threats: '',
						mitigations: ''
					};

					// Parse threat assessment
					const assessmentMatch = section.match(/\*\*Threat Assessment:\*\*\s*(.*?)(?=\*\*|$)/s);
					if (assessmentMatch) {
						threatData.threat_assessment = assessmentMatch[1].trim();
					}

					// Parse user identified threats
					const userThreatsMatch = section.match(
						/\*\*✓ User Identified Threats\*\*\s*(.*?)(?=\*\*🔍|$)/s
					);
					if (userThreatsMatch) {
						threatData.user_threats = userThreatsMatch[1].trim();
					}

					// Parse AI validation & opinion
					const aiValidationMatch = section.match(
						/\*\*🔍 AI Validation & Opinion\*\*\s*(.*?)(?=\*\*🤖|$)/s
					);
					if (aiValidationMatch) {
						threatData.ai_validation = aiValidationMatch[1].trim();
					}

					// Parse AI suggested threats
					const aiThreatsMatch = section.match(
						/\*\*🤖 AI Suggested Threats\*\*\s*(.*?)(?=\*\*🛡️|$)/s
					);
					if (aiThreatsMatch) {
						threatData.ai_threats = aiThreatsMatch[1].trim();
					}

					// Parse mitigations
					const mitigationsMatch = section.match(
						/\*\*🛡️ Recommended Mitigations\*\*\s*(.*?)(?=\*\*|###|$)/s
					);
					if (mitigationsMatch) {
						threatData.mitigations = mitigationsMatch[1].trim();
					}

					structured.threat_categories[categoryKey] = threatData;
				}
			}

			console.log('✅ Successfully parsed raw analysis into structured format');
			return structured;
		} catch (error) {
			console.error('❌ Error parsing raw analysis:', error);

			// Fallback: return minimal structure to avoid breaking
			return {
				threat_categories: {},
				parsed_sections: {
					raw_content: rawAnalysis
				}
			};
		}
	}

	// Helper function to extract a field from text using regex
	function extractField(text, pattern) {
		const match = text.match(pattern);
		return match ? match[1].trim() : '';
	}

	// Helper function to extract numbered list items
	function extractListItems(text, pattern) {
		const match = text.match(pattern);
		if (match) {
			const itemsText = match[1];
			const items = itemsText.match(/\d+\.\s*(.+?)(?=\d+\.|$)/g);
			return items ? items.map((item) => item.replace(/^\d+\.\s*/, '').trim()) : [];
		}
		return [];
	}

	// 🚀 TRIGGER AI ANALYSIS
	// Main function to request AI analysis from Claude

	// Load a past analysis and display it in the AI panel
	async function loadPastAIAnalysis(analysisEntry) {
		try {
			// ✅ Database returns analysis object directly, not wrapped in .result
			showAIResult(analysisEntry);
			showAIAnalysisPanel = true;
			showAnalysisHistory = false;

			showUserNotification('📊 Past analysis loaded successfully');
			console.log('📊 Loaded past analysis:', analysisEntry);
		} catch (error) {
			console.error('❌ Failed to load past analysis:', error);
			showUserNotification('❌ Failed to load past analysis');
		}
	}

	// Delete a past analysis
	async function deletePastAIAnalysis(analysisEntry) {
		try {
			console.log('🗑️ Attempting to delete analysis:', analysisEntry.id);

			// Delete from database first
			const response = await fetch(
				`${API_BASE_URL}/api/threat-modeling/models/${modelId}/analyses/${analysisEntry.id}`,
				{
					method: 'DELETE'
				}
			);

			if (!response.ok) {
				throw new Error('Failed to delete analysis from database');
			}

			console.log('✅ Successfully deleted analysis from database');

			// Remove from local history array after successful database deletion
			const originalLength = analysisHistory.length;
			analysisHistory = analysisHistory.filter((entry) => entry.id !== analysisEntry.id);

			console.log(`📊 Removed from local history: ${originalLength} -> ${analysisHistory.length}`);

			// Force Svelte reactivity
			analysisHistory = [...analysisHistory];

			showUserNotification('🗑️ Analysis deleted successfully');
		} catch (error) {
			console.error('❌ Failed to delete analysis:', error);
			showUserNotification('❌ Failed to delete analysis: ' + error.message);
		}
	}

	// Import threat model from JSON
	async function handleJSONImport(event) {
		const file = event.target.files[0];
		if (!file) return;

		try {
			const fileContent = await file.text();
			const importedData = JSON.parse(fileContent);

			// Validate the imported data structure
			if (!importedData.canvas || !importedData.metadata) {
				throw new Error('Invalid threat model file format');
			}

			// Confirm import with user
			const confirmImport = confirm(
				`Import threat model: "${importedData.metadata.name}"?\n\n` +
					`This will replace the current model data.\n` +
					`Methodology: ${importedData.metadata.methodology || 'Unknown'}\n` +
					`Export Date: ${importedData.metadata.exportDate ? new Date(importedData.metadata.exportDate).toLocaleDateString() : 'Unknown'}`
			);

			if (!confirmImport) {
				// Reset file input
				event.target.value = '';
				return;
			}

			// Import the canvas data
			canvasData.set({
				elements: importedData.canvas.elements || [],
				connections: importedData.canvas.connections || [],
				threats: importedData.canvas.threats || [],
				metadata: importedData.canvas.metadata || { zoom: 1.0, panX: 0, panY: 0 }
			});

			// Update model metadata if available
			if (importedData.metadata.name && modelData) {
				modelData.name = importedData.metadata.name;
				modelData.description = importedData.metadata.description || '';
			}

			// Re-render the canvas
			renderCanvas();

			// Auto-save the imported data
			await saveCanvas();

			showUserNotification(`✅ Threat model "${importedData.metadata.name}" imported successfully`);
			console.log('📂 Threat model imported from JSON:', importedData);
		} catch (error) {
			console.error('❌ Import failed:', error);
			showUserNotification('❌ Failed to import threat model: ' + error.message);
		}

		// Reset file input for future imports
		event.target.value = '';
	}

	// 📄 HANDLE DOCUMENT UPLOAD FOR AI ANALYSIS
	async function handleDocumentUpload(event) {
		const file = event.target.files[0];
		if (!file) return;

		try {
			uploadingDocument = true;
			showUserNotification('📄 Uploading document for AI analysis...');
			console.log('📄 Uploading document:', file.name);

			// Create form data for document upload
			const formData = new FormData();
			formData.append('file', file);

			// Upload document to the backend
			const response = await fetch(
				`${API_BASE_URL}/api/threat-modeling/models/${modelId}/upload-document`,
				{
					method: 'POST',
					body: formData
				}
			);

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));

				// Show specific message for irrelevant documents
				if (errorData.detail && errorData.detail.includes('unrelated to threat modeling')) {
					throw new Error(
						`❌ Document not suitable for threat modeling:\n\n${errorData.detail}\n\nPlease upload documents like:\n• System architecture diagrams\n• Technical specifications\n• Security requirements\n• API documentation\n• Infrastructure documentation`
					);
				}

				throw new Error(errorData.detail || `Upload failed: ${response.status}`);
			}

			const result = await response.json();
			console.log('✅ Document uploaded successfully:', result);
			console.log('🔍 Debug - Upload result structure:', {
				hasDocumentAnalysis: !!result.document_analysis,
				documentAnalysisKeys: result.document_analysis ? Object.keys(result.document_analysis) : [],
				hasExtractedText: !!result.document_analysis?.extracted_text,
				extractedTextLength: result.document_analysis?.extracted_text?.length || 0
			});

			// Update model data with document analysis
			modelData.document_analysis = result.document_analysis;
			modelData.document_content = result.document_analysis?.extracted_text || ''; // Also store for backward compatibility
			modelData.document_file_name = file.name;
			modelData.document_upload_date = new Date().toISOString();

			console.log('🔍 Debug - Updated modelData:', {
				hasDocumentAnalysis: !!modelData.document_analysis,
				hasExtractedText: !!modelData?.document_analysis?.extracted_text,
				extractedTextLength: modelData?.document_analysis?.extracted_text?.length || 0
			});

			showUserNotification('✅ Document uploaded and analyzed successfully!');

			// Reset file input
			event.target.value = '';
		} catch (error) {
			console.error('❌ Document upload failed:', error);
			showUserNotification(`❌ Document upload failed: ${error.message}`);
		} finally {
			uploadingDocument = false;
		}
	}

	// 📄 EXPORT AI ANALYSIS TO PDF
	async function exportAIAnalysisToPDF() {
		try {
			showUserNotification('🤖 Getting current AI analysis for PDF...');
			console.log('📄 Exporting AI analysis to PDF...');

			// Get fresh AI analysis with current canvas state
			let analysisData;

			// Check if we have recent AI analysis result
			if (aiAnalysisResult && aiAnalysisResult.timestamp) {
				const analysisAge = Date.now() - new Date(aiAnalysisResult.timestamp).getTime();
				// Use cached result if less than 5 minutes old
				if (analysisAge < 5 * 60 * 1000) {
					analysisData = aiAnalysisResult;
					console.log('📊 Using recent AI analysis result');
				} else {
					console.log('📊 AI analysis is stale, getting fresh analysis...');
					analysisData = await performFreshAIAnalysis();
				}
			} else {
				console.log('📊 No AI analysis found, performing fresh analysis...');
				analysisData = await performFreshAIAnalysis();
			}

			if (!analysisData) {
				showUserNotification('❌ Unable to get AI analysis for PDF export');
				return;
			}

			showUserNotification('📄 Generating PDF with current analysis...');

			// Create comprehensive PDF data with current canvas state
			const pdfData = {
				analysis: analysisData,
				model_info: {
					name: modelData?.name || 'Untitled Threat Model',
					description: modelData?.description || '',
					methodology: currentMethodology,
					components_count: $canvasData.elements.length,
					connections_count: $canvasData.connections.length,
					threats_count: $canvasData.threats.length
				},
				export_date: new Date().toISOString()
			};

			// Add current diagram image
			if ($canvasData.elements.length > 0) {
				try {
					pdfData.diagram_image = await exportCanvasForAI();
					console.log('📸 Diagram image added to PDF export');
				} catch (error) {
					console.warn('⚠️ Could not include diagram in PDF:', error);
				}
			}

			// Try the alternative base64 URL endpoint first to avoid CORS issues
			try {
				console.log('📄 Attempting PDF export via base64 URL endpoint...');
				const response = await fetch(`${API_BASE_URL}/api/ai/claude/export-pdf-url`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify(pdfData)
				});

				if (response.ok) {
					const result = await response.json();
					if (result.success && result.download_url) {
						// Download using the base64 URL
						const a = document.createElement('a');
						a.href = result.download_url;
						a.download = result.filename;
						document.body.appendChild(a);
						a.click();
						document.body.removeChild(a);

						showUserNotification('✅ AI analysis exported as PDF successfully!');
						console.log('✅ PDF export completed via base64 URL');
						return;
					}
				}
			} catch (urlError) {
				console.log('📄 Base64 URL method failed, trying direct download...', urlError);
			}

			// Fallback to direct download method
			const response = await fetch(`${API_BASE_URL}/api/ai/claude/export-pdf`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(pdfData)
			});

			if (!response.ok) {
				throw new Error(`PDF generation failed: ${response.status}`);
			}

			// Download the PDF file
			const blob = await response.blob();
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `${modelData?.name || 'threat_model'}_AI_Analysis_${new Date().toISOString().split('T')[0]}.pdf`;
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
			document.body.removeChild(a);

			showUserNotification('✅ AI analysis exported as PDF successfully!');
			console.log('✅ PDF export completed');
		} catch (error) {
			console.error('❌ PDF export failed:', error);
			showUserNotification(`❌ PDF export failed: ${error.message}`);
		}
	}

	// Helper function to perform fresh AI analysis
	async function performFreshAIAnalysis() {
		try {
			console.log('🤖 Performing fresh AI analysis...');
			console.log('🔍 Debug - modelData structure:', {
				hasModelData: !!modelData,
				hasDocumentAnalysis: !!modelData?.document_analysis,
				documentAnalysisKeys: modelData?.document_analysis
					? Object.keys(modelData.document_analysis)
					: [],
				hasExtractedText: !!modelData?.document_analysis?.extracted_text,
				documentFileName: modelData?.document_file_name,
				documentUploadDate: modelData?.document_upload_date
			});

			// Prepare current canvas data for AI analysis
			const documentText = modelData?.document_analysis?.extracted_text || '';
			console.log(
				'📄 Document text for AI analysis:',
				documentText ? `${documentText.length} characters` : 'No document content'
			);

			if (documentText) {
				console.log('📄 Document preview:', documentText.substring(0, 200) + '...');
			}

			const analysisRequest = {
				model_id: modelId,
				model_name: modelData?.name || 'Untitled',
				components: $canvasData.elements.map((element) => ({
					id: element.id,
					type: element.type,
					name: element.name || element.type,
					user_label: element.userLabel || element.name || element.type,
					position: { x: element.x, y: element.y },
					size: { width: element.width || 120, height: element.height || 60 },
					properties: element.properties || {}
				})),
				connections: $canvasData.connections.map((conn) => ({
					id: conn.id,
					source: conn.source,
					target: conn.target,
					label: conn.label || ''
				})),
				methodology: currentMethodology,
				analysis_type: 'comprehensive',
				document_text: documentText,
				diagram_image: await exportCanvasForAI()
			};

			// Get user ID for async tracking
			const userId = currentUser?.sub || 'anonymous';

			const response = await fetch(
				`/api/ai/claude/analyze-threats-async?user_id=${encodeURIComponent(userId)}`,
				{
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify(analysisRequest)
				}
			);

			if (!response.ok) {
				throw new Error(`AI analysis failed: ${response.status}`);
			}

			const result = await response.json();
			if (result.task_id) {
				console.log(`🤖 Fresh AI analysis queued: ${result.task_id}`);
				showUserNotification('⏳ AI analysis in progress...');
				// Will be delivered via WebSocket
				return { success: true, task_id: result.task_id };
			} else {
				throw new Error('No task_id received from async endpoint');
			}
		} catch (error) {
			console.error('❌ Fresh AI analysis failed:', error);
			return null;
		}
	}
</script>

<svelte:head>
	<title>{modelData?.name || 'Threat Model'} - Canvas Editor - WithOps</title>
</svelte:head>

<svelte:window on:keydown={handleKeydown} />

<!-- Collaboration Layer -->
{#if collaborationInitialized}
	<CollaborationLayer {modelId} {currentUser} />
{/if}

<div class="tm-canvas-page">
	<!-- Header Navigation -->
	<nav class="tm-header">
		<div class="tm-header-content">
			<a href="/" class="tm-nav-brand">
				<img src="/icons/excellence_17274210.png" alt="WithOps" class="tm-brand-icon" />
				<span class="tm-brand-name">WithOps</span>
			</a>
			<div class="tm-nav-menu">
				<a href="/dashboard" class="tm-nav-link">Overview</a>
				<a href="/organizations" class="tm-nav-link">Organizations</a>
				<a href={`/github/workspace/${orgName}`} class="tm-nav-link">{orgName}</a>
				<a href={`/github/workspace/${orgName}/threat-modeling`} class="tm-nav-link">Threat Modeling</a>
				<span class="tm-nav-link active">{modelData?.name || 'Canvas'}</span>
			</div>
		</div>
	</nav>


	{#if loading}
		<!-- Loading State -->
		<div class="tm-center-state">
			<img src="/icons/excellence_17274210.png" alt="" class="tm-loader-icon" />
			<div class="tm-loader-text">LOADING THREAT MODEL CANVAS...</div>
		</div>
	{:else if error}
		<!-- Error State -->
		<div class="tm-center-state">
			<svg class="tm-error-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
				<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
			</svg>
			<h3 class="tm-error-title">Failed to Load Threat Model</h3>
			<p class="tm-error-text">{error}</p>
			<div class="tm-error-actions">
				<button on:click={loadThreatModel} class="tm-btn tm-btn-primary">Retry Connection</button>
				<button on:click={() => goto(`/github/workspace/${orgName}/threat-modeling`)} class="tm-btn tm-btn-secondary">Go Back</button>
			</div>
		</div>
	{:else}
		<!-- Action Toolbar -->
		<div class="tm-action-bar">
			<div class="tm-action-left">
				<!-- Share Collaboration -->
				{#if collaborationInitialized && currentUser}
					<ShareCollaboration {modelId} {orgName} {currentUser} />
				{/if}

				<!-- Save Status -->
				<div class="tm-save-status">
					{#if saving}
						<span class="tm-save-spinner"></span>
						<span>Saving...</span>
					{:else if lastSaved}
						<span class="tm-save-dot"></span>
						<span>Saved {lastSaved.toLocaleTimeString()}</span>
					{:else}
						<span class="tm-save-muted">Auto-save enabled</span>
					{/if}
				</div>
			</div>

			<div class="tm-action-right">
				<button
					on:click={() => (showAIAnalysisPanel = !showAIAnalysisPanel)}
					class="tm-btn tm-btn-ai {showAIAnalysisPanel ? 'active' : ''}"
					title="{showAIAnalysisPanel ? 'Hide' : 'Show'} AI analysis panel"
				>
					<span>🧠</span>
					<span>{showAIAnalysisPanel ? 'Hide AI' : 'AI Analyze'}</span>
					{#if aiAnalysisResult || analysisHistory.length > 0}
						<span class="tm-ai-dot"></span>
					{/if}
				</button>

				<button on:click={exportToJSON} class="tm-btn tm-btn-secondary" title="Export threat model as JSON">
					💾 Export
				</button>

				<button on:click={() => document.getElementById('import-json-input').click()} class="tm-btn tm-btn-secondary" title="Import threat model from JSON">
					📂 Import
				</button>

				<button on:click={() => exportDiagram('svg')} class="tm-btn tm-btn-secondary">
					📄 SVG
				</button>

				<button on:click={() => goto(`/github/workspace/${orgName}/threat-modeling`)} class="tm-btn tm-btn-secondary">
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
					Back
				</button>
			</div>
		</div>

		<!-- Hidden file input for JSON import -->
		<input
			id="import-json-input"
			type="file"
			accept=".json"
			style="display: none"
			on:change={handleJSONImport}
		/>

		<!-- Main Canvas Area with Fixed Height -->
				<div class="flex flex-1 overflow-hidden" style="height: calc(100vh - 112px);">
			<!-- Left Tools Panel - Conditional Display -->

			{#if showDrawingToolsPanel}
				<div
					class="w-75 flex-shrink-0 overflow-y-auto border-r border-gray-200 bg-white p-3 transition-all duration-300"
				>
					<div class="mb-3 flex items-center justify-between">
						<h3 class="text-sm font-semibold text-gray-900">🎨 Drawing Tools</h3>
						<button
							on:click={() => (showDrawingToolsPanel = false)}
							class="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
							title="Hide drawing tools panel"
							aria-label="Hide drawing tools panel"
						>
							<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M6 18L18 6M6 6l12 12"
								/>
							</svg>
						</button>
					</div>

					<div class="max-h-96 space-y-1 overflow-y-auto">
						{#each Object.entries(ELEMENT_TYPES) as [type, config]}
							{#if type !== 'dataflow'}
								<div
									role="button"
									tabindex="0"
									draggable="true"
									on:dragstart={(e) => onStencilDragStart(e, type)}
									on:keydown={(e) => e.key === 'Enter' && onStencilDragStart(e, type)}
									class="group flex w-full cursor-grab items-center space-x-2 rounded border border-gray-200 p-2 transition-colors duration-200 hover:bg-gray-50 active:cursor-grabbing"
									aria-label="Drag {config.label} to canvas"
									title={config.description}
								>
									<span class="flex-shrink-0 text-lg">{config.icon}</span>
									<div class="min-w-0 flex-1 text-left">
										<div class="truncate text-xs font-medium text-gray-900">{config.label}</div>
										<div
											class="truncate text-xs text-gray-500 transition-colors group-hover:text-gray-700"
										>
											{config.description.substring(0, 25)}{config.description.length > 25
												? '...'
												: ''}
										</div>
									</div>
								</div>
							{/if}
						{/each}

						<!-- 🚀 THREATDRAGON-STYLE DATAFLOW LINE -->
						<div
							role="button"
							tabindex="0"
							draggable="true"
							on:dragstart={(e) => onDataflowDragStart(e)}
							class="w-full cursor-grab rounded border-2 border-dashed border-gray-400 bg-gradient-to-r from-gray-50 to-gray-100 p-2 transition-all duration-200 hover:border-blue-500 hover:bg-blue-50 active:cursor-grabbing"
							aria-label="Drag to create data flow connection"
						>
							<div class="mb-1 flex items-center justify-center">
								<svg width="60" height="20" viewBox="0 0 60 20" class="mx-auto">
									<line
										x1="5"
										y1="10"
										x2="50"
										y2="10"
										stroke="#374151"
										stroke-width="2"
										marker-end="url(#dataflow-arrow)"
									/>
									<circle cx="5" cy="10" r="3" fill="#22C55E" />
									<circle cx="55" cy="10" r="3" fill="#3B82F6" />
									<defs>
										<marker
											id="dataflow-arrow"
											viewBox="0 0 10 10"
											refX="8"
											refY="3"
											markerWidth="6"
											markerHeight="6"
											orient="auto"
										>
											<path d="M0,0 L0,6 L9,3 z" fill="#374151" />
										</marker>
									</defs>
								</svg>
							</div>
							<div class="text-center">
								<div class="text-xs font-medium text-gray-800">➡️ Data Flow</div>
							</div>
						</div>
					</div>
				</div>
			{/if}

			<!-- Canvas Area - Dynamic width based on panels -->
			<div class="relative min-w-0 flex-1 transition-all duration-300" style="min-width: 80px;">
				<!-- Canvas Toggle Button - Show when tools panel is hidden -->
				{#if !showDrawingToolsPanel}
					<div class="absolute top-4 left-4 z-10">
						<button
							on:click={() => (showDrawingToolsPanel = true)}
							class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm transition-all duration-200 hover:bg-gray-50 hover:shadow-md"
							title="Show drawing tools panel"
						>
							<div class="flex items-center space-x-2">
								<span>🎨</span>
								<span>Tools</span>
							</div>
						</button>
					</div>
				{/if}

				<div
					bind:this={canvasContainer}
					class="h-full w-full bg-gray-50"
					style="height: calc(100vh - 80px); min-height: 600px;"
					on:drop={onCanvasDrop}
					on:dragover={onCanvasDragOver}
					on:dragleave={onCanvasDragLeave}
					role="img"
					aria-label="Threat modeling canvas"
				></div>

				<!-- Text Editing Overlay -->
				{#if showTextInput}
					<div
						class="absolute z-50 rounded-lg border-2 border-blue-500 bg-white p-2 shadow-lg"
						style="left: {textEditPosition.x}px; top: {textEditPosition.y}px;"
					>
						<input
							id="text-edit-input"
							type="text"
							bind:value={editingText}
							on:keydown={handleTextEditKeydown}
							on:blur={finishTextEditing}
							class="rounded border border-gray-300 px-3 py-1 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
							placeholder="Enter text..."
							style="min-width: 120px;"
						/>
						<div class="mt-1 text-xs text-gray-500">Press Enter to save, Escape to cancel</div>
					</div>
				{/if}
			</div>

			<!-- Right Properties Panel - Unified for Elements and Connections -->
			{#if $selectedElement || $selectedConnection}
				{@const selectedItem = $selectedElement || $selectedConnection}
				{@const isConnection = !!$selectedConnection}
				<div
					class="flex w-100 flex-shrink-0 flex-col border-l border-gray-200 bg-white"
					style="height: calc(100vh - 80px);"
				>
					<div class="flex-shrink-0 p-3">
						<div class="mb-3 flex items-center justify-between">
							<h3 class="text-sm font-semibold text-gray-900">
								{#if isConnection}
									🔗 Connection Properties
								{:else}
									📊 Element Properties
								{/if}
							</h3>
							<div class="flex space-x-1">
								<button
									on:click={() => {
										console.log('🟡 Properties panel Add Threats button clicked!');
										console.log('🟡 selectedItem:', selectedItem);
										console.log('🟡 $selectedElement:', $selectedElement);
										console.log('🟡 $selectedConnection:', $selectedConnection);
										openThreatDialog(selectedItem);
									}}
									class="rounded border border-blue-300 px-3 py-1 text-sm font-medium text-blue-600 hover:bg-blue-50 hover:text-blue-700"
									title="Add security threats to this {isConnection ? 'connection' : 'component'}"
								>
									🛡️ Add Threats
								</button>
								<button
									on:click={isConnection ? deleteSelectedConnection : deleteSelectedElement}
									class="rounded border border-red-600 bg-red-600 px-2 py-1 text-sm font-medium text-white hover:bg-red-700"
									title="Delete {isConnection ? 'connection' : 'element'}"
								>
									🗑️ Delete
								</button>
								<button
									on:click={() => {
										selectedElement.set(null);
										selectedConnection.set(null);
									}}
									class="rounded border border-gray-300 px-2 py-1 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-700"
									title="Close properties panel"
								>
									✖️ Cancel
								</button>
							</div>
						</div>
					</div>

					<div class="flex-1 overflow-y-auto p-3 pt-0">
						<div class="space-y-4">
							<div>
								<label for="item-name" class="mb-1 block text-sm font-medium text-gray-700"
									>Name</label
								>
								<input
									id="item-name"
									type="text"
									bind:value={selectedItem.name}
									on:input={() => {
										renderCanvas();
										autoSave();
									}}
									class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
								/>
							</div>

							{#if !isConnection}
								<div>
									<label
										for="element-description"
										class="mb-1 block text-sm font-medium text-gray-700">Description</label
									>
									<textarea
										id="element-description"
										bind:value={selectedItem.properties.description}
										on:input={autoSave}
										rows="3"
										class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
										placeholder="Describe this element..."
									></textarea>
								</div>
							{/if}

							{#if !isConnection}
								<div>
									<label class="flex items-center space-x-2">
										<input
											type="checkbox"
											bind:checked={selectedItem.properties.outOfScope}
											on:change={autoSave}
											class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
										/>
										<span class="text-sm font-medium text-gray-700">Out of Scope</span>
									</label>
								</div>

								{#if selectedItem.properties.outOfScope}
									<div>
										<label
											for="element-reason-out-of-scope"
											class="mb-1 block text-sm font-medium text-gray-700">Reason</label
										>
										<textarea
											id="element-reason-out-of-scope"
											bind:value={selectedItem.properties.reasonOutOfScope}
											on:input={autoSave}
											rows="2"
											class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
											placeholder="Why is this out of scope?"
										></textarea>
									</div>
								{/if}
							{/if}

							<!-- Threats Section -->
							{#if selectedItem.threats && selectedItem.threats.length > 0}
								<div class="space-y-2 border-t border-gray-200 pt-3">
									<h4 class="font-medium text-gray-900">Threats ({selectedItem.threats.length})</h4>
									{#each selectedItem.threats as threatId}
										{@const threat = $canvasData.threats.find((t) => t.id === threatId)}
										{#if threat}
											<div class="rounded-lg border border-red-200 bg-red-50 p-3">
												<div class="mb-2 flex items-start justify-between">
													<div class="flex-1">
														<div class="text-sm font-medium text-red-800">{threat.title}</div>
														<div class="mb-1 text-xs text-red-600">{threat.type}</div>

														<!-- Risk Assessment Display -->
														{#if threat.riskLevel}
															<div class="mt-1 flex items-center space-x-2">
																<div
																	class="h-3 w-3 rounded-full"
																	style="background-color: {threat.riskColor || '#EAB308'}"
																></div>
																<span
																	class="text-xs font-medium"
																	style="color: {threat.riskColor || '#EAB308'}"
																>
																	{threat.riskLevel} Risk (Score: {threat.riskScore || 'N/A'})
																</span>
															</div>
															<div class="mt-1 text-xs text-gray-600">
																Likelihood: {threat.likelihood || 'N/A'}/5 | Impact: {threat.impact ||
																	'N/A'}/5
															</div>
														{:else}
															<!-- Legacy scoring display -->
															<div class="text-xs text-gray-600">
																{threat.severity} - Score: {threat.score || 'N/A'}/10
															</div>
														{/if}
													</div>
													<div class="flex items-center space-x-1">
														<span class="rounded bg-red-100 px-2 py-1 text-xs text-red-700"
															>{threat.status}</span
														>
														<button
															on:click={() => editThreat(threat, selectedItem)}
															class="p-1 text-blue-600 hover:text-blue-700"
															title="Edit threat"
														>
															✏️
														</button>
														<button
															on:click={() => deleteThreat(threat.id, selectedItem)}
															class="p-1 text-red-600 hover:text-red-700"
															title="Delete threat"
														>
															🗑️
														</button>
													</div>
												</div>
												{#if threat.description}
													<div class="mb-2 text-xs text-gray-700">
														<strong>Description:</strong>
														{threat.description}
													</div>
												{/if}
												{#if threat.mitigation}
													<div class="text-xs text-gray-700">
														<strong>Mitigation:</strong>
														{threat.mitigation}
													</div>
												{/if}
											</div>
										{/if}
									{/each}
								</div>
							{/if}

							<div class="border-t border-gray-200 pt-3 text-xs text-gray-500">
								<div>
									Type: {isConnection ? 'Connection Line' : ELEMENT_TYPES[selectedItem.type]?.label}
								</div>
								<div>ID: {selectedItem.id}</div>
							</div>
						</div>
					</div>
				</div>
			{/if}

			<!-- RIGHT PANEL - AI-POWERED THREAT ANALYSIS (RESIZABLE) -->
			{#if showAIAnalysisPanel}
				<div
					class="relative flex flex-col overflow-hidden border-l border-slate-200 bg-white"
					style="width: {aiPanelWidth}px; height: calc(100vh - 112px);"
				>
					<!-- Resize Handle -->
					<button
						class="group absolute top-0 bottom-0 left-0 z-10 w-1 cursor-e-resize border-0 bg-slate-200 p-0 hover:bg-slate-400"
						aria-label="Resize AI panel"
						on:mousedown={startAIPanelResize}
						on:keydown={(e) => {
							if (e.key === 'ArrowLeft') {
								e.preventDefault();
								aiPanelWidth = Math.max(aiPanelMinWidth, aiPanelWidth - 20);
							} else if (e.key === 'ArrowRight') {
								e.preventDefault();
								aiPanelWidth = Math.min(aiPanelMaxWidth, aiPanelWidth + 20);
							}
						}}
						title="Drag to resize panel, or use arrow keys"
					>
						<!-- Visible resize indicator -->
						<div
							class="absolute top-1/2 left-0 h-8 w-1 -translate-y-1/2 transform bg-slate-400 opacity-0 transition-opacity group-hover:opacity-100"
						></div>
					</button>

					{#if currentAIView === 'welcome'}
						<!-- AI WELCOME VIEW -->
						<div class="flex h-full flex-col">
							<!-- Welcome Header -->
							<div
								class="flex flex-shrink-0 items-center justify-between border-b border-slate-200 bg-gradient-to-r from-blue-50 to-purple-50 p-6"
							>
								<div class="flex items-center gap-3">
									<div
										class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 shadow-lg"
									>
										<span class="text-lg text-white">🤖</span>
									</div>
									<div>
										<h2 class="text-xl font-bold text-slate-900">AI-Powered Threat Analysis</h2>
										<p class="text-sm text-slate-600">
											Get comprehensive security insights from Claude AI
										</p>
									</div>
								</div>
								<button
									on:click={() => (showAIAnalysisPanel = false)}
									class="rounded-lg p-2 text-slate-500 transition-colors hover:bg-white/50 hover:text-slate-700"
								>
									✕
								</button>
							</div>

							<!-- Welcome Content -->
							<div class="flex-1 space-y-6 overflow-y-auto p-6">
								<!-- Welcome Message -->
								<div
									class="rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50 to-purple-50 py-8 text-center"
								>
									<div class="mb-4 text-6xl">🎯</div>
									<h3 class="mb-2 text-2xl font-bold text-slate-900">
										Welcome to AI Threat Analysis
									</h3>
									<p class="mx-auto max-w-md leading-relaxed text-slate-600">
										Upload documents or analyze your current architecture with Claude AI's advanced
										threat modeling capabilities.
									</p>
								</div>

								<!-- Action Buttons -->
								<div class="space-y-4">
									<!-- Upload Document -->
									<div
										class="rounded-lg border border-slate-200 bg-white p-4 transition-shadow hover:shadow-md"
									>
										<h4 class="mb-2 flex items-center gap-2 font-semibold text-slate-900">
											<span class="text-green-600">📄</span>
											Upload Architecture Document
										</h4>
										<p class="mb-3 text-sm text-slate-600">
											Upload design documents, architecture diagrams, or requirements for AI
											analysis
										</p>
										<input
											type="file"
											accept=".pdf,.doc,.docx,.txt,.md"
											on:change={handleDocumentUpload}
											class="hidden"
											id="ai-document-upload"
										/>
										<button
											on:click={() => document.getElementById('ai-document-upload').click()}
											class="w-full rounded-lg bg-green-600 px-4 py-3 font-medium text-white transition-colors hover:bg-green-700 {uploadingDocument
												? 'cursor-not-allowed opacity-75'
												: ''}"
											disabled={uploadingDocument}
										>
											{#if uploadingDocument}
												<div class="flex items-center justify-center space-x-2">
													<div
														class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
													></div>
													<span>Uploading & Analyzing...</span>
												</div>
											{:else}
												<div class="flex items-center justify-center space-x-2">
													<span>📁</span>
													<span>Choose Document</span>
												</div>
											{/if}
										</button>
										{#if modelData?.document_analysis?.metadata}
											<div class="mt-3 rounded-lg border border-green-200 bg-green-50 p-3">
												<div class="text-sm font-medium text-green-800">✅ Document Ready</div>
												<div class="mt-1 text-xs text-green-600">
													{modelData.document_file_name} uploaded successfully
												</div>
											</div>
										{/if}
									</div>

									<!-- Analyze Architecture -->
									<div
										class="rounded-lg border border-slate-200 bg-white p-4 transition-shadow hover:shadow-md"
									>
										<h4 class="mb-2 flex items-center gap-2 font-semibold text-slate-900">
											<span class="text-purple-600">🏗️</span>
											Analyze Current Architecture
										</h4>
										<p class="mb-3 text-sm text-slate-600">
											Get AI-powered threat analysis of your current diagram components and
											connections
										</p>
										<button
											on:click={() => performAIAnalysis('comprehensive')}
											class="w-full rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-4 py-3 font-medium text-white transition-all hover:from-purple-700 hover:to-indigo-700 {aiAnalyzing
												? 'cursor-not-allowed opacity-75'
												: ''}"
											disabled={aiAnalyzing || $canvasData.elements.length === 0}
										>
											{#if aiAnalyzing}
												<div class="flex items-center justify-center space-x-2">
													<div
														class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
													></div>
													<span>Analyzing Architecture...</span>
												</div>
											{:else}
												<div class="flex items-center justify-center space-x-2">
													<span>🧠</span>
													<span>Start Analysis</span>
												</div>
											{/if}
										</button>
										{#if $canvasData.elements.length === 0}
											<div class="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
												<div class="text-sm text-amber-700">
													⚠️ Add components to your diagram first
												</div>
											</div>
										{/if}
									</div>
								</div>

								<!-- Past Analysis History Cards -->
								{#if analysisHistory.length > 0}
									<div class="space-y-4">
										<div class="flex items-center gap-3">
											<h4 class="text-lg font-semibold text-slate-900">Past Analysis History</h4>
											<span
												class="rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-800"
											>
												{analysisHistory.length} results
											</span>
										</div>

										<div class="space-y-3">
											{#each analysisHistory as analysis, index}
												<button
													type="button"
													class="group w-full cursor-pointer rounded-lg border border-slate-200 bg-white p-4 text-left transition-all hover:border-blue-300 hover:shadow-md focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
													on:click={() => loadPastAIAnalysis(analysis)}
													on:keydown={(e) => e.key === 'Enter' && loadPastAIAnalysis(analysis)}
													aria-label="Load analysis #{analysisHistory.length -
														index} from {new Date(analysis.timestamp).toLocaleDateString()}"
													title="Click to load this analysis result"
												>
													<div class="flex items-start justify-between">
														<div class="flex-1">
															<div class="mb-2 flex items-center gap-3">
																<div
																	class="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-r from-blue-600 to-purple-600"
																>
																	<span class="text-sm text-white">🤖</span>
																</div>
																<div>
																	<h5
																		class="font-semibold text-slate-900 transition-colors group-hover:text-blue-600"
																	>
																		Analysis #{analysisHistory.length - index}
																	</h5>
																	<p class="text-xs text-slate-500">
																		{new Date(analysis.timestamp).toLocaleDateString()} at {new Date(
																			analysis.timestamp
																		).toLocaleTimeString()}
																	</p>
																</div>
															</div>

															<div class="mb-3 grid grid-cols-3 gap-3">
																<div class="rounded-lg bg-slate-50 p-2 text-center">
																	<div class="text-xs text-slate-500">Method</div>
																	<div class="text-sm font-medium text-slate-900">
																		{analysis.methodology || 'STRIDE'}
																	</div>
																</div>
																<div class="rounded-lg bg-slate-50 p-2 text-center">
																	<div class="text-xs text-slate-500">Components</div>
																	<div class="text-sm font-medium text-blue-600">
																		{analysis.diagram_elements_count || 0}
																	</div>
																</div>
																<div class="rounded-lg bg-slate-50 p-2 text-center">
																	<div class="text-xs text-slate-500">Type</div>
																	<div class="text-sm font-medium text-purple-600 capitalize">
																		{analysis.analysis_type || 'comprehensive'}
																	</div>
																</div>
															</div>

															<p class="text-sm leading-relaxed text-slate-600">
																{analysis.analysis?.substring(0, 120) ||
																	'Complete threat analysis with STRIDE methodology'}...
															</p>
														</div>

														<div class="ml-4 opacity-0 transition-opacity group-hover:opacity-100">
															<div class="text-blue-600">
																<svg
																	class="h-5 w-5"
																	fill="none"
																	stroke="currentColor"
																	viewBox="0 0 24 24"
																>
																	<path
																		stroke-linecap="round"
																		stroke-linejoin="round"
																		stroke-width="2"
																		d="M9 5l7 7-7 7"
																	/>
																</svg>
															</div>
														</div>
													</div>
												</button>
											{/each}
										</div>
									</div>
								{:else if !loadingHistory}
									<div class="py-8 text-center text-slate-500">
										<div class="mb-3 text-4xl">📊</div>
										<h4 class="mb-2 font-semibold text-slate-900">No Past Analysis</h4>
										<p class="text-sm">Start your first AI analysis to see results here</p>
									</div>
								{/if}

								{#if loadingHistory}
									<div class="py-8 text-center">
										<div
											class="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"
										></div>
										<p class="text-slate-600">Loading analysis history...</p>
									</div>
								{/if}
							</div>
						</div>
					{:else if currentAIView === 'result'}
						<!-- AI RESULT VIEW -->
						<div class="flex h-full flex-col">
							<!-- Result Header -->
							<div
								class="flex flex-shrink-0 items-center justify-between border-b border-slate-200 bg-gradient-to-r from-blue-50 to-indigo-50 p-4"
							>
								<div class="flex items-center gap-3">
									<button
										on:click={showAIWelcome}
										class="rounded-lg p-2 text-slate-500 transition-colors hover:bg-white/50 hover:text-slate-700"
										title="Back to AI Welcome"
									>
										←
									</button>
									<div
										class="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600"
									>
										<span class="text-sm text-white">🤖</span>
									</div>
									<div>
										<h2 class="text-lg font-semibold text-slate-900">AI Threat Analysis Results</h2>
										<p class="text-xs text-slate-600">
											Claude AI • {aiAnalysisResult?.methodology || currentMethodology} Framework
										</p>
									</div>
								</div>
								<div class="flex items-center gap-2">
									<button
										on:click={() => {
											// Delete current analysis and go back to welcome
											if (aiAnalysisResult?.id) {
												deletePastAIAnalysis(aiAnalysisResult);
											}
											showAIWelcome();
										}}
										class="rounded-lg p-2 text-red-500 transition-colors hover:bg-red-50 hover:text-red-700"
										title="Delete this analysis"
									>
										🗑️
									</button>
									<button
										on:click={() => (showAIAnalysisPanel = false)}
										class="rounded-lg p-2 text-slate-500 transition-colors hover:bg-white/50 hover:text-slate-700"
									>
										✕
									</button>
								</div>
							</div>

							<!-- Result Content with AI Analysis -->
							<div class="min-h-0 flex-1 overflow-y-auto bg-slate-50">
								{#if aiAnalysisResult}
									<div class="space-y-6 p-6">
										<!-- Service Overview -->
										{#if aiAnalysisResult.structured_analysis?.parsed_sections?.service_overview}
											{@const overview =
												aiAnalysisResult.structured_analysis.parsed_sections.service_overview}
											<div
												class="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
											>
												<div
													class="border-b border-slate-200 bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4"
												>
													<h3 class="flex items-center gap-2 text-lg font-semibold text-slate-900">
														<span class="text-blue-600">🏗️</span>
														Service Overview
													</h3>
												</div>
												<div class="p-6">
													<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
														{#if overview.service_name}
															<div>
																<h4 class="mb-2 font-medium text-slate-700">Service Name</h4>
																<p class="text-slate-600">{overview.service_name}</p>
															</div>
														{/if}

														{#if overview.assets_to_protect}
															<div>
																<h4 class="mb-2 font-medium text-slate-700">Assets to Protect</h4>
																<p class="text-slate-600">{overview.assets_to_protect}</p>
															</div>
														{/if}

														{#if overview.description}
															<div class="lg:col-span-2">
																<h4 class="mb-2 font-medium text-slate-700">Description</h4>
																<p class="text-slate-600">{overview.description}</p>
															</div>
														{/if}

														{#if overview.architecture_summary}
															<div class="lg:col-span-2">
																<h4 class="mb-2 font-medium text-slate-700">
																	Architecture Summary
																</h4>
																<p class="text-slate-600">{overview.architecture_summary}</p>
															</div>
														{/if}
													</div>
												</div>
											</div>
										{/if}

										<!-- Threat Modeling Scope -->
										{#if aiAnalysisResult.structured_analysis?.parsed_sections?.scope}
											{@const scope = aiAnalysisResult.structured_analysis.parsed_sections.scope}
											<div
												class="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
											>
												<div
													class="border-b border-slate-200 bg-gradient-to-r from-green-50 to-emerald-50 px-6 py-4"
												>
													<h3 class="flex items-center gap-2 text-lg font-semibold text-slate-900">
														<span class="text-green-600">🎯</span>
														Threat Modeling Scope
													</h3>
												</div>
												<div class="p-6">
													<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
														{#if scope.in_scope}
															<div>
																<h4 class="mb-2 font-medium text-slate-700">In-Scope Components</h4>
																<p class="text-slate-600">{scope.in_scope}</p>
															</div>
														{/if}

														{#if scope.assumptions}
															<div>
																<h4 class="mb-2 font-medium text-slate-700">Assumptions</h4>
																<p class="text-slate-600">{scope.assumptions}</p>
															</div>
														{/if}

														{#if scope.out_of_scope}
															<div class="lg:col-span-2">
																<h4 class="mb-2 font-medium text-slate-700">
																	Out-of-Scope Components
																</h4>
																<p class="text-slate-600">{scope.out_of_scope}</p>
															</div>
														{/if}
													</div>
												</div>
											</div>
										{/if}

										<!-- Risk Rating Section -->
										{#if aiAnalysisResult.structured_analysis?.parsed_sections?.risk_rating}
											{@const riskRating =
												aiAnalysisResult.structured_analysis.parsed_sections.risk_rating}
											{#if riskRating.top_risks?.length > 0 && !riskRating.top_risks[0].includes('[') && !riskRating.top_risks[0].includes('Risk 1 with severity')}
												<div
													class="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
												>
													<div
														class="border-b border-slate-200 bg-gradient-to-r from-red-50 to-orange-50 px-6 py-4"
													>
														<h3
															class="flex items-center gap-2 text-lg font-semibold text-slate-900"
														>
															<span class="text-red-600">📊</span>
															Risk Assessment
														</h3>
													</div>
													<div class="p-6">
														<div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
															{#if riskRating.methodology && !riskRating.methodology.includes('[')}
																<div>
																	<h4 class="mb-2 font-medium text-slate-700">Methodology</h4>
																	<p class="text-slate-600">{riskRating.methodology}</p>
																</div>
															{/if}

															<div class="lg:col-span-2">
																<h4 class="mb-2 font-medium text-slate-700">
																	Top Risks Identified
																</h4>
																<ol class="list-inside list-decimal space-y-1 text-slate-600">
																	{#each riskRating.top_risks as risk}
																		<li>{risk}</li>
																	{/each}
																</ol>
															</div>
														</div>
													</div>
												</div>
											{/if}
										{/if}

										<!-- Mitigation Plan -->
										{#if aiAnalysisResult.structured_analysis?.parsed_sections?.mitigation_plan}
											{@const mitigationPlan =
												aiAnalysisResult.structured_analysis.parsed_sections.mitigation_plan}
											<div
												class="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
											>
												<div
													class="border-b border-slate-200 bg-gradient-to-r from-purple-50 to-indigo-50 px-6 py-4"
												>
													<h3 class="flex items-center gap-2 text-lg font-semibold text-slate-900">
														<span class="text-purple-600">🛡️</span>
														Mitigation Strategy
													</h3>
												</div>
												<div class="p-6">
													<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
														{#if mitigationPlan.short_term}
															<div>
																<h4 class="mb-2 font-medium text-slate-700">Short-Term Actions</h4>
																<div class="whitespace-pre-line text-slate-600">
																	{mitigationPlan.short_term}
																</div>
															</div>
														{/if}

														{#if mitigationPlan.long_term}
															<div>
																<h4 class="mb-2 font-medium text-slate-700">Long-Term Strategy</h4>
																<div class="whitespace-pre-line text-slate-600">
																	{mitigationPlan.long_term}
																</div>
															</div>
														{/if}
													</div>
												</div>
											</div>
										{/if}

										<!-- Threat Categories with Individual Review -->
										{#if aiAnalysisResult.structured_analysis?.threat_categories}
											<div
												class="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
											>
												<div
													class="border-b border-slate-200 bg-gradient-to-r from-red-50 to-orange-50 px-6 py-4"
												>
													<h3 class="flex items-center gap-2 text-lg font-semibold text-slate-900">
														<span class="text-red-600">⚠️</span>
														{aiAnalysisResult.methodology || 'STRIDE'} Threat Analysis
													</h3>
													<p class="mt-1 text-sm text-slate-600">
														Review AI-suggested threats and validate their relevance to your
														architecture
													</p>
												</div>
												<div class="space-y-6 p-6">
													{#each Object.entries(aiAnalysisResult.structured_analysis.threat_categories) as [category, data]}
														<div class="rounded-lg border border-slate-200 bg-white shadow-sm">
															<!-- Category Header -->
															<div class="border-b border-slate-200 bg-slate-50 px-6 py-4">
																<div class="flex items-center gap-3">
																	<div
																		class="flex h-8 w-8 items-center justify-center rounded-lg bg-red-600"
																	>
																		<span class="text-sm text-white"
																			>{getCategoryIcon(category)}</span
																		>
																	</div>
																	<div>
																		<h4 class="text-lg font-semibold text-slate-800 capitalize">
																			{category.replace(/_/g, ' ')}
																		</h4>
																		<p class="text-sm text-slate-600">
																			{getCategoryDescription(
																				category,
																				aiAnalysisResult.methodology || 'STRIDE'
																			)}
																		</p>
																	</div>
																</div>
															</div>

															<div class="space-y-4 p-6">
																<!-- Threat Assessment -->
																{#if data.threat_assessment}
																	<div class="rounded-lg border border-blue-200 bg-blue-50 p-4">
																		<h5
																			class="mb-2 flex items-center gap-2 font-semibold text-blue-900"
																		>
																			<span class="text-blue-600">📋</span> Assessment
																		</h5>
																		<p class="leading-relaxed text-blue-800">
																			{data.threat_assessment}
																		</p>
																	</div>
																{/if}

																<!-- User Identified Threats -->
																{#if data.user_threats}
																	<div class="rounded-lg border border-green-200 bg-green-50 p-4">
																		<h5
																			class="mb-2 flex items-center gap-2 font-semibold text-green-900"
																		>
																			<span class="text-green-600">✓</span> User Identified Threats
																		</h5>
																		<div class="leading-relaxed whitespace-pre-line text-green-800">
																			{data.user_threats}
																		</div>
																	</div>
																{/if}

																<!-- AI Validation & Opinion on User Threats -->
																{#if data.ai_validation}
																	<div
																		class="rounded-lg border border-amber-300 bg-amber-50 p-4 shadow-sm"
																	>
																		<h5
																			class="mb-3 flex items-center gap-2 font-semibold text-amber-900"
																		>
																			<span class="text-amber-600">🔍</span> AI Validation & Expert Opinion
																		</h5>
																		<div class="space-y-2 leading-relaxed text-amber-900">
																			{#each data.ai_validation
																				.split('•')
																				.filter((v) => v.trim())
																				.map((v) => v.trim()) as validation}
																				<div
																					class="flex items-start gap-2 rounded border border-amber-200 bg-white p-2"
																				>
																					{#if validation.includes('✅ Valid')}
																						<span class="flex-shrink-0 text-lg text-green-600"
																							>✅</span
																						>
																						<div class="flex-1 text-green-800">
																							{validation.replace('✅ Valid:', '').trim()}
																						</div>
																					{:else if validation.includes('⚠️ Partially Valid')}
																						<span class="flex-shrink-0 text-lg text-orange-600"
																							>⚠️</span
																						>
																						<div class="flex-1 text-orange-800">
																							{validation.replace('⚠️ Partially Valid:', '').trim()}
																						</div>
																					{:else if validation.includes('❌ Unlikely')}
																						<span class="flex-shrink-0 text-lg text-red-600"
																							>❌</span
																						>
																						<div class="flex-1 text-red-800">
																							{validation.replace('❌ Unlikely:', '').trim()}
																						</div>
																					{:else if validation.includes('💡 Enhancement')}
																						<span class="flex-shrink-0 text-lg text-blue-600"
																							>💡</span
																						>
																						<div class="flex-1 text-blue-800">
																							{validation.replace('💡 Enhancement:', '').trim()}
																						</div>
																					{:else}
																						<div class="flex-1 text-amber-800">{validation}</div>
																					{/if}
																				</div>
																			{/each}
																		</div>
																	</div>
																{/if}

																<!-- AI Suggested Threats with Individual Review -->
																{#if data.ai_threats}
																	<div class="rounded-lg border border-blue-200 bg-blue-50 p-4">
																		<h5
																			class="mb-3 flex items-center gap-2 font-semibold text-blue-900"
																		>
																			<span class="text-blue-600">🤖</span> AI Suggested Threats
																		</h5>

																		<!-- Parse and display individual threats -->
																		{#each parseAIThreats(data.ai_threats) as threat, threatIndex}
																			<div
																				class="mb-3 rounded-lg border border-blue-300 bg-white p-4 shadow-sm last:mb-0"
																			>
																				<div class="flex items-start justify-between gap-3">
																					<div class="flex-1">
																						<p class="leading-relaxed text-blue-900">{threat}</p>
																					</div>

																					<!-- Review Button -->
																					<button
																						on:click={() =>
																							openIndividualThreatReview(
																								threat,
																								category,
																								threatIndex
																							)}
																						class="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 hover:shadow-md"
																						title="Review this threat"
																					>
																						🔍 Review
																					</button>
																				</div>
																			</div>
																		{/each}
																	</div>
																{/if}

																<!-- Recommended Mitigations -->
																{#if data.mitigations}
																	<div class="rounded-lg border border-purple-200 bg-purple-50 p-4">
																		<h5
																			class="mb-2 flex items-center gap-2 font-semibold text-purple-900"
																		>
																			<span class="text-purple-600">🛡️</span> Recommended Mitigations
																		</h5>
																		<div
																			class="leading-relaxed whitespace-pre-line text-purple-800"
																		>
																			{data.mitigations}
																		</div>
																	</div>
																{/if}
															</div>
														</div>
													{/each}
												</div>
											</div>
										{/if}

										<!-- Risk Rating Section (below threat categories) -->
										{#if aiAnalysisResult.structured_analysis?.parsed_sections?.risk_rating}
											{@const riskRating =
												aiAnalysisResult.structured_analysis.parsed_sections.risk_rating}
											<div
												class="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
											>
												<div
													class="border-b border-slate-200 bg-gradient-to-r from-red-50 to-orange-50 px-6 py-4"
												>
													<h3 class="flex items-center gap-2 text-lg font-semibold text-slate-900">
														<span class="text-red-600">📊</span>
														Risk Assessment
													</h3>
												</div>
												<div class="p-6">
													<div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
														{#if riskRating.methodology}
															<div>
																<h4 class="mb-2 font-medium text-slate-700">Methodology</h4>
																<p class="text-slate-600">{riskRating.methodology}</p>
															</div>
														{/if}

														{#if riskRating.top_risks?.length > 0}
															<div class="lg:col-span-2">
																<h4 class="mb-2 font-medium text-slate-700">
																	Top Risks Identified
																</h4>
																<ol class="list-inside list-decimal space-y-1 text-slate-600">
																	{#each riskRating.top_risks as risk}
																		<li>{risk}</li>
																	{/each}
																</ol>
															</div>
														{:else}
															<div class="lg:col-span-2">
																<div class="text-sm text-slate-500 italic">
																	No risk data available from AI analysis
																</div>
															</div>
														{/if}
													</div>
												</div>
											</div>
										{/if}

										<!-- Enhanced Raw Analysis Fallback -->
										{#if !aiAnalysisResult.structured_analysis?.threat_categories && aiAnalysisResult.analysis}
											<div
												class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
											>
												<div
													class="border-b border-slate-200 bg-gradient-to-r from-yellow-50 to-orange-50 px-6 py-4"
												>
													<h3 class="flex items-center gap-3 text-xl font-bold text-slate-900">
														<div
															class="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-r from-yellow-600 to-orange-600"
														>
															<span class="text-lg text-white">⚠️</span>
														</div>
														Raw Analysis Results
														<span
															class="ml-3 rounded-full bg-yellow-100 px-3 py-1 text-sm font-medium text-yellow-800"
														>
															Basic Parsing Mode
														</span>
													</h3>
													<p class="mt-1 text-sm text-slate-600">
														Analysis completed - enhanced parsing with structured sections
														unavailable
													</p>
												</div>
												<div class="p-6">
													<div class="rounded-lg border border-slate-200 bg-slate-50 p-6">
														<pre
															class="font-mono text-sm leading-relaxed whitespace-pre-wrap text-slate-700">{aiAnalysisResult.analysis}</pre>
													</div>

													<!-- Enhancement Notice -->
													<div
														class="mt-6 rounded-xl border border-blue-200 bg-gradient-to-r from-blue-50 to-purple-50 p-5 shadow-sm"
													>
														<div class="flex items-start gap-4">
															<div
																class="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-blue-600 to-purple-600"
															>
																<span class="text-xl text-white">💡</span>
															</div>
															<div class="flex-1">
																<h4 class="mb-2 text-lg font-bold text-blue-900">
																	Unlock Enhanced Analysis Features
																</h4>
																<p class="mb-4 text-sm leading-relaxed text-blue-800">
																	Re-run the AI analysis to get structured sections with service
																	overview, scope analysis, risk ratings, mitigation plans, and
																	individual threat review capabilities.
																</p>
																<button
																	on:click={() => performAIAnalysis('comprehensive')}
																	class="flex items-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-3 text-sm font-bold text-white shadow-lg transition-all hover:from-blue-700 hover:to-purple-700 hover:shadow-xl"
																	disabled={aiAnalyzing}
																>
																	{#if aiAnalyzing}
																		<div
																			class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
																		></div>
																		<span>Re-analyzing...</span>
																	{:else}
																		<span>🔄</span>
																		<span>Re-analyze with Enhanced Parsing</span>
																	{/if}
																</button>
															</div>
														</div>
													</div>
												</div>
											</div>
										{/if}
									</div>
								{:else}
									<div class="p-8 text-center text-slate-500">
										<div class="mb-4 text-6xl">🤖</div>
										<h3 class="mb-2 text-xl font-semibold text-slate-700">
											No AI Analysis Results
										</h3>
										<p class="text-slate-600">
											Run an AI analysis to see detailed threat assessment and recommendations here.
										</p>
									</div>
								{/if}
							</div>
						</div>
					{/if}
				</div>

				<!-- Edit Threat Dialog - Bottom Docked Panel -->
				{#if $showEditThreatDialog && $editingThreat}
					<!-- Bottom Docked Panel - Slides up from bottom -->
					<div
						class="fixed right-0 bottom-0 left-0 z-50 transform border-t border-gray-300 bg-white shadow-2xl transition-transform duration-300 ease-out"
						style="max-height: 70vh;"
					>
						<!-- Panel Header - Fixed -->
						<div
							class="flex items-center justify-between border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4"
						>
							<div class="flex items-center space-x-3">
								<div
									class="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 shadow-lg"
								>
									<span class="text-lg text-white">✏️</span>
								</div>
								<div>
									<h3 class="text-lg font-semibold text-gray-900">Edit Security Threat</h3>
									<p class="text-sm text-gray-600">
										Threat ID: <span class="font-medium text-blue-600">{$editingThreat.id}</span>
									</p>
								</div>
							</div>
							<button
								on:click={() => showEditThreatDialog.set(false)}
								class="rounded-full p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
								aria-label="Close edit threat dialog"
							>
								<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M6 18L18 6M6 6l12 12"
									></path>
								</svg>
							</button>
						</div>

						<!-- Panel Content - Scrollable -->
						<div class="overflow-y-auto p-6" style="max-height: calc(70vh - 80px);">
							<form
								on:submit|preventDefault={(e) => {
									const formData = new FormData(e.target);
									updateThreat({
										title: formData.get('title'),
										type: formData.get('type'),
										status: formData.get('status'),
										severity: formData.get('severity'),
										likelihood: parseInt(formData.get('likelihood')),
										impact: parseInt(formData.get('impact')),
										description: formData.get('description'),
										mitigation: formData.get('mitigation')
									});
								}}
							>
								<!-- Form Grid Layout for Better Space Usage -->
								<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
									<!-- Left Column -->
									<div class="space-y-4">
										<div>
											<label
												for="edit-threat-title"
												class="mb-1 block text-sm font-medium text-gray-700">Title</label
											>
											<input
												id="edit-threat-title"
												name="title"
												type="text"
												value={$editingThreat.title}
												required
												class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
											/>
										</div>

										<div>
											<label
												for="edit-threat-type"
												class="mb-1 block text-sm font-medium text-gray-700">Type</label
											>
											<select
												id="edit-threat-type"
												name="type"
												class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
											>
												{#each ['Spoofing', 'Tampering', 'Repudiation', 'Information Disclosure', 'Denial of Service', 'Elevation of Privilege'] as threatType}
													<option value={threatType} selected={$editingThreat.type === threatType}
														>{threatType}</option
													>
												{/each}
											</select>
										</div>

										<!-- Risk Assessment Section -->
										<div class="rounded-lg bg-gray-50 p-4">
											<h4 class="mb-3 text-sm font-semibold text-gray-800">🎯 Risk Assessment</h4>

											<div class="grid grid-cols-2 gap-3">
												<div>
													<label
														for="edit-threat-likelihood"
														class="mb-1 block text-sm font-medium text-gray-700"
													>
														Likelihood
														<span class="text-xs text-gray-500">(Probability)</span>
													</label>
													<select
														id="edit-threat-likelihood"
														name="likelihood"
														class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
													>
														<option value="1" selected={$editingThreat.likelihood === 1}
															>Very Low (1)</option
														>
														<option value="2" selected={$editingThreat.likelihood === 2}
															>Low (2)</option
														>
														<option value="3" selected={$editingThreat.likelihood === 3}
															>Medium (3)</option
														>
														<option value="4" selected={$editingThreat.likelihood === 4}
															>High (4)</option
														>
														<option value="5" selected={$editingThreat.likelihood === 5}
															>Very High (5)</option
														>
													</select>
												</div>

												<div>
													<label
														for="edit-threat-impact"
														class="mb-1 block text-sm font-medium text-gray-700"
													>
														Impact
														<span class="text-xs text-gray-500">(Consequences)</span>
													</label>
													<select
														id="edit-threat-impact"
														name="impact"
														class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
													>
														<option value="1" selected={$editingThreat.impact === 1}
															>Very Low (1)</option
														>
														<option value="2" selected={$editingThreat.impact === 2}>Low (2)</option
														>
														<option value="3" selected={$editingThreat.impact === 3}
															>Medium (3)</option
														>
														<option value="4" selected={$editingThreat.impact === 4}
															>High (4)</option
														>
														<option value="5" selected={$editingThreat.impact === 5}
															>Very High (5)</option
														>
													</select>
												</div>
											</div>

											<div class="mt-3 rounded border border-gray-200 bg-white p-2">
												<div class="mb-1 text-xs text-gray-600">Current Risk Level:</div>
												<div class="flex items-center space-x-2">
													<div
														class="h-4 w-4 rounded-full"
														style="background-color: {$editingThreat.riskColor || '#EAB308'}"
													></div>
													<span
														class="text-sm font-medium"
														style="color: {$editingThreat.riskColor || '#EAB308'}"
													>
														{$editingThreat.riskLevel || 'Medium'} (Score: {$editingThreat.riskScore ||
															'N/A'})
													</span>
												</div>
											</div>
										</div>

										<div class="grid grid-cols-2 gap-3">
											<div>
												<label
													for="edit-threat-status"
													class="mb-1 block text-sm font-medium text-gray-700">Status</label
												>
												<select
													id="edit-threat-status"
													name="status"
													class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
												>
													<option value="Open" selected={$editingThreat.status === 'Open'}
														>Open</option
													>
													<option
														value="In Progress"
														selected={$editingThreat.status === 'In Progress'}>In Progress</option
													>
													<option value="Mitigated" selected={$editingThreat.status === 'Mitigated'}
														>Mitigated</option
													>
													<option value="Accepted" selected={$editingThreat.status === 'Accepted'}
														>Accepted</option
													>
													<option
														value="Not Applicable"
														selected={$editingThreat.status === 'Not Applicable'}
														>Not Applicable</option
													>
												</select>
											</div>

											<div>
												<label
													for="edit-threat-severity"
													class="mb-1 block text-sm font-medium text-gray-700"
													>Severity (Legacy)</label
												>
												<select
													id="edit-threat-severity"
													name="severity"
													class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
												>
													<option value="Low" selected={$editingThreat.severity === 'Low'}
														>Low</option
													>
													<option value="Medium" selected={$editingThreat.severity === 'Medium'}
														>Medium</option
													>
													<option value="High" selected={$editingThreat.severity === 'High'}
														>High</option
													>
													<option value="Critical" selected={$editingThreat.severity === 'Critical'}
														>Critical</option
													>
												</select>
											</div>
										</div>

										<div>
											<label
												for="edit-threat-score"
												class="mb-1 block text-sm font-medium text-gray-700">Score (1-10)</label
											>
											<input
												id="edit-threat-score"
												name="score"
												type="number"
												min="1"
												max="10"
												value={$editingThreat.score}
												class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
											/>
										</div>
									</div>

									<!-- Right Column -->
									<div class="space-y-4">
										<div>
											<label
												for="edit-threat-description"
												class="mb-1 block text-sm font-medium text-gray-700">Description</label
											>
											<textarea
												id="edit-threat-description"
												name="description"
												rows="4"
												class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
												placeholder="Describe the threat...">{$editingThreat.description}</textarea
											>
										</div>

										<div>
											<label
												for="edit-threat-mitigation"
												class="mb-1 block text-sm font-medium text-gray-700">Mitigation</label
											>
											<textarea
												id="edit-threat-mitigation"
												name="mitigation"
												rows="4"
												class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
												placeholder="How to mitigate this threat..."
												>{$editingThreat.mitigation}</textarea
											>
										</div>

										<!-- Action Buttons -->
										<div class="flex justify-end space-x-3 pt-4">
											<button
												type="button"
												on:click={() => showEditThreatDialog.set(false)}
												class="rounded-md border border-gray-300 bg-gray-100 px-6 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-200"
											>
												Cancel
											</button>
											<button
												type="submit"
												class="rounded-md border border-transparent bg-blue-600 px-6 py-2 text-sm font-medium text-white shadow-lg transition-colors hover:bg-blue-700"
											>
												Update Threat
											</button>
										</div>
									</div>
								</div>
							</form>
						</div>
					</div>
				{/if}

				<!-- Review Dialog - Professional Review Interface -->
				{#if showReviewDialog && currentReviewThreat}
					<div
						class="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black backdrop-blur-sm"
					>
						<div
							class="mx-4 max-h-[90vh] w-full max-w-2xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-2xl"
						>
							<!-- Review Header -->
							<div
								class="border-b border-slate-200 bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4"
							>
								<div class="flex items-center justify-between">
									<div class="flex items-center gap-3">
										<div
											class="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600"
										>
											<span class="text-lg text-white">🔍</span>
										</div>
										<div>
											<h3 class="text-lg font-semibold text-slate-900">Review Threat</h3>
											<p class="text-sm text-slate-600">
												{currentReviewCategory} • Validation Required
											</p>
										</div>
									</div>
									<button
										on:click={() => {
											showReviewDialog = false;
											currentReviewThreat = null;
											currentReviewCategory = null;
											reviewFeedback = '';
											reviewValid = null;
										}}
										class="rounded-lg p-2 text-slate-500 transition-colors hover:bg-white/50 hover:text-slate-700"
									>
										✕
									</button>
								</div>
							</div>

							<!-- Review Content -->
							<div class="max-h-[60vh] overflow-y-auto p-6">
								<!-- Threat Details -->
								<div class="mb-6">
									<h4 class="text-md mb-3 font-semibold text-slate-900">Threat Details</h4>
									<div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
										<div class="space-y-3">
											<div>
												<div class="mb-1 text-sm font-medium text-slate-700">Title</div>
												<div class="text-sm text-slate-900">
													{currentReviewThreat.title ||
														currentReviewThreat.what_can_be_spoofed ||
														'Security Threat'}
												</div>
											</div>
											<div>
												<div class="mb-1 text-sm font-medium text-slate-700">Description</div>
												<div class="text-sm leading-relaxed text-slate-600">
													{currentReviewThreat.description ||
														currentReviewThreat.possible_scenarios ||
														currentReviewThreat.scenarios ||
														'No description available'}
												</div>
											</div>
											{#if currentReviewThreat.impact && currentReviewThreat.likelihood}
												<div
													class="mt-3 grid grid-cols-3 gap-4 rounded-lg border border-slate-200 bg-white p-3"
												>
													<div class="text-center">
														<div class="mb-1 text-xs text-slate-500">Impact</div>
														<div class="text-sm font-bold text-red-600">
															{currentReviewThreat.impact}/5
														</div>
													</div>
													<div class="text-center">
														<div class="mb-1 text-xs text-slate-500">Likelihood</div>
														<div class="text-sm font-bold text-orange-600">
															{currentReviewThreat.likelihood}/5
														</div>
													</div>
													<div class="text-center">
														<div class="mb-1 text-xs text-slate-500">Risk Score</div>
														<div class="text-sm font-bold text-purple-600">
															{currentReviewThreat.impact * currentReviewThreat.likelihood}/25
														</div>
													</div>
												</div>
											{/if}
										</div>
									</div>
								</div>

								<!-- Validation Options -->
								<div class="mb-6">
									<h4 class="text-md mb-3 font-semibold text-slate-900">Is this threat valid?</h4>
									<div class="flex gap-3">
										<button
											on:click={() => (reviewValid = true)}
											class="flex-1 rounded-lg border border-green-300 px-4 py-3 transition-colors hover:bg-green-50 {reviewValid ===
											true
												? 'border-green-500 bg-green-50 ring-2 ring-green-200'
												: 'bg-white'}"
										>
											<div class="flex items-center justify-center gap-2">
												<span class="text-lg text-green-600">✅</span>
												<span class="font-medium text-green-700">Valid Threat</span>
											</div>
											<p class="mt-1 text-xs text-green-600">
												This threat is legitimate and should be addressed
											</p>
										</button>

										<button
											on:click={() => (reviewValid = false)}
											class="flex-1 rounded-lg border border-red-300 px-4 py-3 transition-colors hover:bg-red-50 {reviewValid ===
											false
												? 'border-red-500 bg-red-50 ring-2 ring-red-200'
												: 'bg-white'}"
										>
											<div class="flex items-center justify-center gap-2">
												<span class="text-lg text-red-600">❌</span>
												<span class="font-medium text-red-700">Invalid Threat</span>
											</div>
											<p class="mt-1 text-xs text-red-600">
												This threat is not applicable or incorrect
											</p>
										</button>
									</div>
								</div>

								<!-- Review Feedback -->
								<div class="mb-6">
									<label
										for="review-feedback"
										class="text-md mb-3 block font-semibold text-slate-900"
									>
										Review Comments
										<span class="text-sm font-normal text-slate-600">(Optional)</span>
									</label>
									<textarea
										id="review-feedback"
										bind:value={reviewFeedback}
										placeholder="Provide additional context, reasoning, or recommendations for this threat assessment..."
										class="h-24 w-full resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
									></textarea>
									<p class="mt-1 text-xs text-slate-500">
										Your feedback helps improve AI analysis accuracy and provides context for team
										members.
									</p>
								</div>
							</div>

							<!-- Review Actions -->
							<div class="border-t border-slate-200 bg-slate-50 px-6 py-4">
								<div class="flex items-center justify-between">
									<div class="text-xs text-slate-500">
										{#if currentReviewThreat.reviewed}
											Previously reviewed • Click submit to update
										{:else}
											First time review • Help improve AI accuracy
										{/if}
									</div>
									<div class="flex items-center gap-3">
										<button
											on:click={() => {
												showReviewDialog = false;
												currentReviewThreat = null;
												currentReviewCategory = null;
												reviewFeedback = '';
												reviewValid = null;
											}}
											class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
										>
											Cancel
										</button>
										<button
											on:click={submitThreatReview}
											disabled={reviewValid === null}
											class="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white shadow-lg transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
										>
											Submit Review
										</button>
									</div>
								</div>
							</div>
						</div>
					</div>
				{/if}
			{/if}
		</div>

		<!-- Enhanced User Notification with Icons and Progress -->
		{#if showNotification}
			<div class="fixed top-4 right-4 z-50 translate-x-0 transform transition-all duration-300">
				<div
					class="flex max-w-md items-center space-x-3 rounded-lg border border-gray-200 bg-white px-6 py-4 shadow-lg"
				>
					<!-- Dynamic Icon based on notification content -->
					<div class="flex-shrink-0">
						{#if notification.includes('🤖')}
							<div
								class="flex h-8 w-8 animate-pulse items-center justify-center rounded-full bg-gradient-to-r from-purple-600 to-indigo-600"
							>
								<span class="text-sm text-white">🤖</span>
							</div>
						{:else if notification.includes('✅') || notification.includes('🎉')}
							<div class="flex h-8 w-8 items-center justify-center rounded-full bg-green-500">
								<span class="text-sm text-white">✅</span>
							</div>
						{:else if notification.includes('❌')}
							<div class="flex h-8 w-8 items-center justify-center rounded-full bg-red-500">
								<span class="text-sm text-white">❌</span>
							</div>
						{:else if notification.includes('📄')}
							<div class="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500">
								<span class="text-sm text-white">📄</span>
							</div>
						{:else}
							<div class="flex h-8 w-8 items-center justify-center rounded-full bg-gray-500">
								<span class="text-sm text-white">ℹ️</span>
							</div>
						{/if}
					</div>

					<!-- Notification Content -->
					<div class="min-w-0 flex-1">
						<p class="text-sm font-medium break-words text-gray-900">{notification}</p>
						{#if notification.includes('🤖') && aiAnalyzing}
							<div class="mt-2">
								<div class="h-1.5 w-full rounded-full bg-gray-200">
									<div
										class="h-1.5 animate-pulse rounded-full bg-gradient-to-r from-purple-600 to-indigo-600"
										style="width: 75%"
									></div>
								</div>
								<p class="mt-1 text-xs text-gray-500">This may take 10-30 seconds...</p>
							</div>
						{/if}
					</div>

					<!-- Close Button -->
					<button
						on:click={() => (showNotification = false)}
						class="flex-shrink-0 text-gray-400 transition-colors hover:text-gray-600"
						aria-label="Close notification"
					>
						<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
					</button>
				</div>
			</div>
		{/if}
	{/if}
</div>

<!-- Edit Threat Dialog - Bottom Docked Panel -->
{#if $showEditThreatDialog && $editingThreat}
	<!-- Bottom Docked Panel - Slides up from bottom -->
	<div
		class="fixed right-0 bottom-0 left-0 z-50 transform border-t border-gray-300 bg-white shadow-2xl transition-transform duration-300 ease-out"
		style="max-height: 70vh;"
	>
		<!-- Panel Header - Fixed -->
		<div
			class="flex items-center justify-between border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4"
		>
			<div class="flex items-center space-x-3">
				<div
					class="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 shadow-lg"
				>
					<span class="text-lg text-white">✏️</span>
				</div>
				<div>
					<h3 class="text-lg font-semibold text-gray-900">Edit Security Threat</h3>
					<p class="text-sm text-gray-600">
						Threat ID: <span class="font-medium text-blue-600">{$editingThreat.id}</span>
					</p>
				</div>
			</div>
			<button
				on:click={() => showEditThreatDialog.set(false)}
				class="rounded-full p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
				aria-label="Close edit threat dialog"
			>
				<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M6 18L18 6M6 6l12 12"
					></path>
				</svg>
			</button>
		</div>

		<!-- Panel Content - Scrollable -->
		<div class="overflow-y-auto p-6" style="max-height: calc(70vh - 80px);">
			<form
				on:submit|preventDefault={(e) => {
					const formData = new FormData(e.target);
					updateThreat({
						title: formData.get('title'),
						type: formData.get('type'),
						status: formData.get('status'),
						severity: formData.get('severity'),
						likelihood: parseInt(formData.get('likelihood')),
						impact: parseInt(formData.get('impact')),
						description: formData.get('description'),
						mitigation: formData.get('mitigation')
					});
				}}
			>
				<div class="space-y-4">
					<div class="grid grid-cols-2 gap-4">
						<div>
							<label for="edit-threat-title" class="mb-1 block text-sm font-medium text-gray-700"
								>Title</label
							>
							<input
								id="edit-threat-title"
								name="title"
								type="text"
								value={$editingThreat.title}
								class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
								required
							/>
						</div>

						<div>
							<label for="edit-threat-type" class="mb-1 block text-sm font-medium text-gray-700"
								>Type</label
							>
							<select
								id="edit-threat-type"
								name="type"
								class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
							>
								{#each Object.keys(THREAT_METHODOLOGIES[currentMethodology].threats) as threatType}
									<option value={threatType} selected={$editingThreat.type === threatType}
										>{threatType}</option
									>
								{/each}
							</select>
						</div>
					</div>

					<!-- Risk Assessment Section -->
					<div class="rounded-lg bg-gray-50 p-4">
						<h4 class="mb-3 text-sm font-semibold text-gray-800">🎯 Risk Assessment</h4>

						<div class="grid grid-cols-2 gap-3">
							<div>
								<label
									for="edit-threat-likelihood"
									class="mb-1 block text-xs font-medium text-gray-700">Likelihood (1-5)</label
								>
								<select
									id="edit-threat-likelihood"
									name="likelihood"
									class="w-full rounded border border-gray-300 px-2 py-1 text-sm text-slate-900 focus:ring-1 focus:ring-red-500 focus:outline-none"
								>
									{#each [1, 2, 3, 4, 5] as level}
										<option value={level} selected={$editingThreat.likelihood == level}
											>{level}</option
										>
									{/each}
								</select>
							</div>

							<div>
								<label for="edit-threat-impact" class="mb-1 block text-xs font-medium text-gray-700"
									>Impact (1-5)</label
								>
								<select
									id="edit-threat-impact"
									name="impact"
									class="w-full rounded border border-gray-300 px-2 py-1 text-sm text-slate-900 focus:ring-1 focus:ring-red-500 focus:outline-none"
								>
									{#each [1, 2, 3, 4, 5] as level}
										<option value={level} selected={$editingThreat.impact == level}>{level}</option>
									{/each}
								</select>
							</div>
						</div>

						<!-- Current Risk Display -->
						<div class="mt-3 flex items-center space-x-2">
							<div
								class="h-3 w-3 rounded-full"
								style="background-color: {$editingThreat.riskColor || '#EAB308'}"
							></div>
							<span
								class="text-sm font-medium"
								style="color: {$editingThreat.riskColor || '#EAB308'}"
							>
								{$editingThreat.riskLevel || 'Medium'} (Score: {$editingThreat.riskScore || 'N/A'})
							</span>
						</div>
					</div>

					<div class="grid grid-cols-2 gap-3">
						<div>
							<label for="edit-threat-status" class="mb-1 block text-sm font-medium text-gray-700"
								>Status</label
							>
							<select
								id="edit-threat-status"
								name="status"
								class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
							>
								<option value="Open" selected={$editingThreat.status === 'Open'}>Open</option>
								<option value="In Progress" selected={$editingThreat.status === 'In Progress'}
									>In Progress</option
								>
								<option value="Mitigated" selected={$editingThreat.status === 'Mitigated'}
									>Mitigated</option
								>
								<option value="Accepted" selected={$editingThreat.status === 'Accepted'}
									>Accepted</option
								>
								<option value="Not Applicable" selected={$editingThreat.status === 'Not Applicable'}
									>Not Applicable</option
								>
							</select>
						</div>

						<div>
							<label for="edit-threat-severity" class="mb-1 block text-sm font-medium text-gray-700"
								>Severity</label
							>
							<select
								id="edit-threat-severity"
								name="severity"
								class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
							>
								<option value="Low" selected={$editingThreat.severity === 'Low'}>Low</option>
								<option value="Medium" selected={$editingThreat.severity === 'Medium'}
									>Medium</option
								>
								<option value="High" selected={$editingThreat.severity === 'High'}>High</option>
								<option value="Critical" selected={$editingThreat.severity === 'Critical'}
									>Critical</option
								>
							</select>
						</div>
					</div>

					<div>
						<label
							for="edit-threat-description"
							class="mb-1 block text-sm font-medium text-gray-700">Description</label
						>
						<textarea
							id="edit-threat-description"
							name="description"
							rows="4"
							class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
							placeholder="Describe the threat...">{$editingThreat.description}</textarea
						>
					</div>

					<div>
						<label for="edit-threat-mitigation" class="mb-1 block text-sm font-medium text-gray-700"
							>Mitigation</label
						>
						<textarea
							id="edit-threat-mitigation"
							name="mitigation"
							rows="4"
							class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
							placeholder="How to mitigate this threat...">{$editingThreat.mitigation}</textarea
						>
					</div>

					<!-- Action Buttons -->
					<div class="flex justify-end space-x-3 pt-4">
						<button
							type="button"
							on:click={() => showEditThreatDialog.set(false)}
							class="rounded-md border border-gray-300 bg-gray-100 px-6 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-200"
						>
							Cancel
						</button>
						<button
							type="submit"
							class="rounded-md border border-transparent bg-blue-600 px-6 py-2 text-sm font-medium text-white shadow-lg transition-colors hover:bg-blue-700"
						>
							Update Threat
						</button>
					</div>
				</div>
			</form>
		</div>
	</div>
{/if}

<!-- Add Threat Dialog - Bottom Docked Professional Interface -->
{#if $showThreatDialog && $currentElementForThreat}
	<!-- Bottom Docked Panel - Slides up from bottom -->
	<div
		class="fixed right-0 bottom-0 left-0 z-50 transform border-t border-gray-300 bg-white shadow-2xl transition-transform duration-300 ease-out"
		style="max-height: 70vh;"
	>
		<!-- Panel Header - Fixed -->
		<div
			class="flex items-center justify-between border-b border-gray-200 bg-gradient-to-r from-red-50 to-orange-50 px-6 py-4"
		>
			<div class="flex items-center space-x-3">
				<div
					class="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-r from-red-600 to-orange-600 shadow-lg"
				>
					<span class="text-lg text-white">🛡️</span>
				</div>
				<div>
					<h3 class="text-lg font-semibold text-gray-900">Add Security Threat</h3>
					<p class="text-sm text-gray-600">
						Component: <span class="font-medium text-blue-600"
							>{$currentElementForThreat.name || $currentElementForThreat.type}</span
						>
					</p>
				</div>
			</div>
			<button
				on:click={() => showThreatDialog.set(false)}
				class="rounded-full p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
				aria-label="Close threat dialog"
			>
				<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M6 18L18 6M6 6l12 12"
					></path>
				</svg>
			</button>
		</div>

		<!-- Panel Content - Scrollable -->
		<div class="overflow-y-auto p-6" style="max-height: calc(70vh - 80px);">
			<form
				on:submit|preventDefault={(e) => {
					const formData = new FormData(e.target);

					addThreat({
						title: formData.get('title'),
						type: formData.get('type'),
						status: formData.get('status'),
						severity: formData.get('severity'),
						description: formData.get('description'),
						mitigation: formData.get('mitigation')
					});
					e.target.reset();
				}}
			>
				<div class="space-y-4">
					<div>
						<label for="threat-title" class="mb-1 block text-sm font-medium text-gray-700"
							>Title</label
						>
						<input
							id="threat-title"
							name="title"
							type="text"
							required
							class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
							placeholder="Enter threat title..."
						/>
					</div>

					<div>
						<label for="threat-type" class="mb-1 block text-sm font-medium text-gray-700"
							>Type</label
						>
						<select
							id="threat-type"
							name="type"
							required
							class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
						>
							<option value="" disabled selected>Select threat type...</option>
							<option value="Spoofing">Spoofing</option>
							<option value="Tampering">Tampering</option>
							<option value="Repudiation">Repudiation</option>
							<option value="Information Disclosure">Information Disclosure</option>
							<option value="Denial of Service">Denial of Service</option>
							<option value="Elevation of Privilege">Elevation of Privilege</option>
						</select>
					</div>

					<div>
						<label for="threat-severity" class="mb-1 block text-sm font-medium text-gray-700"
							>Severity</label
						>
						<select
							id="threat-severity"
							name="severity"
							class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
						>
							<option value="Low">Low</option>
							<option value="Medium" selected>Medium</option>
							<option value="High">High</option>
							<option value="Critical">Critical</option>
						</select>
					</div>

					<div>
						<label for="threat-status" class="mb-1 block text-sm font-medium text-gray-700"
							>Status</label
						>
						<select
							id="threat-status"
							name="status"
							class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
						>
							<option value="Open" selected>Open</option>
							<option value="In Progress">In Progress</option>
							<option value="Mitigated">Mitigated</option>
							<option value="Accepted">Accepted</option>
						</select>
					</div>

					<div>
						<label for="threat-description" class="mb-1 block text-sm font-medium text-gray-700"
							>Description</label
						>
						<textarea
							id="threat-description"
							name="description"
							rows="3"
							class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
							placeholder="Describe the threat scenario..."
						></textarea>
					</div>

					<div>
						<label for="threat-mitigation" class="mb-1 block text-sm font-medium text-gray-700"
							>Mitigation</label
						>
						<textarea
							id="threat-mitigation"
							name="mitigation"
							rows="2"
							class="w-full rounded-md border border-gray-300 px-3 py-2 text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
							placeholder="How to mitigate this threat..."
						></textarea>
					</div>

					<div class="flex justify-end space-x-3 border-t border-gray-200 pt-4">
						<button
							type="button"
							on:click={() => showThreatDialog.set(false)}
							class="rounded-lg bg-gray-100 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-200"
						>
							Cancel
						</button>
						<button
							type="submit"
							class="rounded-lg bg-red-600 px-4 py-2 text-white transition-colors hover:bg-red-700"
						>
							Add Threat
						</button>
					</div>
				</div>
			</form>
		</div>
	</div>
{/if}

<!-- Individual AI Threat Review Dialog -->
{#if showIndividualThreatReview && currentThreatForReview}
	<!-- Overlay -->
	<div class="bg-opacity-1 fixed inset-0 z-40 flex items-center justify-center p-4">
		<!-- Dialog -->
		<div class="max-h-[90vh] w-full max-w-2xl overflow-hidden rounded-xl bg-white shadow-2xl">
			<!-- Header -->
			<div class="border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-3">
						<div
							class="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600"
						>
							<span class="text-lg text-white">🔍</span>
						</div>
						<div>
							<h3 class="text-lg font-semibold text-gray-900">Review AI Suggested Threat</h3>
							<p class="text-sm text-gray-600">Validate threat relevance for your architecture</p>
						</div>
					</div>
					<button
						on:click={closeIndividualThreatReview}
						class="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
						aria-label="Close threat review dialog"
					>
						<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							></path>
						</svg>
					</button>
				</div>
			</div>

			<!-- Content -->
			<div class="max-h-[calc(90vh-140px)] overflow-y-auto p-6">
				<!-- Threat Category -->
				<div class="mb-4">
					<div class="mb-1 block text-sm font-medium text-gray-700">Threat Category</div>
					<div class="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
						<span class="font-medium text-gray-900 capitalize"
							>{currentThreatCategory?.replace(/_/g, ' ')}</span
						>
					</div>
				</div>

				<!-- Threat Description -->
				<div class="mb-6">
					<div class="mb-2 block text-sm font-medium text-gray-700">AI Suggested Threat</div>
					<div class="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
						<p class="leading-relaxed text-blue-900">{currentThreatForReview.text}</p>
					</div>
				</div>

				<!-- Validation Section -->
				<div class="mb-6">
					<div class="mb-3 block text-sm font-medium text-gray-700">
						Is this threat relevant to your architecture?
					</div>
					<div class="flex gap-3">
						<button
							on:click={() => (threatReviewValid = true)}
							class="flex-1 rounded-lg border-2 px-4 py-3 transition-all {threatReviewValid === true
								? 'border-green-500 bg-green-50 text-green-700'
								: 'border-gray-200 hover:border-green-300'}"
						>
							<div class="flex items-center justify-center gap-2">
								<span class="text-xl">✓</span>
								<span class="font-medium">Valid</span>
							</div>
							<p
								class="mt-1 text-sm {threatReviewValid === true
									? 'text-green-600'
									: 'text-gray-500'}"
							>
								This threat applies to our system
							</p>
						</button>

						<button
							on:click={() => (threatReviewValid = false)}
							class="flex-1 rounded-lg border-2 px-4 py-3 transition-all {threatReviewValid ===
							false
								? 'border-red-500 bg-red-50 text-red-700'
								: 'border-gray-200 hover:border-red-300'}"
						>
							<div class="flex items-center justify-center gap-2">
								<span class="text-xl">✗</span>
								<span class="font-medium">Invalid</span>
							</div>
							<p
								class="mt-1 text-sm {threatReviewValid === false
									? 'text-red-600'
									: 'text-gray-500'}"
							>
								This threat doesn't apply
							</p>
						</button>
					</div>
				</div>

				<!-- Feedback Section -->
				<div class="mb-6">
					<label for="threat-review-feedback" class="mb-2 block text-sm font-medium text-gray-700">
						Additional Comments <span class="text-gray-500">(Optional)</span>
					</label>
					<textarea
						id="threat-review-feedback"
						bind:value={threatReviewFeedback}
						rows="3"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
						placeholder="Explain why this threat is valid/invalid, or provide additional context..."
					></textarea>
				</div>
			</div>

			<!-- Footer -->
			<div class="flex justify-end gap-3 border-t border-gray-200 bg-gray-50 px-6 py-4">
				<button
					on:click={closeIndividualThreatReview}
					class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50"
				>
					Cancel
				</button>
				<button
					on:click={submitIndividualThreatReview}
					disabled={threatReviewValid === null}
					class="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
				>
					Submit Review
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	/* ============================================
	   MATTE ENGINEERING DESIGN SYSTEM (LIGHT ONLY)
	   ============================================ */
	.tm-canvas-page {
		--font-sans: 'Inter', system-ui, -apple-system, sans-serif;
		--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
		--ease-premium: cubic-bezier(0.2, 0, 0, 1);
		--tm-nav-height: 64px;
		--tm-bar-height: 40px;
		--tm-action-height: 48px;
		--bg-app: #ffffff;
		--bg-surface: #f8fafc;
		--bg-surface-alt: #f1f5f9;
		--border: rgba(0, 0, 0, 0.06);
		--border-focus: rgba(0, 173, 239, 0.2);
		--text-primary: #0f172a;
		--text-secondary: #475569;
		--text-muted: #94a3b8;
		--accent: #0082b4;
		--accent-soft: rgba(0, 130, 180, 0.08);
		--success: #059669;
		--error: #dc2626;
		--warning: #d97706;
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		background: var(--bg-app);
		font-family: var(--font-sans);
		position: relative;
	}

	/* ---- Header Navigation ---- */
	.tm-header {
		height: var(--tm-nav-height);
		background: var(--bg-app);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid var(--border);
		display: flex;
		align-items: center;
		position: sticky;
		top: 0;
		z-index: 100;
		flex-shrink: 0;
	}
	.tm-header-content {
		max-width: 1440px;
		width: 100%;
		margin: 0 auto;
		padding: 0 2rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.tm-nav-brand {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		text-decoration: none;
		color: var(--text-primary);
	}
	.tm-brand-icon { width: 28px; height: 28px; }
	.tm-brand-name {
		font-weight: 700;
		font-size: 1rem;
		letter-spacing: -0.02em;
		color: var(--text-primary);
	}
	.tm-nav-menu {
		display: flex;
		gap: 1.5rem;
		margin-left: 3rem;
	}
	.tm-nav-link {
		font-size: 0.8125rem;
		font-weight: 500;
		color: var(--text-secondary);
		text-decoration: none;
		transition: color 0.15s;
		padding: 0.5rem 0;
		position: relative;
	}
	.tm-nav-link:hover, .tm-nav-link.active { color: var(--text-primary); }
	.tm-nav-link.active::after {
		content: '';
		position: absolute;
		bottom: -1px;
		left: 0; right: 0;
		height: 2px;
		background: var(--accent);
	}

	/* ---- Technical Breadcrumb Bar ---- */
	
	@keyframes tm-blink {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.3; }
	}

	/* ---- Loading / Center State ---- */
	.tm-center-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 6rem 2rem;
		text-align: center;
		gap: 1rem;
		flex: 1;
	}
	.tm-loader-icon {
		width: 40px; height: 40px;
		animation: tm-pulse 2s ease-in-out infinite;
	}
	@keyframes tm-pulse {
		0%, 100% { opacity: 0.5; transform: scale(0.95); }
		50% { opacity: 1; transform: scale(1); }
	}
	.tm-loader-text {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--text-muted);
		letter-spacing: 0.1em;
	}

	/* ---- Error State ---- */
	.tm-error-icon {
		width: 40px; height: 40px;
		color: var(--error);
		opacity: 0.7;
	}
	.tm-error-title {
		font-size: 1.125rem;
		font-weight: 700;
		color: var(--text-primary);
		letter-spacing: -0.02em;
	}
	.tm-error-text {
		color: var(--error);
		font-size: 0.8125rem;
		font-weight: 500;
	}
	.tm-error-actions {
		display: flex;
		gap: 0.75rem;
		margin-top: 0.5rem;
	}

	/* ---- Action Toolbar ---- */
	.tm-action-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem 1.25rem;
		border-bottom: 1px solid var(--border);
		background: var(--bg-surface);
		height: var(--tm-action-height);
		flex-shrink: 0;
		gap: 1rem;
	}
	.tm-action-left, .tm-action-right {
		display: flex;
		align-items: center;
		gap: 0.625rem;
	}

	/* ---- Save Status ---- */
	.tm-save-status {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--text-muted);
	}
	.tm-save-spinner {
		width: 12px; height: 12px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: tm-spin 0.8s linear infinite;
	}
	@keyframes tm-spin { to { transform: rotate(360deg); } }
	.tm-save-dot {
		width: 6px; height: 6px;
		background: var(--success);
		border-radius: 50%;
	}
	.tm-save-muted { color: var(--text-muted); }

	/* ---- Buttons ---- */
	.tm-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.4rem;
		padding: 0.375rem 0.75rem;
		border-radius: 6px;
		font-size: 0.75rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
		font-family: var(--font-sans);
		border: 1px solid var(--border);
		background: var(--bg-surface-alt);
		color: var(--text-secondary);
		white-space: nowrap;
	}
	.tm-btn:hover {
		background: var(--text-primary);
		color: var(--bg-app);
		border-color: var(--text-primary);
		transform: translateY(-1px);
	}
	.tm-btn-primary {
		background: var(--text-primary);
		color: var(--bg-app);
		border-color: var(--text-primary);
	}
	.tm-btn-primary:hover { opacity: 0.9; }
	.tm-btn-secondary {
		background: var(--bg-surface-alt);
		border-color: var(--border);
		color: var(--text-secondary);
	}
	.tm-btn-ai {
		background: linear-gradient(135deg, #6366f1, #8b5cf6);
		color: #ffffff;
		border-color: transparent;
		box-shadow: 0 1px 3px rgba(99, 102, 241, 0.2);
	}
	.tm-btn-ai:hover {
		background: linear-gradient(135deg, #4f46e5, #7c3aed);
		color: #ffffff;
		border-color: transparent;
		box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
	}
	.tm-btn-ai.active {
		box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.3), 0 1px 3px rgba(99, 102, 241, 0.2);
	}
	.tm-ai-dot {
		width: 6px; height: 6px;
		background: #4ade80;
		border-radius: 50%;
		animation: tm-pulse 2s ease-in-out infinite;
	}

	/* ---- Responsive ---- */
	@media (max-width: 768px) {
		.tm-nav-menu { display: none; }
		.tm-action-bar { flex-wrap: wrap; height: auto; padding: 0.5rem; }
	}

	/* ---- Fix form input text visibility in dialogs ---- */
	:global(.fixed input[type="text"]),
	:global(.fixed input[type="number"]),
	:global(.fixed input:not([type])),
	:global(.fixed textarea),
	:global(.fixed select) {
		color: #0f172a !important;
		background-color: #ffffff !important;
	}
	:global(.fixed input::placeholder),
	:global(.fixed textarea::placeholder) {
		color: #94a3b8 !important;
	}
	:global(.fixed option) {
		color: #0f172a !important;
		background-color: #ffffff !important;
	}
	:global(.element) {
		transition: all 0.2s ease;
	}

	:global(.element:hover) {
		opacity: 0.9;
	}

	:global(.resize-handle) {
		transition: all 0.15s ease;
		filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
	}

	:global(.resize-handle:hover) {
		transform: scale(1.1);
		filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
	}

	:global(.connection-handle) {
		transition: all 0.15s ease;
		filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
	}

	:global(.connection-handle:hover) {
		transform: scale(1.1);
		filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
	}

	:global(.connection-drag-handle:hover) {
		transform: scale(1.2);
	}

	/* Enhanced visual feedback for selected elements */
	:global(.element-selected) {
		filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.4));
	}

	/* Striped border effect for selected elements */
	:global(.element-selected rect),
	:global(.element-selected circle) {
		stroke-dasharray: 8, 4;
		animation: dash 1s linear infinite;
	}

	/* Custom Scrollbar for AI Analysis Panel */
	:global(.ai-analysis-scroll) {
		scrollbar-width: thin;
		scrollbar-color: #cbd5e0 #f7fafc;
	}

	:global(.ai-analysis-scroll::-webkit-scrollbar) {
		width: 6px;
	}

	:global(.ai-analysis-scroll::-webkit-scrollbar-track) {
		background: #f7fafc;
		border-radius: 3px;
	}

	:global(.ai-analysis-scroll::-webkit-scrollbar-thumb) {
		background: #cbd5e0;
		border-radius: 3px;
	}

	:global(.ai-analysis-scroll::-webkit-scrollbar-thumb:hover) {
		background: #a0aec0;
	}

	/* Smooth transitions for panel animations */
	:global(.panel-transition) {
		transition: all 0.3s ease-in-out;
	}

	/* Professional typography for AI analysis */
	:global(.ai-analysis-content h2) {
		color: #1a202c;
		border-left: 4px solid #805ad5;
		padding-left: 12px;
	}

	:global(.ai-analysis-content h3) {
		color: #2d3748;
		border-left: 3px solid #667eea;
		padding-left: 10px;
	}

	:global(.ai-analysis-content p) {
		line-height: 1.6;
	}

	/* Progress bar animation */
	@keyframes progress {
		0% {
			width: 0%;
		}
		25% {
			width: 25%;
		}
		50% {
			width: 50%;
		}
		75% {
			width: 75%;
		}
		100% {
			width: 100%;
		}
	}

	@keyframes dash {
		to {
			stroke-dashoffset: -12;
		}
	}
</style>
