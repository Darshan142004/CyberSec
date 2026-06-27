"""Cross-platform identity correlation engine."""

from difflib import SequenceMatcher

from data.models import UnifiedIdentity, Platform
from config import FUZZY_MATCH_THRESHOLD


def resolve_identities(data):
    """Correlate identities across platforms into unified records."""
    all_accounts = []
    for platform_accounts in data["accounts"].values():
        all_accounts.extend(platform_accounts)

    # Phase 1: Exact email matching
    email_groups = {}
    for account in all_accounts:
        if account.email:
            email_groups.setdefault(account.email, []).append(account)

    unified = []
    matched_ids = set()

    for email, accounts in email_groups.items():
        if len(accounts) >= 1:
            identity = _merge_accounts(accounts)
            unified.append(identity)
            for acc in accounts:
                matched_ids.add(acc.id)

    # Phase 2: Fuzzy matching for unmatched accounts
    unmatched = [a for a in all_accounts if a.id not in matched_ids]
    for account in unmatched:
        best_match = _find_fuzzy_match(account, unified)
        if best_match:
            best_match.platform_accounts[account.platform.value] = account
            matched_ids.add(account.id)
        else:
            # Create new unified identity for unmatched
            identity = UnifiedIdentity(
                primary_email=account.email,
                display_name=account.display_name,
                department=account.department,
                title=account.title,
                manager=account.manager,
                platform_accounts={account.platform.value: account},
            )
            unified.append(identity)

    return unified


def _merge_accounts(accounts):
    """Merge multiple platform accounts into a unified identity."""
    primary = accounts[0]
    identity = UnifiedIdentity(
        primary_email=primary.email,
        display_name=primary.display_name,
        department=primary.department,
        title=primary.title,
        manager=primary.manager,
    )

    for account in accounts:
        identity.platform_accounts[account.platform.value] = account
        # Prefer non-empty fields
        if not identity.display_name and account.display_name:
            identity.display_name = account.display_name
        if not identity.department and account.department:
            identity.department = account.department

    return identity


def _find_fuzzy_match(account, unified_list):
    """Find best fuzzy match for an account in existing unified identities."""
    best_score = 0
    best_match = None

    for identity in unified_list:
        score = _compute_similarity(account, identity)
        if score > best_score and score >= FUZZY_MATCH_THRESHOLD:
            best_score = score
            best_match = identity

    return best_match


def _compute_similarity(account, identity):
    """Compute similarity score between an account and a unified identity."""
    scores = []

    # Display name similarity
    if account.display_name and identity.display_name:
        name_score = SequenceMatcher(
            None,
            account.display_name.lower(),
            identity.display_name.lower()
        ).ratio()
        scores.append(name_score * 1.5)  # Weight names higher

    # Username vs display name parts
    if account.username and identity.display_name:
        name_parts = identity.display_name.lower().split()
        username_lower = account.username.lower().replace(".", " ").replace("_", " ")
        for part in name_parts:
            if part in username_lower:
                scores.append(0.6)
                break

    # Department match
    if account.department and identity.department:
        if account.department == identity.department:
            scores.append(0.3)

    return sum(scores) / max(len(scores), 1) if scores else 0
