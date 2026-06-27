"""Seed intentional security issues for detection demonstration."""

import random
from datetime import datetime, timedelta

from data.models import PlatformIdentity, Platform, AccountStatus


def seed_scenarios(data):
    """Inject 40+ intentional security issues into generated data."""
    ad_accounts = data["accounts"][Platform.ACTIVE_DIRECTORY.value]
    aws_accounts = data["accounts"][Platform.AWS_IAM.value]
    okta_accounts = data["accounts"][Platform.OKTA.value]
    people = data["people"]

    _seed_orphaned_accounts(ad_accounts, aws_accounts, people)
    _seed_dormant_admins(ad_accounts, aws_accounts)
    _seed_privilege_spikes(aws_accounts)
    _seed_cross_platform_mismatches(ad_accounts, aws_accounts, okta_accounts)
    _seed_offboarding_failures(ad_accounts, aws_accounts, okta_accounts, people)
    _seed_excessive_permissions(aws_accounts, ad_accounts)
    _seed_token_abuse(aws_accounts, okta_accounts)
    _seed_legitimate_high_privilege(ad_accounts, aws_accounts, people)
    _seed_sso_cascade_anomalies(data.get("audit_events", []), ad_accounts)

    return data


def _seed_orphaned_accounts(ad_accounts, aws_accounts, people):
    """Create accounts with no matching HR record (5-7 scenarios)."""
    orphaned_specs = [
        ("svc_migration", "svc_migration@societe-generale.com", "Migration Tool", True),
        ("admin_temp", "admin.temp@societe-generale.com", "Temp Admin", True),
        ("test_prod", "test.prod@societe-generale.com", "Production Test", False),
        ("legacy_app", "legacy.app@societe-generale.com", "Legacy App Account", False),
        ("contractor_ext", "contractor.external@societe-generale.com", "External Contractor", True),
    ]

    for username, email, display, is_admin in orphaned_specs:
        account = PlatformIdentity(
            platform=Platform.ACTIVE_DIRECTORY,
            username=username,
            email=email,
            display_name=display,
            department="Unknown",
            title="Unknown",
            status=AccountStatus.ACTIVE,
            is_admin=is_admin,
            groups=["Domain Admins"] if is_admin else ["VPN-Users"],
            last_login=datetime.now() - timedelta(days=random.randint(90, 300)),
            created_at=datetime.now() - timedelta(days=random.randint(365, 730)),
            mfa_enabled=False,
            manager="",
            is_service_account=False,
        )
        ad_accounts.append(account)

    # AWS orphaned accounts
    aws_orphaned = [
        ("shadow_admin", "shadow.admin@societe-generale.com", "Shadow Admin"),
        ("data_export_tool", "data.export@societe-generale.com", "Data Export"),
    ]
    for username, email, display in aws_orphaned:
        aws_accounts.append(PlatformIdentity(
            platform=Platform.AWS_IAM,
            username=username,
            email=email,
            display_name=display,
            department="Unknown",
            title="Unknown",
            status=AccountStatus.ACTIVE,
            is_admin=True,
            roles=["AdministratorAccess", "S3FullAccess"],
            last_login=datetime.now() - timedelta(days=random.randint(60, 200)),
            created_at=datetime.now() - timedelta(days=random.randint(300, 600)),
            mfa_enabled=False,
            is_service_account=False,
        ))


def _seed_dormant_admins(ad_accounts, aws_accounts):
    """Create admin accounts inactive for 90+ days (5 scenarios)."""
    ad_admins = [a for a in ad_accounts if a.is_admin and a.status == AccountStatus.ACTIVE]
    for account in random.sample(ad_admins, min(3, len(ad_admins))):
        account.last_login = datetime.now() - timedelta(days=random.randint(120, 280))

    aws_admins = [a for a in aws_accounts if a.is_admin and a.status == AccountStatus.ACTIVE]
    for account in random.sample(aws_admins, min(2, len(aws_admins))):
        account.last_login = datetime.now() - timedelta(days=random.randint(100, 220))
        account.mfa_enabled = False


def _seed_privilege_spikes(aws_accounts):
    """Create accounts with recent massive privilege escalation (5 scenarios)."""
    non_admin_aws = [a for a in aws_accounts if not a.is_admin and a.status == AccountStatus.ACTIVE and not a.is_service_account]
    targets = random.sample(non_admin_aws, min(5, len(non_admin_aws)))

    for account in targets:
        account.roles = ["AdministratorAccess", "IAMFullAccess", "SecurityAudit"]
        account.groups.append("AdministratorAccess")
        account.permissions = [
            "admin_granted:recent",
            f"escalated:{(datetime.now() - timedelta(days=random.randint(1, 7))).isoformat()}",
        ]


def _seed_cross_platform_mismatches(ad_accounts, aws_accounts, okta_accounts):
    """Create inconsistent status across platforms (5 scenarios)."""
    ad_emails = {a.email: a for a in ad_accounts}
    aws_emails = {a.email: a for a in aws_accounts}
    okta_emails = {a.email: a for a in okta_accounts}

    multi_platform = set(ad_emails.keys()) & set(aws_emails.keys()) & set(okta_emails.keys())
    active_multi = [e for e in multi_platform
                    if ad_emails[e].status == AccountStatus.ACTIVE
                    and aws_emails[e].status == AccountStatus.ACTIVE]

    targets = random.sample(list(active_multi), min(5, len(active_multi)))
    for email in targets:
        ad_emails[email].status = AccountStatus.DISABLED


def _seed_offboarding_failures(ad_accounts, aws_accounts, okta_accounts, people):
    """Create terminated employees with active accounts (8-10 scenarios)."""
    terminated = [p for p in people if p["terminated"]]

    # Ensure at least 8 terminated people have active accounts somewhere
    for person in terminated[:10]:
        email = person["email"]
        for acc_list in [ad_accounts, aws_accounts, okta_accounts]:
            for acc in acc_list:
                if acc.email == email:
                    acc.status = AccountStatus.ACTIVE
                    acc.last_login = datetime.now() - timedelta(days=random.randint(1, 10))
                    break


def _seed_excessive_permissions(aws_accounts, ad_accounts):
    """Create non-technical users with admin-level access (6 scenarios)."""
    non_tech = [a for a in aws_accounts
                if a.department in ["Finance", "HR", "Marketing", "Sales"]
                and a.status == AccountStatus.ACTIVE
                and not a.is_service_account]
    targets = random.sample(non_tech, min(4, len(non_tech)))

    for account in targets:
        account.roles = ["AdministratorAccess", "EC2FullAccess", "S3FullAccess", "IAMFullAccess"]
        account.is_admin = True
        account.groups.extend(["AdministratorAccess", "IAMFullAccess"])

    non_tech_ad = [a for a in ad_accounts
                   if a.department in ["Finance", "HR", "Marketing"]
                   and a.status == AccountStatus.ACTIVE
                   and not a.is_admin
                   and not a.is_service_account]
    for account in random.sample(non_tech_ad, min(3, len(non_tech_ad))):
        account.groups.append("Domain Admins")
        account.is_admin = True


def _seed_token_abuse(aws_accounts, okta_accounts):
    """Create token abuse scenarios (5-8 scenarios)."""
    # Expired tokens still being used
    token_accounts = [a for a in aws_accounts + okta_accounts
                      if a.access_tokens and a.status == AccountStatus.ACTIVE]

    for account in random.sample(token_accounts, min(4, len(token_accounts))):
        # Mark tokens as expired but with recent usage
        for token in account.access_tokens:
            token["is_expired"] = True
            token["expires_at"] = (datetime.now() - timedelta(days=random.randint(30, 90))).isoformat()
            token["last_used"] = (datetime.now() - timedelta(days=random.randint(0, 3))).isoformat()
            token["scope_violation"] = True  # Read token making write calls

    # Read-scoped tokens used for write operations
    read_token_accounts = [a for a in aws_accounts
                           if a.access_tokens
                           and a.status == AccountStatus.ACTIVE
                           and any(t.get("scope") == "read" for t in a.access_tokens)]
    for account in random.sample(read_token_accounts, min(3, len(read_token_accounts))):
        for token in account.access_tokens:
            if token.get("scope") == "read":
                token["scope_violation"] = True
                token["observed_actions"] = ["write", "delete", "admin_config"]


def _seed_legitimate_high_privilege(ad_accounts, aws_accounts, people):
    """Seed justified high-privilege users as false positive traps (15-20%)."""
    # IT/Security admins with documented justification
    it_security = [a for a in ad_accounts + aws_accounts
                   if a.department in ["IT", "Security"]
                   and a.is_admin
                   and a.status == AccountStatus.ACTIVE]

    # Mark ~40 accounts as legitimately justified
    for account in random.sample(it_security, min(15, len(it_security))):
        account.justification = random.choice([
            "Approved via ITSM-2024-0892: Domain admin required for AD migration project",
            "Approved via SEC-2024-0145: Security team lead - incident response role",
            "Approved via ITSM-2024-1203: Infrastructure team - production support",
            "Approved via PAM-2024-0067: Break-glass account for disaster recovery",
            "Approved via ITSM-2024-0534: Platform engineering - CI/CD pipeline management",
        ])

    # Mark some executive accounts as justified
    exec_accounts = [a for a in ad_accounts + aws_accounts
                     if a.department == "Executive"
                     and a.status == AccountStatus.ACTIVE]
    for account in random.sample(exec_accounts, min(5, len(exec_accounts))):
        account.justification = "Executive exception: Board-approved elevated access per policy EXC-001"

    # Service accounts with justification
    svc_accounts = [a for a in ad_accounts + aws_accounts if a.is_service_account]
    for account in random.sample(svc_accounts, min(10, len(svc_accounts))):
        account.justification = random.choice([
            "Service account: CI/CD pipeline - approved via ITSM-2024-0301",
            "Service account: Monitoring system - approved via OPS-2024-0089",
            "Service account: Backup automation - approved via ITSM-2024-0445",
            "Service account: Data integration - approved via DATA-2024-0112",
        ])


def _seed_sso_cascade_anomalies(audit_events, ad_accounts):
    """Seed SSO cascade login patterns (5 platforms in 10 minutes)."""
    from data.models import AuditEvent, EventType

    # Pick a few accounts to simulate rapid cross-platform login
    targets = random.sample(
        [a for a in ad_accounts if a.status == AccountStatus.ACTIVE and not a.is_service_account],
        min(3, len(ad_accounts))
    )

    for account in targets:
        base_time = datetime.now() - timedelta(days=random.randint(1, 7))
        for i, platform in enumerate([Platform.ACTIVE_DIRECTORY, Platform.AWS_IAM, Platform.OKTA]):
            audit_events.append(AuditEvent(
                timestamp=base_time + timedelta(minutes=i * 2),
                event_type=EventType.LOGIN_SUCCESS,
                platform=platform,
                identity_id=account.id,
                username=account.username,
                source_ip="185.220.101." + str(random.randint(1, 255)),  # Tor exit node pattern
                action="sso_cascade_login",
                outcome="success",
                is_anomalous=True,
                details={"login_speed": "suspicious", "geo": "unexpected_country"},
            ))
