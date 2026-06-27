# Identity Sprawl & Privileged Access Abuse Detection - Architecture

## System Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                         Flask Web Application                       │
├────────────────────────────────────────────────────────────────────┤
│  Frontend (Single-Page Dashboard)                                   │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐  ┌────────────┐  │
│  │ vis.js   │  │ Risk Table   │  │  Identity  │  │  Incident  │  │
│  │ Graph    │  │ (DataTables) │  │  Detail    │  │  Cluster   │  │
│  └──────────┘  └──────────────┘  └────────────┘  └────────────┘  │
├────────────────────────────────────────────────────────────────────┤
│  REST API Layer (Flask Blueprint)                                   │
│  /api/dashboard | /api/identities | /api/graph | /api/risks        │
│  /api/incidents | /api/compliance | /api/report | /api/audit-events │
├────────────────────────────────────────────────────────────────────┤
│  Detection & Analysis Engine                                        │
│  ┌───────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Risk Detector │  │ Risk Scorer  │  │ Incident Clusterer     │  │
│  │ (8 Rules)     │  │ (Weighted)   │  │ (Identity + Category)  │  │
│  └───────────────┘  └──────────────┘  └────────────────────────┘  │
│  ┌───────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Privilege     │  │ Identity     │  │ Remediation Engine     │  │
│  │ Graph (NX)   │  │ Resolver     │  │ (Platform-Specific)    │  │
│  └───────────────┘  └──────────────┘  └────────────────────────┘  │
├────────────────────────────────────────────────────────────────────┤
│  Data Layer (Synthetic Generation)                                  │
│  ┌───────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ 250 People    │  │ Seed         │  │ Audit Event Generator  │  │
│  │ 3 Platforms   │  │ Scenarios    │  │ (974 events)           │  │
│  │ 15 Svc Accts  │  │ (40+ issues) │  │                        │  │
│  └───────────────┘  └──────────────┘  └────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| Backend | Flask 3.0 | Simple template rendering, no async needed for demo |
| Graph Engine | NetworkX 3.2 | Pure Python, BFS/DFS, transitive closure |
| Data Generation | Faker 20.0 | Realistic synthetic identities |
| Frontend Graph | vis.js (CDN) | Interactive hierarchical layout, no build tools |
| Risk Table | DataTables (CDN) | Sorting, filtering, pagination |
| UI Framework | Bootstrap 5 (CDN) | Responsive dark theme |
| Date Handling | python-dateutil 2.8 | Relative date parsing |

## Detection Engine Architecture

### Rule-Based Approach (over ML)
**Rationale:** For a 48-hour hackathon, deterministic rules provide:
- Explainability: Each finding traces to specific evidence
- Reproducibility: Same data = same results
- Auditability: Compliance teams can review logic
- Speed: No training phase required

### 8 Detection Rules

| # | Rule | MITRE ATT&CK | Severity Range |
|---|------|--------------|----------------|
| 1 | Orphaned Account | T1078, T1078.002 | Medium-High |
| 2 | Dormant Admin (90+ days) | T1078, T1078.001 | High-Critical |
| 3 | Privilege Spike | T1098, T1098.001 | High |
| 4 | Cross-Platform Mismatch | T1078, T1550 | High |
| 5 | Offboarding Failure | T1078, T1098 | Critical |
| 6 | Excessive Permissions | T1078.004, T1098.003 | High |
| 7 | Token/Credential Abuse | T1550.001, T1528 | High-Critical |
| 8 | Unused Permissions | T1078 | Medium |

### Risk Scoring Formula

```
Score = min(base_weight × multiplier_product, 100)

Multipliers applied when:
  - is_admin: ×1.5
  - PII department: ×1.4
  - production access: ×1.3
  - multi-platform: ×1.2
  - no MFA: ×1.3
  - service account: ×1.2
  - expired token: ×1.4
  - dormant >180d: ×1.6
  - dormant >120d: ×1.3
  - offboarding: ×1.5
```

### Identity Aggregate Score
```
aggregate = max(finding_scores) + sum(other_scores × 0.15)
```

## Identity Resolution

### Phase 1: Exact Email Match
All accounts sharing the same email address are merged into one unified identity.

### Phase 2: Fuzzy Matching (SequenceMatcher ≥ 0.75)
Unmatched accounts are compared by:
- Display name similarity (weighted 1.5×)
- Username component matching against name parts
- Department correlation (weighted 0.3)

## Privilege Graph (NetworkX DiGraph)

### Node Types
- **Identity** (dot): Unified person/service account
- **Group** (diamond): AD groups, AWS roles, Okta groups
- **Permission** (triangle): Effective permissions

### Edge Types
- `member_of`: Identity → Group
- `has_role`: Identity → AWS Role
- `grants`: Group → Permission
- `inherits_from`: Group → Parent Group

### Effective Privilege Calculation
BFS traversal from identity node through all `member_of`, `has_role`, and `inherits_from` edges, collecting all reachable `permission` nodes.

## Alert Consolidation

Findings are clustered into Incidents via:
1. **Per-identity clustering**: Identities with ≥2 findings become compound incidents
2. **Systemic clustering**: Categories with ≥3 findings across identities become systemic incidents

**Target:** ≥40% reduction in standalone alerts → **Achieved: 74.8%**

## False Positive Prevention

- Accounts with documented `justification` field are excluded from detection
- Service accounts with approved ITSM tickets are excluded
- Executive exceptions per policy EXC-001 are excluded
- ~15-20% of high-privilege accounts have legitimate justification

## Compliance Framework Alignment

| Framework | Controls Mapped |
|-----------|----------------|
| NIST SP 800-53 | AC-2, AC-6, IA-4, IA-5, PS-4 |
| MITRE ATT&CK | T1078, T1098, T1528, T1550 (10 sub-techniques) |
| GDPR | Art. 5, Art. 17, Art. 32 |
| CIS Controls | 5.1-5.4, 6.1, 6.5, 6.8 |
| ISO 27001 | A.9.2.5, A.9.2.6, A.9.4.1, A.9.4.2 |
| SOX | Section 302, Section 404 |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard/summary` | GET | Executive summary statistics |
| `/api/identities` | GET | List all unified identities |
| `/api/identities/<id>` | GET | Identity detail + remediation |
| `/api/graph` | GET | Full privilege graph (vis.js JSON) |
| `/api/graph/identity/<id>` | GET | Identity-centered subgraph |
| `/api/risks` | GET | Risk findings (filterable) |
| `/api/incidents` | GET | Clustered incidents |
| `/api/audit-events` | GET | Audit event log |
| `/api/compliance` | GET | Compliance + MITRE mapping |
| `/api/report` | GET | Sample risk report (top 10) |
