/**
 * 3D Force Graph privilege graph rendering and interaction.
 */

let myGraph = null;
let allGraphData = null;
let currentRenderedData = null;

async function initGraph() {
    const container = document.getElementById('graph-container');
    container.innerHTML = '<div class="loading-spinner"></div>';

    try {
        const data = await fetch('/api/graph').then(r => r.json());
        allGraphData = data;
        renderGraph(data, container);
        setupGraphControls();
    } catch (err) {
        container.innerHTML = '<p class="text-danger text-center p-4">Failed to load 3D graph</p>';
        console.error('3D Graph load error:', err);
    }
}

function renderGraph(data, container) {
    container.innerHTML = '';
    currentRenderedData = data;

    // Transform node and edge data for 3D force graph format
    const nodes = data.nodes.map(n => {
        let size = 3;
        if (n.type === 'identity') size = 6;
        else if (n.type === 'group') size = 4.5;
        
        let color = n.color || '#4fc3f7';
        if (n.borderWidth) { // High risk / critical severity marker
            color = '#ef5350';
        }

        return {
            id: n.id,
            label: n.label,
            color: color,
            type: n.type,
            platform: n.platform,
            size: size
        };
    });

    const links = data.edges.map(e => ({
        source: e.from,
        target: e.to,
        label: e.label,
        color: e.color || '#757575'
    }));

    const width = container.clientWidth;
    const height = container.clientHeight || 500;

    myGraph = ForceGraph3D()(container)
        .width(width)
        .height(height)
        .graphData({ nodes, links })
        .backgroundColor('rgba(0,0,0,0)') // Transparent background
        .nodeColor(node => node.color)
        .nodeVal(node => node.size)
        .nodeLabel(node => `
            <div style="
                background: rgba(22, 27, 34, 0.95);
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 10px;
                font-family: monospace;
                color: #e6edf3;
                font-size: 0.8rem;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6);
                pointer-events: none;
            ">
                <span style="color: ${node.color}; font-weight: bold; font-size: 0.85rem;">■</span> 
                <strong style="color: #58a6ff;">${node.label}</strong><br/>
                <span style="color: #8b949e;">Type:</span> ${node.type}<br/>
                ${node.platform ? `<span style="color: #8b949e;">Platform:</span> ${node.platform}` : ''}
            </div>
        `)
        .linkLabel(link => `
            <div style="
                background: rgba(13, 17, 23, 0.9);
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 4px 8px;
                font-family: monospace;
                color: #8b949e;
                font-size: 0.7rem;
            ">
                ${link.label || 'member of'}
            </div>
        `)
        .linkColor(link => link.color)
        .linkWidth(1.2)
        .linkDirectionalArrowLength(4)
        .linkDirectionalArrowRelPos(0.98)
        .linkDirectionalArrowColor(link => link.color)
        .onNodeClick(async node => {
            if (node.type === 'identity') {
                // Smooth camera focus
                const distance = 80;
                const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
                myGraph.cameraPosition(
                    { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }, // camera position
                    node, // lookAt target
                    1200 // transition duration in ms
                );
                await loadIdentityDetail(node.id);
            }
        });

    // Custom warm-up and default camera distance
    myGraph.cooldownTicks(100);
    myGraph.cameraPosition({ z: 250 });

    // Handle window resizing
    window.addEventListener('resize', () => {
        if (myGraph && container) {
            myGraph.width(container.clientWidth);
        }
    });
}

function setupGraphControls() {
    // Clear old listeners if any
    const btnFull = document.getElementById('btn-graph-full');
    const btnRisky = document.getElementById('btn-graph-risky');

    // Clone to remove previous event listeners
    const newBtnFull = btnFull.cloneNode(true);
    const newBtnRisky = btnRisky.cloneNode(true);
    btnFull.parentNode.replaceChild(newBtnFull, btnFull);
    btnRisky.parentNode.replaceChild(newBtnRisky, btnRisky);

    newBtnFull.addEventListener('click', () => {
        newBtnFull.classList.add('active');
        newBtnRisky.classList.remove('active');
        renderGraph(allGraphData, document.getElementById('graph-container'));
    });

    newBtnRisky.addEventListener('click', () => {
        newBtnRisky.classList.add('active');
        newBtnFull.classList.remove('active');
        const riskyData = filterRiskyNodes(allGraphData);
        renderGraph(riskyData, document.getElementById('graph-container'));
    });
}

function filterRiskyNodes(data) {
    // Keep only identity nodes with high risk or connected to risky identities
    const riskyNodeIds = new Set();

    data.nodes.forEach(n => {
        if (n.type === 'identity' && (n.borderWidth || n.color === '#ef5350' || n.color === '#ffa726')) {
            riskyNodeIds.add(n.id);
        }
    });

    // Add connected nodes (1 hop from risky identities)
    const connectedIds = new Set(riskyNodeIds);
    data.edges.forEach(e => {
        if (riskyNodeIds.has(e.from)) connectedIds.add(e.to);
        if (riskyNodeIds.has(e.to)) connectedIds.add(e.from);
    });

    return {
        nodes: data.nodes.filter(n => connectedIds.has(n.id)),
        edges: data.edges.filter(e => connectedIds.has(e.from) && connectedIds.has(e.to)),
    };
}

async function focusOnIdentity(identityId) {
    try {
        const subgraph = await fetch(`/api/graph/identity/${identityId}`).then(r => r.json());
        renderGraph(subgraph, document.getElementById('graph-container'));

        // Smooth camera transition to the focused node once loaded
        setTimeout(() => {
            if (myGraph) {
                const node = myGraph.graphData().nodes.find(n => n.id === identityId);
                if (node) {
                    const distance = 80;
                    const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
                    myGraph.cameraPosition(
                        { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
                        node,
                        1200
                    );
                }
            }
        }, 1000);
    } catch (err) {
        console.error('Subgraph focus load error:', err);
    }
}
