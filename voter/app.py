"""
app.py — Electronic Voting System (Streamlit frontend)
Asymmetric Cryptography — ENSTA Alger 2026

All logic runs in Python; no backend server needed beyond `streamlit run app.py`.
"""

import random
import streamlit as st

# ── page config (must be first Streamlit call) ─────────────
st.set_page_config(
    page_title="Electronic Voting System — ENSTA 2026",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── local imports ──────────────────────────────────────────
from state import (
    init, get_status,
    generate_codes, open_election, close_election, reset_system,
    request_voter_card, verify_voter, receive_ballot,
    count_votes, verify_my_vote,
)
from admin import (
    get_valid_k_values, mask_vote, blind_sign,
    unmask_signature, verify_signature,
    N as RSA_N, e as RSA_e, d as RSA_d,
)
from tth import compute_tth

# ── initialise session state ───────────────────────────────
init()

# ══════════════════════════════════════════════════════════
#   GLOBAL CSS
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── palette ── */
:root {
    --bg:      #0a0e14;
    --surface: #0f1520;
    --border:  #1e2d45;
    --accent:  #00d4ff;
    --green:   #00ff9d;
    --orange:  #ff6b35;
    --red:     #ff3b5c;
    --yellow:  #ffd600;
    --muted:   #5a7a9a;
}

/* global bg */
.stApp { background: #0a0e14; }

/* sidebar */
[data-testid="stSidebar"] {
    background: #0f1520 !important;
    border-right: 1px solid #1e2d45;
}
[data-testid="stSidebar"] * { color: #e8f4fd !important; }

/* metric cards */
[data-testid="stMetric"] {
    background: #0f1520;
    border: 1px solid #1e2d45;
    border-radius: 10px;
    padding: 14px 18px !important;
}
[data-testid="stMetricLabel"] { font-size: 11px !important; letter-spacing: 2px; color: #5a7a9a !important; }
[data-testid="stMetricValue"] { color: #00d4ff !important; font-family: monospace; }

/* headings */
h1, h2, h3 { color: #e8f4fd !important; }

/* code / pre */
code, pre { background: #060b12 !important; color: #00ff9d !important; border-radius: 6px; }

/* buttons */
.stButton > button {
    border-radius: 6px !important;
    font-weight: 700 !important;
    transition: all .2s !important;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(0,212,255,.25) !important; }

/* inputs */
input, textarea, select {
    background: #141c2e !important;
    color: #e8f4fd !important;
    border: 1px solid #1e2d45 !important;
    border-radius: 6px !important;
    font-family: monospace !important;
}

/* tabs */
[data-baseweb="tab-list"] { background: #0f1520 !important; border-radius: 8px; }
[data-baseweb="tab"]      { color: #5a7a9a !important; }
[aria-selected="true"]    { color: #00d4ff !important; border-bottom: 2px solid #00d4ff !important; }

/* info / success / error boxes */
.stAlert { border-radius: 8px !important; }

/* dataframe */
[data-testid="stDataFrame"] { border: 1px solid #1e2d45; border-radius: 8px; }

/* divider */
hr { border-color: #1e2d45; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#   HELPER COMPONENTS
# ══════════════════════════════════════════════════════════

def _badge(text: str, color: str = "#00d4ff") -> str:
    return (f'<span style="background:rgba(0,212,255,.1);border:1px solid {color}33;'
            f'color:{color};padding:2px 10px;border-radius:3px;'
            f'font-family:monospace;font-size:12px;font-weight:700">{text}</span>')


def _code_block(text: str):
    st.code(text, language=None)


def _status_row():
    s = get_status()
    cols = st.columns(6)
    cols[0].metric("Registered", s["nb_registered"])
    cols[1].metric("Election", "🟢 OPEN" if s["is_open"] else "🔴 CLOSED")
    cols[2].metric("Cards Sent", s["nb_sent"])
    cols[3].metric("Voted", s["nb_voted"])
    cols[4].metric("Ballot Box", s["urne_size"])
    cols[5].metric("Results", "✅ Ready" if s["results_exist"] else "⏳ Pending")


# ══════════════════════════════════════════════════════════
#   SIDEBAR NAVIGATION
# ══════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🗳️ **EVS**")
    st.caption("Electronic Voting System\nENSTA Alger — 2026")
    st.divider()

    page = st.radio(
        "Navigation",
        ["📊  Dashboard", "👮  Commissioner", "🗳️  Voter", "📮  Ballot Box", "🔢  Counter"],
        label_visibility="collapsed",
    )
    st.divider()

    s = get_status()
    st.markdown("**System Status**")
    st.markdown(f"Gmail config : {'✅' if True else '❌'} Ready")
    st.markdown(f"Codes ready  : {'✅' if s['codes_ready'] else '❌'}")
    st.markdown(f"Election     : {'🟢 OPEN' if s['is_open'] else '🔴 CLOSED'}")
    st.markdown(f"Results      : {'✅' if s['results_exist'] else '⏳'}")

    st.divider()
    st.caption("RSA: N=55  e=27  d=3\nBlind Signature Protocol")


# ══════════════════════════════════════════════════════════
#   PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════

if page == "📊  Dashboard":
    st.title("🗳️ Electronic Voting System")
    st.caption("Asymmetric Cryptography — Blind RSA Signature Protocol — ENSTA Alger 2026")
    st.divider()

    _status_row()
    st.divider()

    s = get_status()

    # Warnings / guidance
    if not s["codes_ready"]:
        st.warning("⚠️  **Step 1:** Commissioner must generate voter codes first.")
    if s["codes_ready"] and not s["is_open"] and not s["results_exist"]:
        st.info("ℹ️  **Step 2:** Commissioner can now open the election.")
    if s["is_open"]:
        st.success("✅ **Election is OPEN** — voters can cast their ballots.")
    if s["urne_size"] > 0 and not s["is_open"] and not s["results_exist"]:
        st.info("ℹ️  **Step 4:** Election closed — go to **Counter** to tally votes.")
    if s["results_exist"]:
        st.success("🏆 **Results are ready!** Go to the Counter page to view them.")
    if not s["codes_ready"] and not s["is_open"]:
        st.info("ℹ️  Start by adding voters in the **Commissioner** tab and generating codes.")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📋 Election Lifecycle")
        _code_block("""\
1. COMMISSIONER  Add voter emails
                 Generate codes (N1 + N2 pairs)
                 Open election

2. VOTER         Enter email → receive N1+N2
                 Enter N1+N2 → identity verified
                 Choose rating (1–10)
                 Blind signature protocol
                 Send ballot to anonymizer

3. COMMISSIONER  Close election

4. COUNTER       Tally votes
                 Publish (N2, vote) pairs

5. ANYONE        Verify own vote with N2""")

    with col2:
        st.markdown("### 🔐 Blind RSA Signature")
        _code_block(f"""\
Parameters:  N={RSA_N}  e={RSA_e}  d={RSA_d}  φ(N)=40
Proof:       {RSA_e}×{RSA_d} mod 40 = {(RSA_e*RSA_d)%40} ✅

VOTER  side:
  m' = vote × k^e mod N   (mask — admin sees m', not vote)
  s  = m'' × k⁻¹ mod N   (unmask)

ADMIN  side:
  m'' = (m')^d mod N      (blind sign)

VERIFY:
  s^e mod N == vote  ✅   (anyone can check)""")


# ══════════════════════════════════════════════════════════
#   PAGE: COMMISSIONER
# ══════════════════════════════════════════════════════════

elif page == "👮  Commissioner":
    st.title("👮 Commissioner Panel")
    st.caption("Manage the election lifecycle: add voters, generate codes, open/close, reset.")
    st.divider()
    _status_row()
    st.divider()

    tab_emails, tab_election, tab_voters, tab_reset = st.tabs([
        "📧 Voter Emails", "⚡ Election Control", "📋 Voter Tracking", "♻️ Reset"
    ])

    # ── Voter Emails ──────────────────────────────────────
    with tab_emails:
        st.subheader("Registered Voter Emails")

        col_add, col_bulk = st.columns(2)
        with col_add:
            st.markdown("**Add a single email**")
            new_email = st.text_input("Email address", placeholder="student@ensta.edu.dz", key="new_email_input")
            if st.button("➕ Add Email", use_container_width=True):
                email = new_email.strip().lower()
                if not email or "@" not in email:
                    st.error("Please enter a valid email address.")
                else:
                    all_known = list(st.session_state.emails) + list(st.session_state.comm_data["used_codes"].keys())
                    if email in all_known:
                        st.warning(f"'{email}' is already registered.")
                    else:
                        st.session_state.emails.append(email)
                        st.success(f"✅ Added: {email}")
                        st.rerun()

        with col_bulk:
            st.markdown("**Bulk import (one per line)**")
            bulk = st.text_area("Emails", placeholder="email1@ensta.edu.dz\nemail2@ensta.edu.dz", height=120, key="bulk_emails")
            if st.button("📥 Import All", use_container_width=True):
                lines = [l.strip().lower() for l in bulk.splitlines() if "@" in l.strip()]
                added = 0
                all_known = list(st.session_state.emails) + list(st.session_state.comm_data["used_codes"].keys())
                for em in lines:
                    if em not in all_known:
                        st.session_state.emails.append(em)
                        added += 1
                st.success(f"✅ Imported {added} new email(s).")
                st.rerun()

        st.divider()
        st.markdown(f"**Registered emails ({len(st.session_state.emails)} remaining)**")
        if st.session_state.emails:
            for em in st.session_state.emails:
                st.markdown(f"- `{em}`")
        else:
            st.caption("No emails remaining (all cards sent).")

    # ── Election Control ──────────────────────────────────
    with tab_election:
        st.subheader("Election Control")
        s = get_status()
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Step 1 — Generate Codes**")
            st.caption(f"{len(st.session_state.emails)} email(s) in the list.")
            if s["is_open"]:
                st.error("Cannot generate codes while election is open.")
            elif not st.session_state.emails:
                st.warning("No emails in the list yet.")
            else:
                if st.button(f"⚙️ Generate {len(st.session_state.emails)} Code Pairs",
                             use_container_width=True, type="primary"):
                    generate_codes()
                    st.success(f"✅ Generated {len(st.session_state.codes)} code pairs.")
                    st.rerun()

        with col2:
            st.markdown("**Step 2 — Open / Close**")
            if s["is_open"]:
                if st.button("🔴 Close Election", use_container_width=True, type="secondary"):
                    close_election()
                    st.success("🔴 Election is now CLOSED.")
                    st.rerun()
            else:
                disabled = not s["codes_ready"]
                if st.button("🟢 Open Election", use_container_width=True,
                             type="primary", disabled=disabled):
                    open_election()
                    st.success("🟢 Election is now OPEN!")
                    st.rerun()
                if disabled:
                    st.caption("Generate codes first.")

        with col3:
            st.markdown("**Current Pool**")
            st.metric("Unused codes", len(st.session_state.codes))
            st.metric("Cards sent", s["nb_sent"])

    # ── Voter Tracking ────────────────────────────────────
    with tab_voters:
        st.subheader("Voter Tracking")
        used = st.session_state.comm_data["used_codes"]
        if not used:
            st.info("No voter cards have been sent yet.")
        else:
            rows = []
            for email, info in used.items():
                rows.append({
                    "Email":   email,
                    "N1":      info["N1"],
                    "Voted":   "✅ Yes" if info["has_voted"] else "⏳ No",
                })
            import pandas as pd
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Reset ─────────────────────────────────────────────
    with tab_reset:
        st.subheader("♻️ Full System Reset")
        st.warning("""
**This will:**
- 🗑️  Delete all votes, codes, and results
- ✅  Restore the voter email list from backup
- ✅  Keep Gmail configuration
        """)
        confirm = st.text_input("Type **RESET** to confirm", key="reset_confirm")
        if st.button("♻️ Reset Now", type="primary", use_container_width=True):
            if confirm == "RESET":
                reset_system()
                st.success("✅ Reset complete! Ready for a new election.")
                st.rerun()
            else:
                st.error("Please type RESET (all caps) to confirm.")


# ══════════════════════════════════════════════════════════
#   PAGE: VOTER
# ══════════════════════════════════════════════════════════

elif page == "🗳️  Voter":
    st.title("🗳️ Voter Portal")
    st.caption("Cast your ballot using the Blind RSA Signature protocol.")
    st.divider()

    s = get_status()
    if not s["is_open"]:
        st.error("❌ The election is not open yet. Please wait for the commissioner to open it.")
        st.stop()

    # ── step tracker ──────────────────────────────────────
    STEPS = ["Email", "Credentials", "Vote", "Blind Sign", "Done"]
    step  = st.session_state.get("voter_step", 1)

    prog_cols = st.columns(len(STEPS))
    for i, (col, label) in enumerate(zip(prog_cols, STEPS), start=1):
        done   = i < step
        active = i == step
        color  = "#00ff9d" if done else ("#00d4ff" if active else "#1e2d45")
        col.markdown(
            f'<div style="text-align:center;padding:8px;border-bottom:2px solid {color};'
            f'color:{"#00ff9d" if done else "#00d4ff" if active else "#5a7a9a"};'
            f'font-size:12px;font-weight:700">'
            f'{"✅ " if done else ""}{i}. {label}</div>',
            unsafe_allow_html=True,
        )
    st.divider()

    # ────────────────────────────────────────────────────
    #   PHASE 1 — Request voter card
    # ────────────────────────────────────────────────────
    if step == 1:
        st.subheader("Phase 1 — Request Your Voter Card")
        st.caption("Enter your registered @ensta.edu.dz email. You will receive N1 and N2 codes.")

        email = st.text_input("Your email address", placeholder="you@ensta.edu.dz", key="voter_email_input")
        if st.button("📧 Request Voter Card", type="primary"):
            if not email:
                st.error("Please enter your email.")
            else:
                ok, msg = request_voter_card(email)
                if not ok:
                    st.error(f"❌ {msg}")
                else:
                    parts = msg.split("|")
                    if parts[0] == "OK":
                        n1, n2 = parts[1], parts[2]
                        st.session_state.voter_email = email
                        st.session_state.voter_n1    = n1
                        st.session_state.voter_n2    = n2
                        st.session_state.voter_step  = 1  # stay on 1 to show inbox
                        st.session_state.voter_card_ready = True
                    else:
                        # already sent
                        st.info(msg)

        # Simulated inbox
        if st.session_state.get("voter_card_ready"):
            st.divider()
            st.success("✅ Voter card sent! Check your simulated inbox below.")
            n1 = st.session_state.voter_n1
            n2 = st.session_state.voter_n2
            em = st.session_state.voter_email
            _code_block(f"""\
FROM :  voting-system@ensta.edu.dz
TO   :  {em}
SUBJ :  Your Voter Card — ENSTA 2026
─────────────────────────────────────────────
        ★  KEEP THIS EMAIL CONFIDENTIAL  ★
─────────────────────────────────────────────

  N1  =  {n1}
  N2  =  {n2}

  ⚠  Do NOT share these codes with anyone.
  ⚠  Keep N2 to verify your vote later.
─────────────────────────────────────────────""")
            if st.button("✅ I have my N1 and N2 — Continue →", type="primary"):
                st.session_state.voter_step = 2
                st.rerun()

    # ────────────────────────────────────────────────────
    #   PHASE 2 — Enter credentials
    # ────────────────────────────────────────────────────
    elif step == 2:
        st.subheader("Phase 2 — Enter Your Credentials")
        st.caption("Type the N1 and N2 codes from your email exactly as shown.")

        col1, col2 = st.columns(2)
        n1_input = col1.text_input("N1 code", value=st.session_state.get("voter_n1",""),
                                   placeholder="ABC123DEF456", key="input_n1")
        n2_input = col2.text_input("N2 code", value=st.session_state.get("voter_n2",""),
                                   placeholder="XYZ789GHI012", key="input_n2")

        if st.button("🔐 Verify Identity", type="primary"):
            n1 = n1_input.strip().upper()
            n2 = n2_input.strip().upper()
            if not n1 or not n2:
                st.error("Both N1 and N2 are required.")
            else:
                ok, msg = verify_voter(n1, n2)
                if not ok:
                    st.error(f"❌ Access Denied: {msg}")
                else:
                    st.success("✅ Identity verified!")
                    st.session_state.voter_n1   = n1
                    st.session_state.voter_n2   = n2
                    st.session_state.voter_step = 3
                    st.rerun()

    # ────────────────────────────────────────────────────
    #   PHASE 3 — Choose vote
    # ────────────────────────────────────────────────────
    elif step == 3:
        st.subheader("Phase 3 — Choose Your Rating")
        st.caption("Rate the Asymmetric Cryptography course from 1 to 10.")

        vote = st.select_slider(
            "Your rating",
            options=list(range(1, 11)),
            value=st.session_state.get("voter_vote", 5),
            format_func=lambda v: f"{v}/10  {'★'*v}{'☆'*(10-v)}",
            key="voter_vote_slider",
        )
        st.session_state.voter_vote = vote

        st.markdown(f"### Your selection: **{vote}/10** {'★'*vote}")
        col1, col2 = st.columns([1, 4])
        if col1.button("← Back", key="back_3"):
            st.session_state.voter_step = 2
            st.rerun()
        if col2.button("Confirm Rating → Blind Signature", type="primary"):
            st.session_state.voter_step = 4
            st.rerun()

    # ────────────────────────────────────────────────────
    #   PHASE 4 — Blind Signature
    # ────────────────────────────────────────────────────
    elif step == 4:
        st.subheader("Phase 4 — Blind Signature Protocol")
        st.caption(f"RSA: N={RSA_N}, e={RSA_e}, d={RSA_d}  |  The admin signs your vote WITHOUT seeing it.")

        vote = st.session_state.voter_vote
        valid_ks = get_valid_k_values()
        if "voter_k" not in st.session_state:
            st.session_state.voter_k = random.choice(valid_ks)
        k = st.session_state.voter_k

        # ── Step A: mask ──────────────────────────────
        st.markdown("#### 🎭 Step A — Voter masks the vote")
        m_prime = mask_vote(vote, k)
        st.session_state.voter_m_prime = m_prime
        _code_block(f"""\
vote = {vote}   k = {k}   (random, coprime with N={RSA_N})

m' = vote × k^e  mod N
   = {vote}  ×  {k}^{RSA_e}  mod {RSA_N}
   = {m_prime}

→ Admin receives m'={m_prime}  (cannot see vote={vote}!)""")

        # ── Step B: admin blind signs ─────────────────
        st.markdown("#### ✍️ Step B — Admin signs blindly")
        m_double_prime = blind_sign(m_prime)
        st.session_state.voter_m_double_prime = m_double_prime
        _code_block(f"""\
m'' = (m')^d  mod N
    = {m_prime}^{RSA_d}  mod {RSA_N}
    = {m_double_prime}

→ Admin returns m''={m_double_prime}  (still did not see vote={vote}!)""")

        # ── Step C: unmask ────────────────────────────
        st.markdown("#### 🔓 Step C — Voter unmasks signature")
        from admin import mod_inverse
        k_inv = mod_inverse(k, RSA_N)
        s     = unmask_signature(m_double_prime, k)
        st.session_state.voter_signature = s
        _code_block(f"""\
k⁻¹ = {k_inv}   (modular inverse of k={k})

s = m'' × k⁻¹  mod N
  = {m_double_prime} × {k_inv}  mod {RSA_N}
  = {s}

s is the real RSA signature of vote={vote} (vote^d mod N)""")

        # ── Step D: verify ────────────────────────────
        st.markdown("#### ✅ Step D — Verify signature")
        valid = verify_signature(vote, s)
        check = pow(s, RSA_e, RSA_N)
        if valid:
            _code_block(f"""\
s^e  mod N  =  {s}^{RSA_e}  mod {RSA_N}  =  {check}  ==  {vote}  ✅  VALID""")
            st.success("Signature is valid! Ready to send ballot.")
        else:
            _code_block(f"""\
s^e  mod N  =  {s}^{RSA_e}  mod {RSA_N}  =  {check}  ≠  {vote}  ❌  INVALID""")
            st.error("Signature invalid! Ballot rejected.")
            st.stop()

        col1, col2 = st.columns([1, 4])
        if col1.button("← Back", key="back_4"):
            st.session_state.voter_step = 3
            del st.session_state["voter_k"]
            st.rerun()
        if col2.button("📮 Send Ballot to Anonymizer →", type="primary", disabled=not valid):
            # build ballot
            import string as _str
            random_bits = ''.join(random.choices(_str.ascii_uppercase + _str.digits, k=8))
            n1  = st.session_state.voter_n1
            n2  = st.session_state.voter_n2
            tth = compute_tth(n2)
            ballot = {
                "N1":          n1,
                "N2":          n2,
                "tth_n2":      tth,
                "vote":        vote,
                "random_bits": random_bits,
                "ballot_str":  f"{vote}|{n2}|{random_bits}",
                "signature":   s,
            }
            ok, msg = receive_ballot(ballot)
            if ok:
                st.session_state.voter_step        = 5
                st.session_state.voter_random_bits = random_bits
                st.session_state.voter_tth         = tth
                st.rerun()
            else:
                st.error(f"❌ Anonymizer rejected ballot: {msg}")

    # ────────────────────────────────────────────────────
    #   PHASE 5 — Done
    # ────────────────────────────────────────────────────
    elif step == 5:
        st.balloons()
        st.subheader("✅ Vote Submitted Successfully!")

        vote = st.session_state.voter_vote
        k    = st.session_state.voter_k
        mp   = st.session_state.voter_m_prime
        mpp  = st.session_state.voter_m_double_prime
        s    = st.session_state.voter_signature
        n2   = st.session_state.voter_n2

        _code_block(f"""\
╔══════════════════════════════════════════════╗
║         VOTE SUBMITTED SUCCESSFULLY          ║
╚══════════════════════════════════════════════╝

  Vote          : {vote}/10  {'★'*vote}
  k  (masking)  : {k}
  m' (masked)   : {mp}      ← what admin saw
  m'' (signed)  : {mpp}
  s  (signature): {s}
  Verify        : {s}^{RSA_e} mod {RSA_N} = {pow(s,RSA_e,RSA_N)} == {vote} ✅

  N2  (keep it!): {n2}

  Use N2 in the Counter page to verify your vote
  was counted after the election closes.""")

        st.info(f"💡 **Important:** save your N2 code:  `{n2}`  — you can use it later to verify your vote was counted.")

        if st.button("🔄 New voter session", type="secondary"):
            for key in list(st.session_state.keys()):
                if key.startswith("voter_"):
                    del st.session_state[key]
            st.rerun()


# ══════════════════════════════════════════════════════════
#   PAGE: BALLOT BOX (ANONYMIZER)
# ══════════════════════════════════════════════════════════

elif page == "📮  Ballot Box":
    st.title("📮 Ballot Box — Anonymizer")
    st.caption("Anonymous ballots stored after removing N1. No link between ballot and voter identity.")
    st.divider()

    urne = st.session_state.urne
    st.metric("Ballots in the box", len(urne))
    st.info("🔒 Anonymity guaranteed — N1 is **never** stored in the ballot box.")
    st.divider()

    if not urne:
        st.warning("The ballot box is empty.")
    else:
        for i, b in enumerate(urne, 1):
            with st.expander(f"Ballot #{i}", expanded=False):
                _code_block(f"""\
N2          : {b['N2']}
TTH(N2)     : {b['tth_n2'][:40]}...
ballot_str  : {b['ballot_str']}
signature   : {b['signature']}
vote        : {b['vote']}/10  (visible for counting)""")


# ══════════════════════════════════════════════════════════
#   PAGE: COUNTER
# ══════════════════════════════════════════════════════════

elif page == "🔢  Counter":
    st.title("🔢 Vote Counter")
    st.caption("Tally votes after the election closes. Verify signatures and publish (N2, vote) pairs.")
    st.divider()

    s = get_status()

    if s["is_open"]:
        st.error("❌ Election is still OPEN. Close it first (Commissioner → Election Control).")
        st.stop()

    col_tally, col_verify = st.columns([2, 1])

    with col_tally:
        st.subheader("Tally Votes")
        if s["urne_size"] == 0:
            st.warning("No ballots in the box yet.")
        else:
            if st.button("🔢 Run Counting (Dépouillement)", type="primary", use_container_width=True):
                results = count_votes()
                st.success("✅ Counting complete!")
                st.rerun()

    with col_verify:
        st.subheader("Verify My Vote")
        n2_input = st.text_input("Enter your N2 code", placeholder="ABC123...")
        if st.button("🔍 Verify", use_container_width=True):
            ok, msg = verify_my_vote(n2_input.strip().upper())
            if ok:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")

    # ── Results ───────────────────────────────────────────
    if st.session_state.results:
        st.divider()
        st.subheader("📊 Election Results")
        r = st.session_state.results
        s_data = r["summary"]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Ballots", s_data["total"])
        c2.metric("Valid Votes",   s_data["valid"])
        c3.metric("Rejected",      s_data["invalid"])
        c4.metric("Average Grade", f"{s_data['average']}/10")

        st.divider()
        st.markdown("**Breakdown by grade**")
        vc = r["vote_counts"]
        if vc:
            import pandas as pd
            df = pd.DataFrame(
                [(g, c, "★"*g) for g, c in sorted(vc.items())],
                columns=["Grade", "Votes", "Stars"]
            )
            st.bar_chart(df.set_index("Grade")["Votes"])
            st.dataframe(df, hide_index=True, use_container_width=True)

        st.divider()
        st.markdown("**Public verification — (N2, vote) pairs**")
        rows = []
        for i, rec in enumerate(r["public_results"], 1):
            rows.append({
                "#":      i,
                "N2":     rec["N2"],
                "Vote":   rec["vote"],
                "Status": "✅ Counted" if rec["valid"] else f"❌ Rejected ({rec.get('reason','')})",
            })
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
