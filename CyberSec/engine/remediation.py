"""Platform-specific remediation commands and compliance mapping."""

from data.models import RiskCategory


COMPLIANCE_MAP = {
    RiskCategory.ORPHANED_ACCOUNT: [
        "NIST SP 800-53 AC-2(3): Disable inactive accounts",
        "CIS Control 5.3: Disable dormant accounts",
        "GDPR Art. 5(1)(e): Storage limitation",
    ],
    RiskCategory.DORMANT_ADMIN: [
        "NIST SP 800-53 AC-2(3): Disable inactive accounts",
        "CIS Control 5.2: Use unique passwords",
        "ISO 27001 A.9.2.5: Review of user access rights",
    ],
    RiskCategory.PRIVILEGE_SPIKE: [
        "NIST SP 800-53 AC-6: Least privilege",
        "CIS Control 6.8: Define and maintain role-based access",
        "SOX Section 404: Internal controls",
    ],
    RiskCategory.CROSS_PLATFORM_MISMATCH: [
        "NIST SP 800-53 AC-2: Account management",
        "CIS Control 5.1: Establish access granting process",
        "ISO 27001 A.9.2.6: Removal of access rights",
    ],
    RiskCategory.OFFBOARDING_FAILURE: [
        "NIST SP 800-53 PS-4: Personnel termination",
        "GDPR Art. 17: Right to erasure",
        "CIS Control 5.4: Restrict administrator privileges",
        "SOX Section 302: Corporate responsibility",
    ],
    RiskCategory.EXCESSIVE_PERMISSIONS: [
        "NIST SP 800-53 AC-6: Least privilege",
        "CIS Control 6.1: Minimize administrative privileges",
        "ISO 27001 A.9.4.1: Information access restriction",
    ],
    RiskCategory.TOKEN_ABUSE: [
        "NIST SP 800-53 IA-5: Authenticator management",
        "CIS Control 6.5: Require MFA for administrative access",
        "ISO 27001 A.9.4.2: Secure log-on procedures",
        "GDPR Art. 32: Security of processing",
    ],
    RiskCategory.UNUSED_PERMISSIONS: [
        "NIST SP 800-53 AC-6: Least privilege",
        "CIS Control 6.1: Minimize administrative privileges",
        "GDPR Art. 5(1)(c): Data minimisation",
    ],
}


def generate_remediation(finding):
    """Generate platform-specific remediation commands for a finding."""
    platform = finding.platform
    category = finding.category
    evidence = finding.evidence
    username = evidence.get("username", "UNKNOWN")

    commands = _get_commands(platform, category, username, evidence)
    compliance = COMPLIANCE_MAP.get(category, [])

    finding.remediation = commands
    finding.compliance_refs = compliance

    return {
        "commands": commands,
        "compliance": compliance,
        "priority": _priority_label(finding.severity),
        "sla": _sla_for_severity(finding.severity),
    }


def _get_commands(platform, category, username, evidence):
    """Generate CLI commands based on platform and risk category."""
    if "active_directory" in platform:
        return _ad_commands(category, username)
    elif "aws_iam" in platform:
        return _aws_commands(category, username, evidence)
    elif "okta" in platform:
        return _okta_commands(category, username)

    # Multi-platform findings
    commands = []
    if isinstance(platform, str) and "," in platform:
        platforms = [p.strip() for p in platform.split(",")]
        for p in platforms:
            commands.extend(_get_commands(p, category, username, evidence))
    return commands or [f"# Manual review required for {username}"]


def _ad_commands(category, username):
    """Active Directory remediation commands."""
    base = [f"# Active Directory - {username}"]

    if category == RiskCategory.ORPHANED_ACCOUNT:
        return base + [
            f"Disable-ADAccount -Identity '{username}'",
            f"Set-ADUser -Identity '{username}' -Description 'Orphaned - disabled by IAM automation'",
            f"Move-ADObject -Identity (Get-ADUser '{username}').DistinguishedName -TargetPath 'OU=Disabled,DC=corp,DC=societe-generale,DC=com'",
        ]
    elif category == RiskCategory.DORMANT_ADMIN:
        return base + [
            f"Remove-ADGroupMember -Identity 'Domain Admins' -Members '{username}' -Confirm:$false",
            f"Disable-ADAccount -Identity '{username}'",
            f"Set-ADUser -Identity '{username}' -Description 'Dormant admin - privileges revoked'",
        ]
    elif category == RiskCategory.OFFBOARDING_FAILURE:
        return base + [
            f"Disable-ADAccount -Identity '{username}'",
            f"Set-ADUser -Identity '{username}' -Description 'Terminated employee - immediate disable'",
            f"Get-ADUser '{username}' -Properties MemberOf | ForEach-Object {{ $_.MemberOf | Remove-ADGroupMember -Members '{username}' -Confirm:$false }}",
        ]
    elif category == RiskCategory.EXCESSIVE_PERMISSIONS:
        return base + [
            f"Remove-ADGroupMember -Identity 'Domain Admins' -Members '{username}' -Confirm:$false",
            f"Set-ADUser -Identity '{username}' -Description 'Excessive permissions removed - least privilege enforcement'",
        ]
    elif category == RiskCategory.CROSS_PLATFORM_MISMATCH:
        return base + [
            f"# Verify status in AD:",
            f"Get-ADUser -Identity '{username}' -Properties Enabled,LastLogonDate",
        ]

    return base + [f"# Review account: Get-ADUser -Identity '{username}' -Properties *"]


def _aws_commands(category, username, evidence):
    """AWS IAM remediation commands."""
    base = [f"# AWS IAM - {username}"]

    if category == RiskCategory.ORPHANED_ACCOUNT:
        return base + [
            f"aws iam create-login-profile --user-name {username} --password-reset-required 2>/dev/null || true",
            f"aws iam delete-login-profile --user-name {username}",
            f"aws iam list-access-keys --user-name {username} | jq -r '.AccessKeyMetadata[].AccessKeyId' | xargs -I {{}} aws iam update-access-key --user-name {username} --access-key-id {{}} --status Inactive",
        ]
    elif category == RiskCategory.DORMANT_ADMIN:
        return base + [
            f"aws iam remove-user-from-group --user-name {username} --group-name Admins",
            f"aws iam detach-user-policy --user-name {username} --policy-arn arn:aws:iam::aws:policy/AdministratorAccess",
            f"aws iam update-access-key --user-name {username} --access-key-id <KEY_ID> --status Inactive",
        ]
    elif category == RiskCategory.PRIVILEGE_SPIKE:
        roles = evidence.get("new_roles", [])
        cmds = base + [f"# Revert privilege escalation:"]
        for role in roles:
            cmds.append(f"aws iam detach-user-policy --user-name {username} --policy-arn arn:aws:iam::aws:policy/{role}")
        return cmds
    elif category == RiskCategory.OFFBOARDING_FAILURE:
        return base + [
            f"aws iam delete-login-profile --user-name {username}",
            f"aws iam list-access-keys --user-name {username} | jq -r '.AccessKeyMetadata[].AccessKeyId' | xargs -I {{}} aws iam delete-access-key --user-name {username} --access-key-id {{}}",
            f"aws iam list-attached-user-policies --user-name {username} | jq -r '.AttachedPolicies[].PolicyArn' | xargs -I {{}} aws iam detach-user-policy --user-name {username} --policy-arn {{}}",
        ]
    elif category == RiskCategory.EXCESSIVE_PERMISSIONS:
        return base + [
            f"aws iam detach-user-policy --user-name {username} --policy-arn arn:aws:iam::aws:policy/AdministratorAccess",
            f"aws iam attach-user-policy --user-name {username} --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess",
        ]
    elif category == RiskCategory.TOKEN_ABUSE:
        token_id = evidence.get("token_id", "<TOKEN_ID>")
        return base + [
            f"# Revoke compromised token:",
            f"aws iam list-access-keys --user-name {username}",
            f"aws iam update-access-key --user-name {username} --access-key-id {token_id} --status Inactive",
            f"aws iam delete-access-key --user-name {username} --access-key-id {token_id}",
            f"# Rotate credentials:",
            f"aws iam create-access-key --user-name {username}",
        ]
    elif category == RiskCategory.UNUSED_PERMISSIONS:
        unused = evidence.get("unused_permissions", [])
        cmds = base + [f"# Remove unused permissions (right-sizing):"]
        for perm in unused[:5]:
            cmds.append(f"# Revoke: {perm}")
        cmds.append(f"aws iam create-policy-version --policy-arn <POLICY_ARN> --policy-document file://right-sized-policy.json --set-as-default")
        return cmds

    return base + [f"# Review: aws iam get-user --user-name {username}"]


def _okta_commands(category, username):
    """Okta remediation commands."""
    base = [f"# Okta - {username}"]

    if category in (RiskCategory.ORPHANED_ACCOUNT, RiskCategory.OFFBOARDING_FAILURE):
        return base + [
            f"okta users deactivate {username}",
            f"okta users suspend {username}",
            f"# Remove all app assignments:",
            f"okta users apps list {username} | jq -r '.[].id' | xargs -I {{}} okta apps users remove {{}} {username}",
        ]
    elif category == RiskCategory.DORMANT_ADMIN:
        return base + [
            f"okta groups remove-user --group-id <ADMIN_GROUP_ID> --user-id {username}",
            f"okta users deactivate {username}",
        ]
    elif category == RiskCategory.EXCESSIVE_PERMISSIONS:
        return base + [
            f"okta groups remove-user --group-id <PRIVILEGED_GROUP_ID> --user-id {username}",
        ]
    elif category == RiskCategory.TOKEN_ABUSE:
        return base + [
            f"# Revoke Okta API token:",
            f"okta api-tokens revoke --token-id <TOKEN_ID> --user {username}",
            f"okta users sessions clear {username}",
        ]
    elif category == RiskCategory.UNUSED_PERMISSIONS:
        return base + [
            f"# Right-size Okta app assignments:",
            f"okta users apps list {username}",
            f"# Remove unused app assignments based on access review",
        ]

    return base + [f"# Review: okta users get {username}"]


def _priority_label(severity):
    from data.models import Severity
    return {
        Severity.CRITICAL: "P1 - Immediate",
        Severity.HIGH: "P2 - Within 24h",
        Severity.MEDIUM: "P3 - Within 7 days",
        Severity.LOW: "P4 - Next review cycle",
    }.get(severity, "P4")


def _sla_for_severity(severity):
    from data.models import Severity
    return {
        Severity.CRITICAL: "4 hours",
        Severity.HIGH: "24 hours",
        Severity.MEDIUM: "7 days",
        Severity.LOW: "30 days",
    }.get(severity, "30 days")
