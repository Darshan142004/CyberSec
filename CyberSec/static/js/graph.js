/**
 * vis.js privilege graph rendering and interaction.
 */

let network = null;
let allGraphData = null;

async function initGraph() {
    const container = document.getElementById('graph-container');
    container.innerHTML = '<div class="loading-spinner"></div>';

    try {
        const data = await fetch('/api/graph').then(r => r.json());
        allGraphData = data;
        renderGraph(data, container);
        setupGraphControls();
    } catch (err) {
        container.innerHTML = '<p class="text-danger text-center p-4">Failed to load graph</p>';
        console.error('Graph load error:', err);
    }
}

function renderGraph(data, container) {
    container.innerHTML = '';

    const nodes = new vis.DataSet(data.nodes.map(n => ({
        id: n.id,
        label: n.label,
        color: {
            background: n.color || '#4fc3f7',
            border: n.borderWidth ? '#ef5350' : (n.color || '#4fc3f7'),
            highlight: { background: '#fff', border: '#58a6ff' },
        },
        shape: n.shape || 'dot',
        size: n.size || 15,
        borderWidth: n.borderWidth || 1,
        font: { color: '#e6edf3', size: 10 },
        title: `${n.label}\nType: ${n.type}\n${n.platform ? 'Platform: ' + n.platform : ''}`,
        nodeType: n.type,
        group: n.group,
    })));

    const edges = new vis.DataSet(data.edges.map(e => ({
        from: e.from,
        to: e.to,
        label: e.label,
        arrows: e.arrows || 'to',
        color: { color: e.color || '#757575', opacity: 0.6 },
        font: { color: '#8b949e', size: 8, strokeWidth: 0 },
        smooth: { type: 'cubicBezier', roundness: 0.4 },
    })));

    const options = {
        physics: {
            stabilization: { iterations: 200 },
            barnesHut: {
                gravitationalConstant: -3000,
                springLength: 120,
                springConstant: 0.02,
                damping: 0.3,
            },
        },
        interaction: {
            hover: true,
            tooltipDelay: 100,
            zoomView: true,
            dragView: true,
        },
        layout: {
            improvedLayout: true,
        },
        groups: {
            identity: { shape: 'dot', size: 20 },
            group: { shape: 'diamond', size: 15 },
            permission: { shape: 'triangle', size: 10 },
        },
    };

    network = new vis.Network(container, { nodes, edges }, options);

    // Click handler for identity nodes
    network.on('click', async (params) => {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const node = nodes.get(nodeId);
            if (node && node.nodeType === 'identity') {
                await loadIdentityDetail(nodeId);
            }
        }
    });

    // Hover effect
    network.on('hoverNode', (params) => {
        document.getElementById('graph-container').style.cursor = 'pointer';
    });
    network.on('blurNode', () => {
        document.getElementById('graph-container').style.cursor = 'default';
    });
}

function setupGraphControls() {
    document.getElementById('btn-graph-full').addEventListener('click', () => {
        document.getElementById('btn-graph-full').classList.add('active');
        document.getElementById('btn-graph-risky').classList.remove('active');
        renderGraph(allGraphData, document.getElementById('graph-container'));
    });

    document.getElementById('btn-graph-risky').addEventListener('click', () => {
        document.getElementById('btn-graph-risky').classList.add('active');
        document.getElementById('btn-graph-full').classList.remove('active');
        const riskyData = filterRiskyNodes(allGraphData);
        renderGraph(riskyData, document.getElementById('graph-container'));
    });
}

function filterRiskyNodes(data) {
    // Keep only identity nodes with risk or connected to risky identities
    const riskyNodeIds = new Set();

    data.nodes.forEach(n => {
        if (n.type === 'identity' && n.borderWidth) {
            riskyNodeIds.add(n.id);
        }
        if (n.type === 'identity' && n.color === '#ef5350') {
            riskyNodeIds.add(n.id);
        }
        if (n.type === 'identity' && n.color === '#ffa726') {
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
    if (!network) return;

    try {
        const subgraph = await fetch(`/api/graph/identity/${identityId}`).then(r => r.json());
        renderGraph(subgraph, document.getElementById('graph-container'));
    } catch (err) {
        console.error('Subgraph load error:', err);
    }
}
