<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { getAuthClient } from '$lib/auth';
    import '../app.css';

    let canvas;
    let animationInstance;
    let isAuthenticated = false;
    let user = null;

    // Auth functions
    async function handleSignIn() {
        try {
            const client = await getAuthClient();
            await client.loginWithRedirect();
        } catch (error) {
            console.error('Sign in failed:', error);
        }
    }

    async function handleGetStarted() {
        try {
            const client = await getAuthClient();
            const authenticated = await client.isAuthenticated();
            
            if (authenticated) {
                goto('/dashboard');
            } else {
                await client.loginWithRedirect();
            }
        } catch (error) {
            console.error('Get started failed:', error);
        }
    }

    // Check authentication status
    onMount(async () => {
        try {
            const client = await getAuthClient();
            isAuthenticated = await client.isAuthenticated();
            if (isAuthenticated) {
                user = await client.getUser();
            }
        } catch (error) {
            console.error('Auth check failed:', error);
        }

        // Initialize animation
        if (canvas) {
            animationInstance = new AnimationManager(canvas);
            animationInstance.start();
            
            const handleResize = () => {
                if (animationInstance) {
                    animationInstance.resize();
                }
            };
            
            window.addEventListener('resize', handleResize);
            
            return () => {
                if (animationInstance) {
                    animationInstance.stop();
                }
                window.removeEventListener('resize', handleResize);
            };
        }
    });

    // Night Sky with Stars Animation System
    class NightSkyPipeline {
        constructor(canvas, ctx) {
            this.canvas = canvas;
            this.ctx = ctx;
            this.time = 0;
            this.pipes = [];
            this.nodes = [];
            this.energyFlows = [];
            this.stars = [];
            
            // Dark space color palette
            this.colors = {
                pipeBase: '#1A1A2E',
                pipeMetal: '#16213E',
                pipeLight: '#0F3460',
                pipeDark: '#0A0A0A',
                blueGlow: '#4A9EFF',
                orangeBand: '#FF8B4A',
                energyCore: '#66D9FF',
                supercharged: '#00FFFF', // Cyan for supercharged particles
                background: '#000000',
                starColor: '#FFFFFF'
            };
            
            this.initialize();
        }
        
        initialize() {
            // Get actual canvas dimensions for proper scaling
            const rect = this.canvas.getBoundingClientRect();
            const canvasWidth = rect.width;
            const canvasHeight = rect.height;
            
            const centerX = canvasWidth / 2;
            const centerY = canvasHeight / 2;
            
            // Create larger, more sophisticated pipeline
            this.pipes = this.generateCurvedPipes(centerX, centerY, canvasWidth, canvasHeight);
            this.nodes = this.generateNodes(centerX, centerY, canvasWidth, canvasHeight);
            this.energyFlows = this.generateEnergyFlows();
            this.stars = this.generateStars(canvasWidth, canvasHeight);
        }
        
        generateStars(canvasWidth, canvasHeight) {
            const stars = [];
            // Reduced from 200 to 150 for better performance while maintaining beauty
            for (let i = 0; i < 150; i++) {
                stars.push({
                    x: Math.random() * canvasWidth,
                    y: Math.random() * canvasHeight,
                    size: Math.random() * 1.5 + 0.5, // Slightly smaller for performance
                    brightness: Math.random() * 0.8 + 0.2,
                    twinkleSpeed: Math.random() * 0.015 + 0.008, // Slightly slower for performance
                    twinklePhase: Math.random() * Math.PI * 2
                });
            }
            return stars;
        }
        
        generateCurvedPipes(centerX, centerY, canvasWidth, canvasHeight) {
            const pipes = [];
            
            // Scale pipe dimensions based on canvas size
            const baseRadius = Math.min(canvasWidth, canvasHeight) * 0.3;
            const radiusStep = Math.min(canvasWidth, canvasHeight) * 0.05;
            
            // Larger main central hub pipes - even bigger
            for (let i = 0; i < 10; i++) { // Increased from 8 to 10
                const angle = (i / 10) * Math.PI * 2;
                const radius = baseRadius + i * radiusStep;
                
                pipes.push({
                    path: this.generateCurvedPath(
                        centerX, centerY,
                        centerX + Math.cos(angle) * radius,
                        centerY + Math.sin(angle) * radius,
                        100 + i * 30 // Increased curve strength
                    ),
                    thickness: 20 + i * 4, // Much thicker pipes
                    depth: (i % 3 - 1) * 50,
                    glowIntensity: 0.5 + (i % 2) * 0.3,
                    orangeBands: Math.floor(Math.random() * 4) + 2, // More bands
                    pulseSpeed: 0.01 + (i % 3) * 0.005 // Add pulsing animation
                });
            }
            
            // Secondary curved connections - larger and more
            for (let i = 0; i < 8; i++) { // Increased from 6 to 8
                const startAngle = (i / 8) * Math.PI * 2;
                const endAngle = ((i + 4) / 8) * Math.PI * 2;
                const connectionRadius = baseRadius * 0.8;
                
                pipes.push({
                    path: this.generateCurvedPath(
                        centerX + Math.cos(startAngle) * connectionRadius,
                        centerY + Math.sin(startAngle) * connectionRadius,
                        centerX + Math.cos(endAngle) * connectionRadius * 1.2,
                        centerY + Math.sin(endAngle) * connectionRadius * 1.2,
                        120 // Increased curve
                    ),
                    thickness: 16, // Thicker
                    depth: (i % 2 - 0.5) * 60,
                    glowIntensity: 0.4,
                    orangeBands: 3,
                    pulseSpeed: 0.008 + (i % 2) * 0.004
                });
            }
            
            return pipes;
        }
        
        generateCurvedPath(x1, y1, x2, y2, curvature) {
            const midX = (x1 + x2) / 2;
            const midY = (y1 + y2) / 2;
            const dx = x2 - x1;
            const dy = y2 - y1;
            const perpX = -dy / Math.sqrt(dx * dx + dy * dy) * curvature;
            const perpY = dx / Math.sqrt(dx * dx + dy * dy) * curvature;
            
            return {
                start: { x: x1, y: y1 },
                control: { x: midX + perpX, y: midY + perpY },
                end: { x: x2, y: y2 }
            };
        }
        
        generateNodes(centerX, centerY, canvasWidth, canvasHeight) {
            const nodes = [];
            
            // Scale node distances based on canvas size
            const baseDistance = Math.min(canvasWidth, canvasHeight) * 0.25;
            const distanceStep = Math.min(canvasWidth, canvasHeight) * 0.08;
            
            // Central processing hub - much larger
            nodes.push({
                x: centerX, y: centerY,
                radius: 45, // Increased from 35
                type: 'hub',
                glowColor: this.colors.blueGlow,
                pulseSpeed: 0.02
            });
            
            // Distributed processing nodes - larger and more
            for (let i = 0; i < 12; i++) { // Increased from 10
                const angle = (i / 12) * Math.PI * 2;
                const distance = baseDistance + (i % 4) * distanceStep;
                
                nodes.push({
                    x: centerX + Math.cos(angle) * distance,
                    y: centerY + Math.sin(angle) * distance,
                    radius: 25 + (i % 3) * 10, // Much larger nodes
                    type: 'processor',
                    glowColor: i % 2 ? this.colors.blueGlow : this.colors.orangeBand,
                    pulseSpeed: 0.015 + (i % 3) * 0.01
                });
            }
            
            return nodes;
        }
        
        generateEnergyFlows() {
            const flows = [];
            
            // Enhanced: Even more spectacular energy flows for maximum visual impact
            for (let i = 0; i < 50; i++) { // Back to 50 particles for optimal performance
                const energyType = Math.random() > 0.85 ? 'supercharged' : 'normal';
                let color;
                
                if (energyType === 'supercharged') {
                    color = this.colors.supercharged;
                } else {
                    color = Math.random() > 0.35 ? this.colors.blueGlow : this.colors.orangeBand;
                }
                
                flows.push({
                    progress: Math.random(),
                    speed: 0.001 + Math.random() * 0.007, // Wider speed variation
                    pipeIndex: Math.floor(Math.random() * this.pipes.length),
                    intensity: 0.3 + Math.random() * 0.7, // More intensity range
                    color: color,
                    size: 1.5 + Math.random() * 5, // Larger size variation
                    glowRadius: 4 + Math.random() * 12, // Enhanced glow range
                    trail: [], // Trail for spectacular effect
                    maxTrailLength: 4 + Math.floor(Math.random() * 6), // 4-10 trail segments
                    pulsePhase: Math.random() * Math.PI * 2, // Individual pulsing
                    energyType: energyType // Special energy types
                });
            }
            
            return flows;
        }
        
        update() {
            this.time += 0.016;
            
            // Optimized stars twinkling - reduce frequency for performance
            if (this.time % 0.1 < 0.016) { // Update every 6th frame
                this.stars.forEach(star => {
                    star.twinklePhase += star.twinkleSpeed;
                    star.brightness = 0.3 + Math.sin(star.twinklePhase) * 0.5;
                });
            }
            
            // Enhanced energy flows with advanced trail system and effects
            this.energyFlows.forEach(flow => {
                // Store previous position for trail
                const prevProgress = flow.progress;
                
                // Update pulse phase for dynamic effects
                flow.pulsePhase += 0.05;
                
                flow.progress += flow.speed;
                if (flow.progress > 1) {
                    flow.progress = 0;
                    flow.pipeIndex = Math.floor(Math.random() * this.pipes.length);
                    flow.trail = []; // Reset trail when restarting
                    
                    // Chance to become supercharged
                    if (Math.random() > 0.9) {
                        flow.energyType = 'supercharged';
                    } else {
                        flow.energyType = 'normal';
                    }
                }
                
                // Enhanced intensity with multiple wave patterns
                const baseIntensity = 0.4 + Math.sin(this.time * 2 + flow.progress * Math.PI * 2) * 0.3;
                const pulseIntensity = Math.sin(flow.pulsePhase) * 0.2;
                const speedBoost = flow.energyType === 'supercharged' ? 1.5 : 1;
                
                flow.intensity = Math.min(1, (baseIntensity + pulseIntensity) * speedBoost);
                
                // Enhanced trail management with better performance
                if (flow.trail.length >= flow.maxTrailLength) {
                    flow.trail.shift(); // Remove oldest trail point
                }
                if (prevProgress < flow.progress && flow.progress - prevProgress < 0.5) { // Only add if moving forward normally
                    flow.trail.push({
                        progress: prevProgress,
                        intensity: flow.intensity * 0.7,
                        size: flow.size * 0.8
                    });
                }
            });
        }
        
        drawStars() {
            this.stars.forEach(star => {
                this.ctx.save();
                this.ctx.globalAlpha = Math.max(0, star.brightness);
                this.ctx.fillStyle = this.colors.starColor;
                this.ctx.shadowColor = this.colors.starColor;
                this.ctx.shadowBlur = star.size * 2;
                this.ctx.beginPath();
                this.ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
                this.ctx.fill();
                this.ctx.restore();
            });
        }
        
        draw3DPipe(pipe) {
            const path = pipe.path;
            const thickness = pipe.thickness;
            const depth = pipe.depth;
            
            this.ctx.save();
            
            // Calculate 3D perspective
            const scale = 1 + depth * 0.002;
            const offsetY = depth * 0.3;
            
            // Draw pipe path with Bezier curve
            this.ctx.beginPath();
            this.ctx.moveTo(path.start.x, path.start.y + offsetY);
            this.ctx.quadraticCurveTo(
                path.control.x, path.control.y + offsetY,
                path.end.x, path.end.y + offsetY
            );
            
            // Dark metallic pipe gradient
            const gradient = this.ctx.createLinearGradient(0, -thickness, 0, thickness);
            gradient.addColorStop(0, this.colors.pipeLight);
            gradient.addColorStop(0.3, this.colors.pipeMetal);
            gradient.addColorStop(0.7, this.colors.pipeBase);
            gradient.addColorStop(1, this.colors.pipeDark);
            
            this.ctx.strokeStyle = gradient;
            this.ctx.lineWidth = thickness * scale;
            this.ctx.lineCap = 'round';
            this.ctx.stroke();
            
            // Orange accent bands
            for (let i = 0; i < pipe.orangeBands; i++) {
                const bandPosition = 0.2 + (i * 0.3);
                const bandPoint = this.getPointOnCurve(path, bandPosition);
                
                this.ctx.save();
                this.ctx.translate(bandPoint.x, bandPoint.y + offsetY);
                
                // Orange band glow
                this.ctx.shadowColor = this.colors.orangeBand;
                this.ctx.shadowBlur = 8;
                this.ctx.strokeStyle = this.colors.orangeBand;
                this.ctx.lineWidth = thickness * 0.3 * scale;
                this.ctx.beginPath();
                this.ctx.arc(0, 0, thickness * 0.6 * scale, 0, Math.PI * 2);
                this.ctx.stroke();
                
                this.ctx.restore();
            }
            
            // Energy glow effect
            if (pipe.glowIntensity > 0.6) {
                this.ctx.save();
                this.ctx.globalAlpha = (pipe.glowIntensity - 0.6) * 2;
                this.ctx.shadowColor = this.colors.blueGlow;
                this.ctx.shadowBlur = 15;
                this.ctx.strokeStyle = this.colors.blueGlow;
                this.ctx.lineWidth = thickness * 0.4 * scale;
                
                this.ctx.beginPath();
                this.ctx.moveTo(path.start.x, path.start.y + offsetY);
                this.ctx.quadraticCurveTo(
                    path.control.x, path.control.y + offsetY,
                    path.end.x, path.end.y + offsetY
                );
                this.ctx.stroke();
                this.ctx.restore();
            }
            
            this.ctx.restore();
        }
        
        getPointOnCurve(path, t) {
            const x = (1 - t) * (1 - t) * path.start.x + 
                     2 * (1 - t) * t * path.control.x + 
                     t * t * path.end.x;
            const y = (1 - t) * (1 - t) * path.start.y + 
                     2 * (1 - t) * t * path.control.y + 
                     t * t * path.end.y;
            return { x, y };
        }
        
        drawGlowingNodes() {
            this.nodes.forEach(node => {
                const pulse = Math.sin(this.time * node.pulseSpeed) * 0.3 + 0.7;
                const radius = node.radius * pulse;
                
                this.ctx.save();
                
                // Outer glow
                this.ctx.shadowColor = node.glowColor;
                this.ctx.shadowBlur = 25; // Increased glow
                this.ctx.fillStyle = node.glowColor;
                this.ctx.globalAlpha = 0.6;
                this.ctx.beginPath();
                this.ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
                this.ctx.fill();
                
                // Inner core
                this.ctx.shadowBlur = 0;
                this.ctx.fillStyle = '#FFFFFF';
                this.ctx.globalAlpha = 0.9;
                this.ctx.beginPath();
                this.ctx.arc(node.x, node.y, radius * 0.4, 0, Math.PI * 2);
                this.ctx.fill();
                
                // Ring highlight for hub
                if (node.type === 'hub') {
                    this.ctx.strokeStyle = node.glowColor;
                    this.ctx.lineWidth = 3; // Thicker ring
                    this.ctx.globalAlpha = pulse;
                    this.ctx.beginPath();
                    this.ctx.arc(node.x, node.y, radius * 1.5, 0, Math.PI * 2);
                    this.ctx.stroke();
                }
                
                this.ctx.restore();
            });
        }
        
        drawEnergyFlows() {
            // Performance optimization: batch similar operations
            this.ctx.save();
            
            this.energyFlows.forEach(flow => {
                if (flow.pipeIndex >= this.pipes.length) return;
                
                const pipe = this.pipes[flow.pipeIndex];
                const point = this.getPointOnCurve(pipe.path, flow.progress);
                
                // Enhanced trail effect with varied sizes and opacity
                flow.trail.forEach((trailPoint, index) => {
                    const trailPos = this.getPointOnCurve(pipe.path, trailPoint.progress);
                    const trailAlpha = (index / flow.trail.length) * trailPoint.intensity * 0.8;
                    const trailSize = (trailPoint.size || flow.size) * (0.2 + (index / flow.trail.length) * 0.8);
                    
                    this.ctx.save();
                    this.ctx.globalAlpha = trailAlpha;
                    this.ctx.shadowColor = flow.color;
                    this.ctx.shadowBlur = flow.glowRadius * 0.6;
                    this.ctx.fillStyle = flow.color;
                    this.ctx.beginPath();
                    this.ctx.arc(trailPos.x, trailPos.y, trailSize, 0, Math.PI * 2);
                    this.ctx.fill();
                    this.ctx.restore();
                });
                
                // Main energy particle with enhanced effects
                this.ctx.save();
                
                // Supercharged particles get special treatment
                const isSupercharged = flow.energyType === 'supercharged';
                const effectMultiplier = isSupercharged ? 1.8 : 1;
                const currentIntensity = flow.intensity * effectMultiplier;
                
                this.ctx.globalAlpha = Math.min(1, currentIntensity);
                
                // Triple-layer glow effect for maximum impact
                // Outer glow layer
                this.ctx.shadowColor = flow.color;
                this.ctx.shadowBlur = flow.glowRadius * 2 * effectMultiplier;
                this.ctx.fillStyle = flow.color;
                this.ctx.beginPath();
                this.ctx.arc(point.x, point.y, flow.size * 1.5 * effectMultiplier, 0, Math.PI * 2);
                this.ctx.fill();
                
                // Middle glow layer
                this.ctx.shadowBlur = flow.glowRadius * effectMultiplier;
                this.ctx.globalAlpha = Math.min(1, currentIntensity * 0.9);
                this.ctx.beginPath();
                this.ctx.arc(point.x, point.y, flow.size * 1.2 * effectMultiplier, 0, Math.PI * 2);
                this.ctx.fill();
                
                // Inner bright core
                this.ctx.shadowBlur = flow.glowRadius * 0.3;
                this.ctx.fillStyle = '#FFFFFF';
                this.ctx.globalAlpha = Math.min(1, currentIntensity * 0.95);
                this.ctx.beginPath();
                this.ctx.arc(point.x, point.y, flow.size * 0.5 * effectMultiplier, 0, Math.PI * 2);
                this.ctx.fill();
                
                // Supercharged particles get extra effects
                if (isSupercharged) {
                    // Lightning-like energy spikes
                    for (let i = 0; i < 6; i++) {
                        const angle = (i / 6) * Math.PI * 2 + this.time * 2;
                        const spikeLength = flow.size * 2 * Math.sin(this.time * 4 + i);
                        const endX = point.x + Math.cos(angle) * spikeLength;
                        const endY = point.y + Math.sin(angle) * spikeLength;
                        
                        this.ctx.strokeStyle = flow.color;
                        this.ctx.lineWidth = 2;
                        this.ctx.globalAlpha = currentIntensity * 0.6;
                        this.ctx.shadowBlur = flow.glowRadius;
                        this.ctx.beginPath();
                        this.ctx.moveTo(point.x, point.y);
                        this.ctx.lineTo(endX, endY);
                        this.ctx.stroke();
                    }
                    
                    // Pulsing outer ring
                    this.ctx.strokeStyle = flow.color;
                    this.ctx.lineWidth = 3;
                    this.ctx.globalAlpha = Math.sin(this.time * 6) * 0.5 + 0.5;
                    this.ctx.shadowBlur = flow.glowRadius * 1.5;
                    this.ctx.beginPath();
                    this.ctx.arc(point.x, point.y, flow.size * 3, 0, Math.PI * 2);
                    this.ctx.stroke();
                }
                
                // High-intensity particles get energy rings
                if (flow.intensity > 0.6 && !isSupercharged) {
                    this.ctx.strokeStyle = flow.color;
                    this.ctx.lineWidth = 1.5;
                    this.ctx.globalAlpha = (flow.intensity - 0.6) * 2.5;
                    this.ctx.shadowBlur = flow.glowRadius * 1.5;
                    this.ctx.beginPath();
                    this.ctx.arc(point.x, point.y, flow.size * 2.5, 0, Math.PI * 2);
                    this.ctx.stroke();
                    
                    // Secondary ring
                    this.ctx.globalAlpha = (flow.intensity - 0.6) * 1.5;
                    this.ctx.beginPath();
                    this.ctx.arc(point.x, point.y, flow.size * 3.5, 0, Math.PI * 2);
                    this.ctx.stroke();
                }
                
                this.ctx.restore();
            });
            
            this.ctx.restore();
        }
        
        draw() {
            this.ctx.save();
            
            // Get actual render dimensions
            const rect = this.canvas.getBoundingClientRect();
            const renderWidth = rect.width;
            const renderHeight = rect.height;
            
            // Pure black night sky background
            this.ctx.fillStyle = this.colors.background;
            this.ctx.fillRect(0, 0, renderWidth, renderHeight);
            
            // Draw twinkling stars
            this.drawStars();
            
            // Draw energy flows first (background)
            this.drawEnergyFlows();
            
            // Draw 3D pipes
            this.pipes.forEach(pipe => this.draw3DPipe(pipe));
            
            // Draw glowing nodes on top
            this.drawGlowingNodes();
            
            this.ctx.restore();
        }
    }

    class NetworkGrid {
        constructor(canvas, ctx) {
            this.canvas = canvas;
            this.ctx = ctx;
            this.nodes = [];
            this.connections = [];
            this.pulses = [];
            
            this.initializeGrid();
        }
        
        initializeGrid() {
            // Create background network grid
            const gridSize = 100;
            const rows = Math.ceil(this.canvas.height / gridSize);
            const cols = Math.ceil(this.canvas.width / gridSize);
            
            for (let row = 0; row < rows; row++) {
                for (let col = 0; col < cols; col++) {
                    this.nodes.push({
                        x: col * gridSize,
                        y: row * gridSize,
                        opacity: Math.random() * 0.3 + 0.1,
                        pulse: Math.random() * Math.PI * 2
                    });
                }
            }
            
            // Create random connections
            for (let i = 0; i < 20; i++) {
                const start = this.nodes[Math.floor(Math.random() * this.nodes.length)];
                const end = this.nodes[Math.floor(Math.random() * this.nodes.length)];
                if (start !== end) {
                    this.connections.push({ start, end, opacity: Math.random() * 0.2 });
                }
            }
        }
        
        update() {
            this.nodes.forEach(node => {
                node.pulse += 0.02;
                node.opacity = 0.1 + Math.sin(node.pulse) * 0.1;
            });
        }
        
        draw() {
            this.ctx.save();
            this.ctx.strokeStyle = '#333';
            this.ctx.fillStyle = '#4A9EFF';
            
            // Draw connections
            this.connections.forEach(conn => {
                this.ctx.globalAlpha = conn.opacity;
                this.ctx.beginPath();
                this.ctx.moveTo(conn.start.x, conn.start.y);
                this.ctx.lineTo(conn.end.x, conn.end.y);
                this.ctx.stroke();
            });
            
            // Draw nodes
            this.nodes.forEach(node => {
                this.ctx.globalAlpha = node.opacity;
                this.ctx.beginPath();
                this.ctx.arc(node.x, node.y, 2, 0, Math.PI * 2);
                this.ctx.fill();
            });
            
            this.ctx.restore();
        }
    }

    class AnimationManager {
        constructor(canvas) {
            this.canvas = canvas;
            this.ctx = canvas.getContext('2d');
            this.running = false;
            
            this.pipeline = new NightSkyPipeline(canvas, this.ctx);
            this.grid = new NetworkGrid(canvas, this.ctx);
            
            this.resize();
        }
        
        resize() {
            const rect = this.canvas.getBoundingClientRect();
            // Fix canvas dimensions to prevent cropping
            const pixelRatio = window.devicePixelRatio || 1;
            this.canvas.width = rect.width * pixelRatio;
            this.canvas.height = rect.height * pixelRatio;
            
            // Set canvas style dimensions to match container exactly
            this.canvas.style.width = rect.width + 'px';
            this.canvas.style.height = rect.height + 'px';
            
            this.ctx.scale(pixelRatio, pixelRatio);
            
            // Reinitialize components with new dimensions
            this.pipeline = new NightSkyPipeline(this.canvas, this.ctx);
            this.grid = new NetworkGrid(this.canvas, this.ctx);
        }
        
        start() {
            if (this.running) return;
            this.running = true;
            this.animate();
        }
        
        stop() {
            this.running = false;
        }
        
        animate() {
            if (!this.running) return;
            
            // Performance optimization: use requestAnimationFrame more efficiently
            const startTime = performance.now();
            
            // Update components
            this.pipeline.update();
            
            // Only update grid occasionally for performance
            if (startTime % 100 < 16) { // Update grid every ~6th frame
                this.grid.update();
            }
            
            // Clear and draw with optimized rendering
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            
            // Draw background grid less frequently for performance
            if (startTime % 200 < 16) { // Update grid visual every ~12th frame
                this.grid.draw();
            }
            
            // Draw main pipeline animation (the star of the show)
            this.pipeline.draw();
            
            // Performance monitoring: skip frames if needed
            const renderTime = performance.now() - startTime;
            const targetFrameTime = 16.67; // 60 FPS
            
            if (renderTime < targetFrameTime) {
                requestAnimationFrame(() => this.animate());
            } else {
                // If frame took too long, use setTimeout to maintain smooth animation
                setTimeout(() => requestAnimationFrame(() => this.animate()), 1);
            }
        }
    }

    onMount(async () => {
        try {
            const client = await getAuthClient();
            isAuthenticated = await client.isAuthenticated();
            if (isAuthenticated) {
                user = await client.getUser();
            }
        } catch (error) {
            console.error('Auth check failed:', error);
        }

        // Initialize animation
        if (canvas) {
            animationInstance = new AnimationManager(canvas);
            animationInstance.start();
            
            const handleResize = () => {
                if (animationInstance) {
                    animationInstance.resize();
                }
            };
            
            window.addEventListener('resize', handleResize);
            
            return () => {
                if (animationInstance) {
                    animationInstance.stop();
                }
                window.removeEventListener('resize', handleResize);
            };
        }
    });
</script>

<!-- Navigation Bar -->
<nav class="navbar">
    <div class="nav-container">
        <div class="nav-brand">
            <img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
            <span class="brand-name">WithOps</span>
        </div>
        <div class="nav-menu">
            <a href="#home" class="nav-link active">Home</a>
            <a href="#features" class="nav-link">Features</a>
            <a href="#security" class="nav-link">Security</a>
            <a href="#analytics" class="nav-link">Analytics</a>
            <a href="#docs" class="nav-link">Docs</a>
            <a href="#contact" class="nav-link">Contact</a>
        </div>
        <div class="nav-actions">
            {#if isAuthenticated}
                <span class="user-welcome">Welcome, {user?.name}</span>
                <button class="nav-btn-primary" on:click={() => goto('/dashboard')}>Dashboard</button>
            {:else}
                <button class="nav-btn-secondary" on:click={handleSignIn}>Sign In</button>
                <button class="nav-btn-primary" on:click={handleGetStarted}>Get Started</button>
            {/if}
        </div>
    </div>
</nav>

<!-- Hero Section with Split Layout -->
<main class="hero-dashboard" id="home">
    <canvas bind:this={canvas} class="background-animation"></canvas>
    
    <div class="hero-split-container">
        <!-- Left Side - Content -->
        <div class="hero-content-left">
            <header class="hero-section">
                <h1 class="main-title">
                    <span class="title-highlight">WithOps</span>
                    <span class="title-subtitle">DevSecOps Platform</span>
                </h1>
                <p class="hero-description">
                    Advanced security automation and continuous integration platform
                    with AI-powered threat detection and real-time monitoring capabilities.
                </p>
                <div class="cta-buttons">
                    {#if isAuthenticated}
                        <button class="btn-primary" on:click={() => goto('/dashboard')}>Go to Dashboard</button>
                        <button class="btn-secondary">Learn More</button>
                    {:else}
                        <button class="btn-primary" on:click={handleGetStarted}>Get Started</button>
                        <button class="btn-secondary" on:click={handleSignIn}>Sign In</button>
                    {/if}
                </div>
            </header>
        </div>
        
        <!-- Right Side - Animation -->
        <div class="hero-animation-right">
            <!-- Animation canvas will be positioned here via CSS -->
        </div>
    </div>
</main>

<!-- Features Section -->
<section class="features-section" id="features">
    <div class="features-container">
        <header class="section-header">
            <h2 class="section-title">Advanced DevSecOps Features</h2>
            <p class="section-description">
                Comprehensive security and automation capabilities for modern development workflows
            </p>
        </header>
        
        <div class="features-grid">
            <div class="feature-card enhanced">
                <div class="feature-icon-wrapper">
                    <div class="feature-icon">🤖</div>
                    <div class="icon-glow"></div>
                </div>
                <h3>AI Threat Analysis</h3>
                <p>Automatically identify and mitigate security risks in your codebase using advanced AI models.</p>
                <div class="feature-metrics">
                    <span class="metric">99.9% Accuracy</span>
                    <span class="metric">Real-time Analysis</span>
                </div>
            </div>
            
            <div class="feature-card enhanced">
                <div class="feature-icon-wrapper">
                    <div class="feature-icon">🔄</div>
                    <div class="icon-glow"></div>
                </div>
                <h3>Integrated CI/CD Workflows</h3>
                <p>Simplify build, test, and deployment pipelines with Docker and GitHub Actions.</p>
                <div class="feature-metrics">
                    <span class="metric">Docker Ready</span>
                    <span class="metric">GitHub Actions</span>
                </div>
            </div>
            
            <div class="feature-card enhanced">
                <div class="feature-icon-wrapper">
                    <div class="feature-icon">�</div>
                    <div class="icon-glow"></div>
                </div>
                <h3>User & Collaboration Management</h3>
                <p>Secure authentication, user roles, and real-time collaboration for distributed teams.</p>
                <div class="feature-metrics">
                    <span class="metric">Auth0 Security</span>
                    <span class="metric">Team Collaboration</span>
                </div>
            </div>
            
            <div class="feature-card enhanced">
                <div class="feature-icon-wrapper">
                    <div class="feature-icon">📊</div>
                    <div class="icon-glow"></div>
                </div>
                <h3>Threat Library & Reporting</h3>
                <p>Maintain a comprehensive threat database and generate actionable security reports.</p>
                <div class="feature-metrics">
                    <span class="metric">Threat Database</span>
                    <span class="metric">Actionable Reports</span>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Footer -->
<footer class="footer">
    <div class="footer-container">
        <div class="footer-content">
            <div class="footer-brand">
                <img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
                <span class="brand-name">WithOps</span>
                <p class="brand-description">
                    Next-generation DevSecOps platform for modern development teams
                </p>
            </div>
            
            <div class="footer-links">
                <div class="link-group">
                    <h4>Platform</h4>
                    <a href="#security">Security</a>
                    <a href="#monitoring">Monitoring</a>
                    <a href="#analytics">Analytics</a>
                    <a href="#automation">Automation</a>
                </div>
                
                <div class="link-group">
                    <h4>Resources</h4>
                    <a href="#docs">Documentation</a>
                    <a href="#api">API Reference</a>
                    <a href="#tutorials">Tutorials</a>
                    <a href="#support">Support</a>
                </div>
                
                <div class="link-group">
                    <h4>Company</h4>
                    <a href="#about">About</a>
                    <a href="#careers">Careers</a>
                    <a href="#blog">Blog</a>
                    <a href="#contact">Contact</a>
                </div>
            </div>
        </div>
        
        <div class="footer-bottom">
            <p>&copy; 2025 WithOps Platform. All rights reserved.</p>
            <div class="footer-social">
                <a href="/github" class="social-link">GitHub</a>
                <a href="/linkedin" class="social-link">LinkedIn</a>
                <a href="/twitter" class="social-link">Twitter</a>
            </div>
        </div>
    </div>
</footer>

<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    /* Navigation Bar */
    .navbar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 1000;
        background: rgba(0, 0, 0, 0.9);
        backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(74, 158, 255, 0.2);
        padding: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .nav-container {
        max-width: 1200px;
        margin: 0 auto;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 2rem;
    }
    
    .nav-brand {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .brand-icon {
        width: 32px;
        height: 32px;
        filter: drop-shadow(0 0 10px #4A9EFF);
    }
    
    .brand-name {
        font-size: 1.2rem;
        font-weight: 700;
        color: #4A9EFF;
    }
    
    .user-welcome {
        color: #CCCCCC;
        margin-right: 1rem;
        font-size: 0.9rem;
    }
    
    .nav-menu {
        display: flex;
        gap: 2rem;
        align-items: center;
    }
    
    .nav-link {
        color: #CCCCCC;
        text-decoration: none;
        font-weight: 500;
        transition: color 0.3s ease;
        position: relative;
    }
    
    .nav-link:hover,
    .nav-link.active {
        color: #4A9EFF;
    }
    
    .nav-link::after {
        content: '';
        position: absolute;
        bottom: -5px;
        left: 0;
        width: 0;
        height: 2px;
        background: #4A9EFF;
        transition: width 0.3s ease;
    }
    
    .nav-link:hover::after,
    .nav-link.active::after {
        width: 100%;
    }
    
    .nav-actions {
        display: flex;
        gap: 1rem;
        align-items: center;
    }
    
    .nav-btn-secondary,
    .nav-btn-primary {
        padding: 0.5rem 1.2rem;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
    }
    
    .nav-btn-secondary {
        background: transparent;
        color: #CCCCCC;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .nav-btn-secondary:hover {
        background: rgba(255, 255, 255, 0.1);
        color: white;
    }
    
    .nav-btn-primary {
        background: linear-gradient(135deg, #4A9EFF 0%, #FF8B4A 100%);
        color: white;
    }
    
    .nav-btn-primary:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(74, 158, 255, 0.3);
    }

    /* Hero Dashboard with Split Layout */
    .hero-dashboard {
        position: relative;
        height: 100vh;
        overflow: hidden;
        background: #000000;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-top: 0; /* Remove any top margin that might interfere */
        padding-top: 80px; /* Add padding to account for fixed navbar */
    }
    
    .background-animation {
        position: absolute;
        top: 0;
        right: 0;
        width: 60%; /* Animation takes right 60% of screen */
        height: 100%;
        z-index: 1;
        /* Prevent cropping and ensure full display */
        display: block;
        object-fit: contain;
        object-position: center center;
    }
    
    .hero-split-container {
        display: grid;
        grid-template-columns: 1fr 1fr; /* 50-50 split */
        width: 100%;
        height: calc(100vh - 80px); /* Subtract navbar height */
        max-width: 1400px;
        margin: 0 auto;
        align-items: center;
        position: relative;
        z-index: 2;
        margin-top: 80px; /* Push content below navbar */
    }
    
    .hero-content-left {
        padding: 3rem 3rem 3rem 2rem;
        display: flex;
        flex-direction: column;
        justify-content: center;
        height: 100%;
        /* background: rgba(0, 0, 0, 0.1); Semi-transparent background for readability */
        backdrop-filter: blur(4px);
    }
    
    .hero-animation-right {
        position: relative;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        /* Animation canvas will overlay this area */
    }
    
    .hero-section {
        margin-bottom: 0; /* Remove bottom margin since we removed scroll indicator */
        text-align: left; /* Left align the content */
    }
    
    .main-title {
        font-size: clamp(2.5rem, 8vw, 5rem);
        font-weight: 700;
        margin-bottom: 1.5rem;
        background: linear-gradient(135deg, #4A9EFF 0%, #FF8B4A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.1;
        text-shadow: 0 0 30px rgba(74, 158, 255, 0.3);
    }
    
    .title-subtitle {
        display: block;
        font-size: 0.5em;
        opacity: 1;
        margin-top: 0.5rem;
        letter-spacing: 0.1em;
    }
    
    .hero-description {
        font-size: 1.2rem;
        color: #CCCCCC;
        max-width: 500px; /* Limit width for better readability */
        margin: 0 0 3rem 0; /* Remove auto centering */
        line-height: 1.7;
        text-align: left;
    }
    
    .cta-buttons {
        display: flex;
        gap: 1.5rem;
        justify-content: flex-start; /* Left align buttons */
        flex-wrap: wrap;
    }
    
    .btn-primary, .btn-secondary {
        padding: 1.2rem 2.5rem;
        border: none;
        border-radius: 10px;
        font-size: 1.1rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
        display: inline-block;
    }
    
    .btn-primary {
        background: linear-gradient(135deg, #4A9EFF 0%, #FF8B4A 100%);
        color: white;
        box-shadow: 0 8px 25px rgba(74, 158, 255, 0.3);
    }
    
    .btn-primary:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 35px rgba(74, 158, 255, 0.4);
    }
    
    .btn-secondary {
        background: rgba(255, 255, 255, 0.1);
        color: #4A9EFF;
        border: 2px solid #4A9EFF;
        backdrop-filter: blur(10px);
    }
    
    .btn-secondary:hover {
        background: #4A9EFF;
        color: white;
        transform: translateY(-3px);
    }
    
    /* Features Section */
    .features-section {
        background: linear-gradient(180deg, #000000 0%, #0A0A0A 50%, #000000 100%);
        padding: 6rem 0;
        min-height: 100vh;
    }
    
    .features-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 2rem;
    }
    
    .section-header {
        text-align: center;
        margin-bottom: 4rem;
    }
    
    .section-title {
        font-size: clamp(2.5rem, 6vw, 4rem);
        font-weight: 700;
        color: white;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #4A9EFF 0%, #FF8B4A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .section-description {
        font-size: 1.2rem;
        color: #CCCCCC;
        max-width: 600px;
        margin: 0 auto;
        line-height: 1.6;
    }
    
    .features-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
        gap: 2rem;
        margin-top: 3rem;
    }
    
    .feature-card.enhanced {
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(74, 158, 255, 0.2);
        border-radius: 16px;
        padding: 2.5rem;
        text-align: center;
        transition: all 0.4s ease;
        position: relative;
        overflow: hidden;
    }
    
    .feature-card.enhanced::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(74, 158, 255, 0.1), transparent);
        transition: left 0.6s;
    }
    
    .feature-card.enhanced:hover::before {
        left: 100%;
    }
    
    .feature-card.enhanced:hover {
        transform: translateY(-8px);
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.04) 100%);
        border-color: rgba(74, 158, 255, 0.4);
        box-shadow: 0 20px 40px rgba(74, 158, 255, 0.1);
    }
    
    .feature-icon-wrapper {
        position: relative;
        display: inline-block;
        margin-bottom: 1.5rem;
    }
    
    .feature-icon {
        font-size: 3rem;
        position: relative;
        z-index: 2;
    }
    
    .icon-glow {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 80px;
        height: 80px;
        background: radial-gradient(circle, rgba(74, 158, 255, 0.3) 0%, transparent 70%);
        border-radius: 50%;
        z-index: 1;
        animation: pulse 2s ease-in-out infinite alternate;
    }
    
    @keyframes pulse {
        0% { transform: translate(-50%, -50%) scale(1); opacity: 0.7; }
        100% { transform: translate(-50%, -50%) scale(1.2); opacity: 0.3; }
    }
    
    .feature-card.enhanced h3 {
        color: #4A9EFF;
        margin-bottom: 1rem;
        font-size: 1.4rem;
        font-weight: 600;
    }
    
    .feature-card.enhanced p {
        color: #CCCCCC;
        line-height: 1.6;
        margin-bottom: 1.5rem;
        font-size: 1rem;
    }
    
    .feature-metrics {
        display: flex;
        gap: 1rem;
        justify-content: center;
        flex-wrap: wrap;
    }
    
    .metric {
        background: rgba(74, 158, 255, 0.1);
        color: #4A9EFF;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        border: 1px solid rgba(74, 158, 255, 0.3);
    }

    /* Footer */
    .footer {
        background: linear-gradient(180deg, #000000 0%, #0A0A0A 100%);
        border-top: 1px solid rgba(74, 158, 255, 0.2);
        padding: 3rem 0 1rem;
    }
    
    .footer-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 2rem;
    }
    
    .footer-content {
        display: grid;
        grid-template-columns: 1fr 2fr;
        gap: 3rem;
        margin-bottom: 2rem;
    }
    
    .footer-brand {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }
    
    .footer-brand .brand-icon {
        width: 48px;
        height: 48px;
        filter: drop-shadow(0 0 10px #4A9EFF);
    }
    
    .footer-brand .brand-name {
        font-size: 1.5rem;
        font-weight: 700;
        color: #4A9EFF;
    }
    
    .brand-description {
        color: #CCCCCC;
        line-height: 1.5;
        max-width: 300px;
    }
    
    .footer-links {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 2rem;
    }
    
    .link-group h4 {
        color: white;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    
    .link-group a {
        color: #CCCCCC;
        text-decoration: none;
        display: block;
        margin-bottom: 0.5rem;
        transition: color 0.3s ease;
    }
    
    .link-group a:hover {
        color: #4A9EFF;
    }
    
    .footer-bottom {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 2rem;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        color: #888;
    }
    
    .footer-social {
        display: flex;
        gap: 1rem;
    }
    
    .social-link {
        color: #CCCCCC;
        text-decoration: none;
        transition: color 0.3s ease;
    }
    
    .social-link:hover {
        color: #4A9EFF;
    }

    /* Responsive Design */
    @media (max-width: 768px) {
        .nav-container {
            padding: 0 1rem;
            flex-wrap: wrap;
        }
        
        .nav-menu {
            display: none;
        }
        
        .nav-actions {
            gap: 0.5rem;
        }
        
        .user-welcome {
            display: none; /* Hide on mobile for space */
        }
        
        /* Mobile: Stack layout vertically */
        .hero-dashboard {
            padding-top: 60px; /* Smaller navbar on mobile */
        }
        
        .hero-split-container {
            grid-template-columns: 1fr;
            grid-template-rows: 1fr 1fr;
            height: calc(100vh - 60px);
            margin-top: 60px;
        }
        
        .background-animation {
            width: 100%;
            height: 50%; /* Animation takes bottom half */
            top: 50%;
        }
        
        .hero-content-left {
            padding: 2rem 1.5rem;
            background: rgba(0, 0, 0, 0.9);
            order: 1;
        }
        
        .hero-animation-right {
            order: 2;
        }
        
        .main-title {
            font-size: clamp(2rem, 12vw, 4rem);
            text-align: center;
        }
        
        .hero-description {
            font-size: 1rem;
            margin-bottom: 2rem;
            text-align: center;
            max-width: none;
        }
        
        .hero-section {
            text-align: center;
        }
        
        .cta-buttons {
            flex-direction: column;
            align-items: center;
            gap: 1rem;
            justify-content: center;
        }
        
        .btn-primary, .btn-secondary {
            width: 100%;
            max-width: 280px;
            padding: 1rem 2rem;
        }
        
        .features-grid {
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }
        
        .feature-card.enhanced {
            padding: 2rem 1.5rem;
        }
        
        .footer-content {
            grid-template-columns: 1fr;
            gap: 2rem;
            text-align: center;
        }
        
        .footer-links {
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }
        
        .footer-bottom {
            flex-direction: column;
            gap: 1rem;
            text-align: center;
        }
    }

    @media (max-width: 480px) {
        .navbar {
            padding: 0.5rem 0;
        }
        
        .nav-container {
            padding: 0 0.5rem;
        }
        
        .nav-actions {
            gap: 0.25rem;
        }
        
        .nav-btn-secondary,
        .nav-btn-primary {
            padding: 0.4rem 0.8rem;
            font-size: 0.85rem;
        }
        
        .brand-name {
            font-size: 1rem;
        }
        
        .brand-icon {
            width: 24px;
            height: 24px;
        }
        
        .hero-content-left {
            padding: 0.5rem;
        }
        
        .main-title {
            margin-bottom: 1rem;
        }
        
        .hero-description {
            font-size: 0.9rem;
            line-height: 1.5;
        }
        
        .section-title {
            font-size: clamp(1.8rem, 8vw, 2.5rem);
        }
        
        .section-description {
            font-size: 1rem;
        }
        
        .features-container {
            padding: 0 1rem;
        }
        
        .feature-card.enhanced {
            padding: 1.5rem 1rem;
        }
        
        .feature-metrics {
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .metric {
            font-size: 0.75rem;
        }
    }

    /* Tablet optimizations */
    @media (min-width: 481px) and (max-width: 768px) {
        .features-grid {
            grid-template-columns: repeat(2, 1fr);
        }
        
        .hero-split-container {
            grid-template-columns: 1fr 1fr; /* Keep split on tablet */
        }
        
        .background-animation {
            width: 50%;
            height: 100%;
            top: 0;
        }
        
        .hero-content-left {
            padding: 2rem 1.5rem;
        }
        
        .cta-buttons {
            flex-direction: row;
            justify-content: flex-start;
        }
        
        .btn-primary, .btn-secondary {
            width: auto;
            min-width: 140px;
        }
    }

    /* Large screen optimizations */
    @media (min-width: 1200px) {
        .features-grid {
            grid-template-columns: repeat(3, 1fr);
            max-width: 1400px;
            margin: 3rem auto 0;
        }
        
        .hero-content-left {
            max-width: 900px;
        }
        
        .main-title {
            font-size: clamp(4rem, 8vw, 7rem);
        }
        
        .hero-description {
            font-size: 1.4rem;
            max-width: 800px;
        }
    }
</style>
