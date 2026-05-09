"""
state.py — Central state manager (replaces all JSON files).
All data lives in st.session_state so it persists across reruns
within the same browser session.
"""
import random
import string
import streamlit as st
from tth import compute_tth


# ── helpers ────────────────────────────────────────────────

def _generate_code(length: int = 12) -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))


def _generate_random_bits(length: int = 8) -> str:
    return _generate_code(length)


# ── initialise session_state ───────────────────────────────

def init():
    """Call once at the top of every Streamlit page."""
    if "initialised" not in st.session_state:
        st.session_state.initialised = True

        # emails.json  – registered voters
        st.session_state.emails: list[str] = [
            "am.boutria@ensta.edu.dz",
            "am.bouakkaz@ensta.edu.dz",
            "am.khedri@ensta.edu.dz",
        ]

        # emails_backup.json
        st.session_state.emails_backup: list[str] = list(st.session_state.emails)

        # codes.json  – pool of unused {N1, N2} pairs
        st.session_state.codes: list[dict] = []

        # commissioner_data.json
        st.session_state.comm_data: dict = {
            "election_open": False,
            "used_codes": {},   # email → {N1, tth_n2, has_voted, _N2}
        }

        # urne.json  – anonymous ballots (no N1)
        st.session_state.urne: list[dict] = []

        # results.json
        st.session_state.results: dict | None = None


# ── commissioner actions ───────────────────────────────────

def generate_codes():
    """Generate one {N1, N2} pair per remaining email. Saves backup."""
    emails = st.session_state.emails
    st.session_state.emails_backup = list(emails)

    used_n1: set[str] = set()
    codes = []
    # generate a few extra to avoid running out
    for _ in range(len(emails) + 10):
        n1 = _generate_code()
        while n1 in used_n1:
            n1 = _generate_code()
        used_n1.add(n1)
        codes.append({"N1": n1, "N2": _generate_code()})
    st.session_state.codes = codes


def open_election():
    st.session_state.comm_data["election_open"] = True


def close_election():
    st.session_state.comm_data["election_open"] = False


def reset_system():
    """Full reset – restore emails from backup, wipe everything else."""
    st.session_state.emails = list(st.session_state.emails_backup)
    st.session_state.codes = []
    st.session_state.comm_data = {"election_open": False, "used_codes": {}}
    st.session_state.urne = []
    st.session_state.results = None
    # also reset voter wizard state
    for key in list(st.session_state.keys()):
        if key.startswith("voter_"):
            del st.session_state[key]


# ── voter actions ──────────────────────────────────────────

def request_voter_card(email: str) -> tuple[bool, str]:
    """Phase 1: email → assign N1+N2, return them for display."""
    email = email.strip().lower()
    data  = st.session_state.comm_data

    if not data["election_open"]:
        return False, "Election is not open yet."

    used = data["used_codes"]

    # already sent?
    if email in used:
        info = used[email]
        if info["has_voted"]:
            return False, "You have already voted!"
        return True, f"Card already sent. N1={info['N1']}  N2={info['_N2']}"

    # check registered list
    if email not in st.session_state.emails:
        return False, f"'{email}' is not registered. Contact the commissioner."

    codes = st.session_state.codes
    if not codes:
        return False, "No codes available. Contact the commissioner."

    entry = codes.pop(0)
    n1, n2 = entry["N1"], entry["N2"]
    tth_n2 = compute_tth(n2)

    # remove from email list
    st.session_state.emails = [e for e in st.session_state.emails if e != email]

    used[email] = {"N1": n1, "tth_n2": tth_n2, "has_voted": False, "_N2": n2}
    return True, f"OK|{n1}|{n2}"


def verify_voter(n1: str, n2: str) -> tuple[bool, str]:
    data = st.session_state.comm_data
    if not data["election_open"]:
        return False, "Election is not open."
    for email, info in data["used_codes"].items():
        if info["N1"] == n1:
            if info["has_voted"]:
                return False, "You have already voted!"
            if compute_tth(n2) != info["tth_n2"]:
                return False, "N2 is incorrect. Check your email."
            return True, "OK"
    return False, f"N1 '{n1}' not found."


def invalidate_n1(n1: str):
    for email, info in st.session_state.comm_data["used_codes"].items():
        if info["N1"] == n1:
            info["has_voted"] = True
            return


def verify_tth_n2(n2: str) -> bool:
    tth = compute_tth(n2)
    return any(v["tth_n2"] == tth for v in st.session_state.comm_data["used_codes"].values())


# ── anonymizer ─────────────────────────────────────────────

def receive_ballot(ballot: dict) -> tuple[bool, str]:
    n1 = ballot.get("N1", "")
    n2 = ballot.get("N2", "")

    ok, reason = verify_voter(n1, n2)
    if not ok:
        return False, reason

    invalidate_n1(n1)

    anon = {
        "N2":         ballot["N2"],
        "tth_n2":     ballot["tth_n2"],
        "vote":       ballot["vote"],
        "ballot_str": ballot["ballot_str"],
        "signature":  ballot["signature"],
    }
    st.session_state.urne.append(anon)
    return True, "Ballot accepted."


# ── counter ────────────────────────────────────────────────

def count_votes() -> dict:
    from admin import verify_signature

    urne = st.session_state.urne
    results, vote_counts = [], {}
    valid = invalid = 0

    for ballot in urne:
        vote      = ballot["vote"]
        signature = ballot["signature"]
        n2        = ballot["N2"]

        sig_ok = verify_signature(vote, signature)
        n2_ok  = verify_tth_n2(n2)

        if sig_ok and n2_ok:
            results.append({"N2": n2, "vote": vote, "valid": True})
            vote_counts[vote] = vote_counts.get(vote, 0) + 1
            valid += 1
        else:
            reason = "Invalid signature" if not sig_ok else "Invalid N2"
            results.append({"N2": n2, "vote": "?", "valid": False, "reason": reason})
            invalid += 1

    avg = round(sum(r["vote"] for r in results if r["valid"]) / valid, 2) if valid else 0

    output = {
        "summary":        {"total": len(urne), "valid": valid, "invalid": invalid, "average": avg},
        "vote_counts":    vote_counts,
        "public_results": results,
    }
    st.session_state.results = output
    return output


def verify_my_vote(n2: str) -> tuple[bool, str]:
    if not st.session_state.results:
        return False, "Results not available yet."
    for r in st.session_state.results["public_results"]:
        if r["N2"] == n2:
            if r["valid"]:
                return True, f"Your vote ({r['vote']}/10) was counted successfully!"
            return False, f"Your ballot was rejected: {r.get('reason', '')}"
    return False, f"N2 '{n2}' not found in results."


# ── status snapshot ────────────────────────────────────────

def get_status() -> dict:
    data = st.session_state.comm_data
    used = data["used_codes"]
    return {
        "codes_ready":    len(st.session_state.codes) > 0 or len(used) > 0,
        "is_open":        data["election_open"],
        "nb_registered":  len(st.session_state.emails),
        "nb_sent":        len(used),
        "nb_voted":       sum(1 for v in used.values() if v["has_voted"]),
        "urne_size":      len(st.session_state.urne),
        "results_exist":  st.session_state.results is not None,
    }
