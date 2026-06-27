/**
 * Risk register table with sorting and filtering.
 */

let dataTable = null;

function initRiskTable(findings) {
    const tbody = document.getElementById('risk-table-body');
    tbody.innerHTML = findings.map(f => renderRiskRow(f)).join('');

    dataTable = $('#risk-table').DataTable({
        order: [[0, 'desc']],
        pageLength: 15,
        lengthMenu: [10, 15, 25, 50],
        language: {
            emptyTable: 'No risk findings detected',
            info: 'Showing _START_ to _END_ of _TOTAL_ findings',
        },
        columnDefs: [
            { orderable: true, targets: [0, 1, 2, 3, 4] },
            { orderable: false, targets: [5] },
        ],
    });
}

function updateRiskTable(findings) {
    if (dataTable) {
        dataTable.destroy();
    }
    const tbody = document.getElementById('risk-table-body');
    tbody.innerHTML = findings.map(f => renderRiskRow(f)).join('');

    dataTable = $('#risk-table').DataTable({
        order: [[0, 'desc']],
        pageLength: 15,
        lengthMenu: [10, 15, 25, 50],
    });
}

function renderRiskRow(finding) {
    const severityBadge = `<span class="badge badge-${finding.severity}">${finding.severity.toUpperCase()}</span>`;
    const categoryBadge = formatCategory(finding.category);
    const platformBadge = finding.platform ? `<span class="platform-badge platform-${finding.platform.split(',')[0].trim()}">${finding.platform}</span>` : '-';

    const scoreClass = finding.score >= 80 ? 'score-critical' :
                       finding.score >= 60 ? 'score-high' :
                       finding.score >= 40 ? 'score-medium' : 'score-low';

    return `
        <tr data-identity-id="${finding.identity_id}" data-finding-id="${finding.id}">
            <td>
                <div class="d-flex align-items-center gap-2">
                    <strong>${finding.score.toFixed(1)}</strong>
                    <div class="score-bar flex-grow-1" style="width:50px;">
                        <div class="score-bar-fill ${scoreClass}" style="width:${finding.score}%"></div>
                    </div>
                </div>
            </td>
            <td>${severityBadge}</td>
            <td>${categoryBadge}</td>
            <td class="text-truncate" style="max-width:300px;" title="${finding.title}">${finding.title}</td>
            <td>${platformBadge}</td>
            <td>
                <button class="btn btn-sm btn-outline-info" onclick="showRemediation('${finding.identity_id}', '${finding.id}')">Fix</button>
                <button class="btn btn-sm btn-outline-secondary" onclick="inspectIdentity('${finding.identity_id}')">Inspect</button>
            </td>
        </tr>
    `;
}

function formatCategory(category) {
    const labels = {
        'OrphanedAccount': 'Orphaned',
        'DormantAdmin': 'Dormant Admin',
        'PrivilegeSpike': 'Priv. Spike',
        'CrossPlatformMismatch': 'X-Platform',
        'OffboardingFailure': 'Offboarding',
        'ExcessivePermissions': 'Excessive',
        'TokenAbuse': 'Token Abuse',
        'UnusedPermissions': 'Unused Perms',
    };
    return `<small class="text-muted">${labels[category] || category}</small>`;
}

async function showRemediation(identityId, findingId) {
    try {
        const identity = await fetch(`/api/identities/${identityId}`).then(r => r.json());
        const finding = identity.findings.find(f => f.id === findingId);
        const remediation = identity.remediation;

        let content = '';
        if (finding) {
            content += `<h6>${finding.title}</h6>`;
            content += `<p class="text-muted">${finding.description}</p>`;
        }

        if (remediation && remediation.length > 0) {
            remediation.forEach((r, i) => {
                if (r.commands && r.commands.length > 0) {
                    content += `<div class="mb-3">`;
                    content += `<small class="text-muted">Priority: ${r.priority} | SLA: ${r.sla}</small>`;
                    content += `<div class="remediation-code mt-2">${formatCommands(r.commands)}</div>`;
                    if (r.compliance && r.compliance.length > 0) {
                        content += `<div class="mt-2">${r.compliance.map(c => `<span class="compliance-tag">${c}</span>`).join('')}</div>`;
                    }
                    content += `</div>`;
                }
            });
        }

        document.getElementById('remediation-content').innerHTML = content || '<p class="text-muted">No remediation data available.</p>';
        new bootstrap.Modal(document.getElementById('remediationModal')).show();
    } catch (err) {
        console.error('Remediation load error:', err);
    }
}

function formatCommands(commands) {
    return commands.map(cmd => {
        if (cmd.startsWith('#')) {
            return `<span class="cmd-comment">${escapeHtml(cmd)}</span>`;
        }
        return `<span class="cmd-action">${escapeHtml(cmd)}</span>`;
    }).join('\n');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function inspectIdentity(identityId) {
    await loadIdentityDetail(identityId);
    await focusOnIdentity(identityId);
}
