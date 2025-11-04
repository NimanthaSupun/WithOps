import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { IndexeddbPersistence } from 'y-indexeddb';
import { Awareness } from 'y-protocols/awareness';

/**
 * Yjs-based Real-time Collaboration Store
 * Provides true real-time collaboration with conflict resolution
 */

// Yjs document and providers
let ydoc = null;
let wsProvider = null;
let indexeddbProvider = null;

// Collaboration stores
export const room = writable(null);
export const isConnected = writable(false);
export const connectionError = writable(null);

// Real-time collaborative data
export const yElements = writable(new Map());
export const yConnections = writable(new Map());
export const yThreats = writable(new Map());
export const yMetadata = writable({});
export const yComments = writable([]);

// User presence
export const others = writable([]);
export const myPresence = writable({
	cursor: null,
	selection: null,
	userInfo: { name: '', avatar: '', color: '#000000' }
});

// Derived stores
export const onlineUsersCount = derived(others, ($others) => $others.length + 1);
export const userColors = derived(others, ($others) => {
	const colors = {};
	$others.forEach((user) => {
		if (user.userInfo?.name && user.userInfo?.color) {
			colors[user.userInfo.name] = user.userInfo.color;
		}
	});
	return colors;
});

// Legacy compatibility exports
export const liveElements = yElements;
export const liveConnections = yConnections;
export const liveThreats = yThreats;
export const liveMetadata = yMetadata;
export const liveComments = yComments;

/**
 * Initialize Yjs collaboration
 * @param {string} modelId - The threat model ID
 * @param {Object} userInfo - Current user information
 */
export async function initializeCollaboration(modelId, userInfo = {}) {
	if (!browser) {
		console.log('Not in browser environment, skipping Yjs collaboration');
		return null;
	}

	try {
		console.log('🤝 Initializing Yjs collaboration for model:', modelId);

		// Create Yjs document
		ydoc = new Y.Doc();

		// Note: WebSocket collaboration disabled for local development
		// To enable: set up your own Y.js WebSocket server
		const roomName = `threat-model-${modelId}`;

		// Create IndexedDB provider for offline persistence (local only)
		indexeddbProvider = new IndexeddbPersistence(roomName, ydoc);

		console.log('📱 Local-only collaboration mode enabled (IndexedDB persistence)');

		// Get shared types from Yjs document
		const yElementsMap = ydoc.getMap('elements');
		const yConnectionsMap = ydoc.getMap('connections');
		const yThreatsMap = ydoc.getMap('threats');
		const yMetadataMap = ydoc.getMap('metadata');
		const yCommentsArray = ydoc.getArray('comments');

		// Set up awareness for user presence (local awareness for development)
		const awareness = new Awareness(ydoc);
		awareness.setLocalStateField('user', {
			name: userInfo.name || 'Anonymous User',
			color: userInfo.color || generateUserColor(userInfo.name || 'Anonymous'),
			avatar: userInfo.avatar || '',
			id: userInfo.id || `user-${Date.now()}`
		});

		// Listen to awareness changes (other users)
		awareness.on('change', () => {
			const states = awareness.getStates();
			const otherUsers = [];

			states.forEach((state, clientId) => {
				if (clientId !== awareness.clientID && state.user) {
					otherUsers.push({
						connectionId: clientId,
						userInfo: state.user,
						presence: state
					});
				}
			});

			others.set(otherUsers);
			console.log('👥 Online users:', otherUsers.length + 1);
		});

		// Listen to document changes
		yElementsMap.observe(() => {
			const elementsMap = new Map();
			yElementsMap.forEach((value, key) => {
				elementsMap.set(key, value);
			});
			yElements.set(elementsMap);
		});

		yConnectionsMap.observe(() => {
			const connectionsMap = new Map();
			yConnectionsMap.forEach((value, key) => {
				connectionsMap.set(key, value);
			});
			yConnections.set(connectionsMap);
		});

		yThreatsMap.observe(() => {
			const threatsMap = new Map();
			yThreatsMap.forEach((value, key) => {
				threatsMap.set(key, value);
			});
			yThreats.set(threatsMap);
		});

		yMetadataMap.observe(() => {
			const metadata = {};
			yMetadataMap.forEach((value, key) => {
				metadata[key] = value;
			});
			yMetadata.set(metadata);
		});

		yCommentsArray.observe(() => {
			yComments.set(yCommentsArray.toArray());
		});

		// Connection status (disabled for local development)
		// wsProvider.on('status', (event) => {
		//     console.log('🌐 Connection status:', event.status);
		//     isConnected.set(event.status === 'connected');
		//     if (event.status === 'connected') {
		//         connectionError.set(null);
		//     }
		// });

		// wsProvider.on('connection-error', (error) => {
		//     console.error('❌ Connection error:', error);
		//     connectionError.set(error.message);
		// });

		// Set local-only status
		isConnected.set(true); // Local IndexedDB always "connected"
		connectionError.set(null);

		// Store providers for cleanup
		const collaborationRoom = {
			ydoc,
			// wsProvider, // Disabled for local development
			indexeddbProvider,
			awareness,
			yElementsMap,
			yConnectionsMap,
			yThreatsMap,
			yMetadataMap,
			yCommentsArray
		};

		room.set(collaborationRoom);
		console.log('✅ Yjs collaboration initialized successfully');

		return collaborationRoom;
	} catch (error) {
		console.error('❌ Failed to initialize Yjs collaboration:', error);
		connectionError.set(error.message);
		isConnected.set(false);
		throw error;
	}
}

/**
 * Update user presence
 */
export function updatePresence(presenceUpdate) {
	if (!browser || !wsProvider) return;

	const awareness = wsProvider.awareness;
	const currentState = awareness.getLocalState() || {};
	awareness.setLocalState({
		...currentState,
		...presenceUpdate
	});
}

/**
 * Add or update an element
 */
export function updateLiveElement(element) {
	if (!browser || !ydoc) return;

	const yElementsMap = ydoc.getMap('elements');
	yElementsMap.set(element.id, element);
	console.log('📝 Updated element via Yjs:', element.id);
}

/**
 * Remove an element
 */
export function removeLiveElement(elementId) {
	if (!browser || !ydoc) return;

	const yElementsMap = ydoc.getMap('elements');
	yElementsMap.delete(elementId);
	console.log('🗑️ Removed element via Yjs:', elementId);
}

/**
 * Add or update a connection
 */
export function updateLiveConnection(connection) {
	if (!browser || !ydoc) return;

	const yConnectionsMap = ydoc.getMap('connections');
	yConnectionsMap.set(connection.id, connection);
	console.log('🔗 Updated connection via Yjs:', connection.id);
}

/**
 * Add a comment
 */
export function addComment(comment) {
	if (!browser || !ydoc) return;

	const yCommentsArray = ydoc.getArray('comments');
	const newComment = {
		...comment,
		id: `comment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
		timestamp: Date.now()
	};
	yCommentsArray.push([newComment]);
	console.log('💬 Added comment via Yjs:', newComment.id);
}

/**
 * Update canvas metadata
 */
export function updateLiveMetadata(metadataUpdate) {
	if (!browser || !ydoc) return;

	const yMetadataMap = ydoc.getMap('metadata');
	Object.entries(metadataUpdate).forEach(([key, value]) => {
		yMetadataMap.set(key, value);
	});
	yMetadataMap.set('lastModified', Date.now());
	console.log('📊 Updated metadata via Yjs');
}

/**
 * Disconnect from collaboration
 */
export function disconnectCollaboration() {
	if (!browser) return;

	try {
		// WebSocket provider disabled for local development
		// if (wsProvider) {
		//     wsProvider.destroy();
		//     wsProvider = null;
		// }
		if (indexeddbProvider) {
			indexeddbProvider.destroy();
			indexeddbProvider = null;
		}
		if (ydoc) {
			ydoc.destroy();
			ydoc = null;
		}

		room.set(null);
		isConnected.set(false);
		others.set([]);
		console.log('👋 Disconnected from Yjs collaboration');
	} catch (error) {
		console.error('Error disconnecting:', error);
	}
}

/**
 * Broadcast a custom event
 */
export function broadcastEvent(event) {
	if (!browser || !wsProvider) return;

	const awareness = wsProvider.awareness;
	const currentState = awareness.getLocalState() || {};
	awareness.setLocalState({
		...currentState,
		customEvent: {
			...event,
			timestamp: Date.now()
		}
	});
	console.log('📡 Broadcasted event via Yjs:', event);
}

/**
 * Generate consistent user color
 */
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

	let hash = 0;
	for (let i = 0; i < userName.length; i++) {
		const char = userName.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}

	return colors[Math.abs(hash) % colors.length];
}
