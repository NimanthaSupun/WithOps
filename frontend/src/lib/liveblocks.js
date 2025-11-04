import { createClient } from '@liveblocks/client';

// Create Liveblocks client
export const client = createClient({
	// Get your public key from https://liveblocks.io/dashboard/apikeys
	publicApiKey: import.meta.env.VITE_LIVEBLOCKS_PUBLIC_KEY || 'pk_dev_demo_key',

	// Define the rooms and their types
	throttle: 16, // 60fps updates

	// Configure presence for real-time user indicators
	defaultPresence: {
		cursor: null, // { x: number, y: number }
		selection: null, // Selected element ID
		userInfo: {
			name: '',
			avatar: '',
			color: '#000000'
		}
	}
});

/**
 * Create or join a collaboration room for a threat model
 * @param {string} modelId - The threat model ID
 * @param {Object} userInfo - User information for presence
 */
export function createCollaborationRoom(modelId, userInfo = {}) {
	const roomId = `threat-model-${modelId}`;

	return client.enterRoom(roomId, {
		initialPresence: {
			cursor: null,
			selection: null,
			userInfo: {
				name: userInfo.name || 'Anonymous',
				avatar: userInfo.avatar || '',
				color: userInfo.color || generateUserColor()
			}
		}
	});
}

/**
 * Generate a random color for user identification
 */
function generateUserColor() {
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
	return colors[Math.floor(Math.random() * colors.length)];
}

/**
 * Storage configuration for persistent data
 */
export const storageConfig = {
	// Canvas elements (processes, datastores, actors, etc.)
	elements: {
		type: 'LiveList',
		default: []
	},

	// Connections between elements
	connections: {
		type: 'LiveList',
		default: []
	},

	// Threats associated with elements
	threats: {
		type: 'LiveList',
		default: []
	},

	// Canvas metadata (zoom, pan, etc.)
	metadata: {
		type: 'LiveObject',
		default: {
			zoom: 1.0,
			panX: 0,
			panY: 0,
			lastModified: Date.now(),
			version: '1.0'
		}
	},

	// Comments and discussions
	comments: {
		type: 'LiveList',
		default: []
	}
};

/**
 * Presence configuration for real-time user indicators
 */
export const presenceConfig = {
	cursor: null, // Current mouse/cursor position
	selection: null, // Currently selected element
	userInfo: {
		name: '',
		avatar: '',
		color: '#000000'
	},
	lastSeen: Date.now()
};
