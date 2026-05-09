# 🗳️ Electronic Voting System — ENSTA Alger 2026
## Blind RSA Signature Protocol

### Files
```
evs_app/
├── app.py          ← Streamlit UI (run this)
├── admin.py        ← RSA blind signature logic
├── tth.py          ← Toy Tetragraph Hash (Merkle + SHA-256)
├── state.py        ← In-memory state manager (no JSON files needed)
└── requirements.txt
```

### Install & Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
Then open http://localhost:8501 in your browser.

### Quick Demo Flow
1. **Commissioner** tab → Generate Codes → Open Election
2. **Voter** tab → Enter email → Get N1+N2 → Vote → Blind Sign
3. **Commissioner** tab → Close Election
4. **Counter** tab → Run Counting → View Results → Verify with N2

### RSA Parameters
- N=55, e=27, d=3, φ(N)=40
- Blind signature: m' = vote × k^e mod N  →  m'' = (m')^d mod N  →  s = m'' × k⁻¹ mod N
- Verify: s^e mod N == vote ✅
