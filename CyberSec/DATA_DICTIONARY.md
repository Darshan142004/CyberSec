# Data Dictionary

## Dataset Overview

| Metric | Value |
|--------|-------|
| Total People (HR Records) | 250 |
| Terminated Employees | 55 (22%) |
| Active Directory Accounts | ~240 |
| AWS IAM Accounts | ~150 |
| Okta Accounts | ~220 |
| Service Accounts | 15-20 (cross-platform) |
| Total Platform Accounts | ~620 |
| Unified Identities | ~272 |
| Audit Events | ~974 |
| Groups/Roles | 40 |

## Anomaly Distribution

| Scenario | Count | Percentage |
|----------|-------|-----------|
| Orphaned/stale accounts | 68 findings | ~25% of identities |
| Over-privileged identities | 7 findings | ~3% |
| Privilege escalation events | 5 findings | ~2% |
| Token/credential abuse | 7 findings | ~3% |
| Cross-platform mismatch | 26 findings | ~10% |
| Offboarding failures | 63 findings | ~23% |
| Dormant admins | 14 findings | ~5% |
| Unused permissions | 88 findings | ~32% |
| Legitimate high-privilege (false positives) | 26 justified | ~10% |

---

## Entity: PlatformIdentity

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | UUID | Unique account identifier | `a1b2c3d4-...` |
| platform | Enum | Source platform | `active_directory`, `aws_iam`, `okta` |
| username | String | Platform-specific login name | `jsmith` (AD), `john.smith` (AWS), `john.smith@sg.com` (Okta) |
| email | String | Corporate email | `john.smith@societe-generale.com` |
| display_name | String | Full name | `John Smith` |
| department | String | HR department | `Engineering`, `Finance`, etc. |
| title | String | Job title | `Senior Developer` |
| status | Enum | Account state | `active`, `disabled`, `suspended`, `locked` |
| is_admin | Boolean | Elevated privileges flag | `true`/`false` |
| groups | List[String] | Group memberships | `["Domain Admins", "VPN-Users"]` |
| roles | List[String] | Assigned roles (AWS) | `["AdministratorAccess"]` |
| granted_permissions | List[String] | All granted permissions | `["s3:GetObject", "s3:PutObject"]` |
| used_permissions | List[String] | Permissions actually exercised | `["s3:GetObject"]` |
| last_login | DateTime | Most recent authentication | `2026-05-15T09:30:00` |
| created_at | DateTime | Account creation date | `2022-03-01T00:00:00` |
| mfa_enabled | Boolean | Multi-factor auth status | `true`/`false` |
| manager | String | Reporting manager name | `Jane Director` |
| is_service_account | Boolean | Non-human identity flag | `true`/`false` |
| access_tokens | List[Object] | API tokens/keys | See AccessToken |
| justification | String | Approved access reason | `"Approved via ITSM-2024-0892"` |

## Entity: AccessToken

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| token_id | String | Token identifier | `a1b2c3d4e5f6` |
| scope | String | Declared access scope | `read`, `read-write`, `admin` |
| created_at | DateTime | Token creation time | `2025-11-01T00:00:00` |
| expires_at | DateTime | Token expiration | `2026-05-01T00:00:00` |
| last_used | DateTime | Last API call time | `2026-06-18T14:30:00` |
| is_expired | Boolean | Past expiration date | `true`/`false` |
| scope_violation | Boolean | Used beyond scope | `true`/`false` |
| observed_actions | List[String] | Actual operations | `["write", "delete"]` |

## Entity: AuditEvent

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | UUID | Event identifier | `e1f2g3h4-...` |
| timestamp | DateTime | Event occurrence time | `2026-06-15T10:22:33` |
| event_type | Enum | Event category | `login_success`, `privilege_change`, `token_usage` |
| platform | Enum | Source platform | `active_directory`, `aws_iam`, `okta` |
| identity_id | UUID | Related account ID | `a1b2c3d4-...` |
| username | String | Acting username | `jsmith` |
| source_ip | String | Origin IP address | `10.0.1.45` or `203.0.113.1` |
| target_resource | String | Accessed resource | `s3://prod-data-lake/customer-pii/` |
| action | String | Operation performed | `login`, `read`, `write`, `group_add` |
| outcome | String | Result | `success`, `failure` |
| details | Object | Additional context | `{"reason": "mfa_failed"}` |
| is_anomalous | Boolean | Flagged as suspicious | `true`/`false` |

### Event Types

| Type | Description | Count |
|------|-------------|-------|
| `login_success` | Successful authentication | ~550 |
| `login_failure` | Failed authentication attempt | ~65 |
| `privilege_change` | Permission/role modification | ~100 |
| `resource_access` | Data/resource interaction | ~180 |
| `token_usage` | API token activity | ~70 |
| `group_add` | Group membership addition | Included in privilege_change |
| `role_assign` | Role assignment | Included in privilege_change |

## Entity: UnifiedIdentity

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unified identity identifier |
| primary_email | String | Canonical email address |
| display_name | String | Resolved display name |
| department | String | HR department |
| title | String | Job title |
| manager | String | Reporting manager |
| platform_accounts | Dict[Platform→Identity] | Linked platform accounts |
| risk_score | Float (0-100) | Aggregate risk score |
| findings | List[RiskFinding] | Associated risk findings |
| is_service_account | Boolean | Non-human identity |
| has_justification | Boolean | Has approved access exception |

## Entity: RiskFinding

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Finding identifier |
| identity_id | UUID | Related unified identity |
| category | Enum | Detection rule category |
| severity | Enum | `critical`, `high`, `medium`, `low` |
| score | Float (0-100) | Weighted risk score |
| title | String | Human-readable summary |
| description | String | Detailed explanation |
| platform | String | Affected platform(s) |
| evidence | Object | Supporting data |
| remediation | List[String] | CLI commands to fix |
| compliance_refs | List[String] | Compliance controls |
| mitre_refs | List[String] | MITRE ATT&CK techniques |

## Entity: Incident

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Incident identifier |
| title | String | Incident summary |
| root_cause | String | Underlying cause category |
| affected_identities | List[UUID] | Impacted identities |
| findings | List[RiskFinding] | Clustered findings |
| severity | Enum | Maximum severity |
| aggregate_score | Float | Combined risk score |
| remediation_steps | List[String] | Consolidated actions |
| status | String | `open`, `investigating`, `resolved` |

## Platform Username Conventions

| Platform | Format | Example |
|----------|--------|---------|
| Active Directory | First initial + last name | `jsmith` |
| AWS IAM | first.last or first_last | `john.smith` |
| Okta | Email address | `john.smith@societe-generale.com` |
| Service Accounts | prefix_system | `svc_jenkins` |

## Group Hierarchy

### Active Directory
```
Enterprise Admins
  └── Domain Admins
       ├── Server Operators
       └── Backup Operators
```

### AWS IAM
```
AdministratorAccess
  └── PowerUserAccess
       └── ReadOnlyAccess
```

### Okta
```
IT-Admins
  └── Privileged-Access
```
