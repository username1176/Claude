"""ZeroTax AI — State Filing Portals & LLC Data
Comprehensive registry of all 50 states + DC for business formation links,
annual report fees, and filing deadlines.
"""

STATE_PORTALS: dict[str, dict] = {
    "AL": {"name": "Alabama",      "sos": "https://www.sos.alabama.gov/business-services",          "llc_fee": 200,  "annual_fee": 100,  "annual_due": "April 15",    "income_tax": 5.0,  "no_income_tax": False},
    "AK": {"name": "Alaska",       "sos": "https://www.commerce.alaska.gov/web/cbpl/businesslicensing","llc_fee": 250,  "annual_fee": 100,  "annual_due": "Jan 2",       "income_tax": 0.0,  "no_income_tax": True},
    "AZ": {"name": "Arizona",      "sos": "https://azcc.gov/business-services/",                    "llc_fee": 50,   "annual_fee": 0,    "annual_due": "N/A",         "income_tax": 2.5,  "no_income_tax": False},
    "AR": {"name": "Arkansas",     "sos": "https://www.sos.arkansas.gov/business-commercial-services","llc_fee": 50,  "annual_fee": 150,  "annual_due": "May 1",       "income_tax": 4.4,  "no_income_tax": False},
    "CA": {"name": "California",   "sos": "https://bizfileonline.sos.ca.gov/",                      "llc_fee": 70,   "annual_fee": 800,  "annual_due": "April 15",    "income_tax": 13.3, "no_income_tax": False},
    "CO": {"name": "Colorado",     "sos": "https://www.sos.state.co.us/biz/BusinessEntityCriteriaExt.do","llc_fee": 50,"annual_fee": 10,  "annual_due": "Anniversary", "income_tax": 4.4,  "no_income_tax": False},
    "CT": {"name": "Connecticut",  "sos": "https://www.concord-sots.ct.gov/CONCORD/",               "llc_fee": 120,  "annual_fee": 80,   "annual_due": "March 31",    "income_tax": 6.99, "no_income_tax": False},
    "DE": {"name": "Delaware",     "sos": "https://icis.corp.delaware.gov/Ecorp/",                  "llc_fee": 90,   "annual_fee": 300,  "annual_due": "June 1",      "income_tax": 6.6,  "no_income_tax": False},
    "FL": {"name": "Florida",      "sos": "https://dos.myflorida.com/sunbiz/",                      "llc_fee": 125,  "annual_fee": 138,  "annual_due": "May 1",       "income_tax": 0.0,  "no_income_tax": True},
    "GA": {"name": "Georgia",      "sos": "https://sos.ga.gov/index.php/corporations",              "llc_fee": 100,  "annual_fee": 50,   "annual_due": "April 1",     "income_tax": 5.49, "no_income_tax": False},
    "HI": {"name": "Hawaii",       "sos": "https://www.ehawaiigov.org/selfservice/",                "llc_fee": 50,   "annual_fee": 15,   "annual_due": "March 31",    "income_tax": 11.0, "no_income_tax": False},
    "ID": {"name": "Idaho",        "sos": "https://sos.idaho.gov/business/",                        "llc_fee": 100,  "annual_fee": 0,    "annual_due": "N/A",         "income_tax": 5.8,  "no_income_tax": False},
    "IL": {"name": "Illinois",     "sos": "https://www.ilsos.gov/departments/business_services/",   "llc_fee": 150,  "annual_fee": 75,   "annual_due": "Anniversary", "income_tax": 4.95, "no_income_tax": False},
    "IN": {"name": "Indiana",      "sos": "https://inbiz.in.gov/",                                  "llc_fee": 95,   "annual_fee": 32,   "annual_due": "Anniversary", "income_tax": 3.05, "no_income_tax": False},
    "IA": {"name": "Iowa",         "sos": "https://sos.iowa.gov/business/",                         "llc_fee": 50,   "annual_fee": 60,   "annual_due": "April 1",     "income_tax": 6.0,  "no_income_tax": False},
    "KS": {"name": "Kansas",       "sos": "https://www.sos.ks.gov/business/",                       "llc_fee": 160,  "annual_fee": 55,   "annual_due": "April 15",    "income_tax": 5.7,  "no_income_tax": False},
    "KY": {"name": "Kentucky",     "sos": "https://www.sos.ky.gov/bus/business-filings/",           "llc_fee": 40,   "annual_fee": 15,   "annual_due": "June 30",     "income_tax": 5.0,  "no_income_tax": False},
    "LA": {"name": "Louisiana",    "sos": "https://www.sos.la.gov/BusinessServices/",               "llc_fee": 100,  "annual_fee": 35,   "annual_due": "Anniversary", "income_tax": 4.25, "no_income_tax": False},
    "ME": {"name": "Maine",        "sos": "https://www.maine.gov/sos/cec/corp/",                    "llc_fee": 175,  "annual_fee": 85,   "annual_due": "June 1",      "income_tax": 7.15, "no_income_tax": False},
    "MD": {"name": "Maryland",     "sos": "https://egos.dat.maryland.gov/",                         "llc_fee": 100,  "annual_fee": 300,  "annual_due": "April 15",    "income_tax": 5.75, "no_income_tax": False},
    "MA": {"name": "Massachusetts","sos": "https://corp.sec.state.ma.us/CorpWeb/",                  "llc_fee": 500,  "annual_fee": 500,  "annual_due": "Anniversary", "income_tax": 9.0,  "no_income_tax": False},
    "MI": {"name": "Michigan",     "sos": "https://www.michigan.gov/sos/corporations",              "llc_fee": 50,   "annual_fee": 25,   "annual_due": "Feb 15",      "income_tax": 4.25, "no_income_tax": False},
    "MN": {"name": "Minnesota",    "sos": "https://www.sos.state.mn.us/business-liens/",            "llc_fee": 155,  "annual_fee": 0,    "annual_due": "N/A",         "income_tax": 9.85, "no_income_tax": False},
    "MS": {"name": "Mississippi",  "sos": "https://www.sos.ms.gov/business-services",               "llc_fee": 50,   "annual_fee": 0,    "annual_due": "N/A",         "income_tax": 4.7,  "no_income_tax": False},
    "MO": {"name": "Missouri",     "sos": "https://www.sos.mo.gov/business/corporations/",          "llc_fee": 50,   "annual_fee": 45,   "annual_due": "Anniversary", "income_tax": 4.95, "no_income_tax": False},
    "MT": {"name": "Montana",      "sos": "https://biz.mt.gov/",                                   "llc_fee": 70,   "annual_fee": 20,   "annual_due": "April 15",    "income_tax": 6.75, "no_income_tax": False},
    "NE": {"name": "Nebraska",     "sos": "https://www.nebraska.gov/sos/corp/",                     "llc_fee": 100,  "annual_fee": 26,   "annual_due": "April 1",     "income_tax": 6.64, "no_income_tax": False},
    "NV": {"name": "Nevada",       "sos": "https://esos.nv.gov/EntitySearch/",                      "llc_fee": 425,  "annual_fee": 350,  "annual_due": "Anniversary", "income_tax": 0.0,  "no_income_tax": True},
    "NH": {"name": "New Hampshire","sos": "https://www.sos.nh.gov/corporations-division",           "llc_fee": 100,  "annual_fee": 100,  "annual_due": "April 1",     "income_tax": 0.0,  "no_income_tax": True},
    "NJ": {"name": "New Jersey",   "sos": "https://www.njportal.com/dor/businessregistration",      "llc_fee": 125,  "annual_fee": 75,   "annual_due": "Anniversary", "income_tax": 10.75,"no_income_tax": False},
    "NM": {"name": "New Mexico",   "sos": "https://portal.sos.state.nm.us/BFS/",                   "llc_fee": 50,   "annual_fee": 0,    "annual_due": "N/A",         "income_tax": 5.9,  "no_income_tax": False},
    "NY": {"name": "New York",     "sos": "https://www.dos.ny.gov/corps/",                          "llc_fee": 200,  "annual_fee": 9,    "annual_due": "Anniversary", "income_tax": 10.9, "no_income_tax": False},
    "NC": {"name": "North Carolina","sos":"https://www.sosnc.gov/online_services/business_registration","llc_fee": 125,"annual_fee": 202, "annual_due": "April 15",    "income_tax": 4.5,  "no_income_tax": False},
    "ND": {"name": "North Dakota", "sos": "https://sos.nd.gov/business/business-services",          "llc_fee": 135,  "annual_fee": 50,   "annual_due": "Nov 15",      "income_tax": 2.5,  "no_income_tax": False},
    "OH": {"name": "Ohio",         "sos": "https://www.ohiosos.gov/businesses/",                    "llc_fee": 99,   "annual_fee": 0,    "annual_due": "N/A",         "income_tax": 3.99, "no_income_tax": False},
    "OK": {"name": "Oklahoma",     "sos": "https://www.sos.ok.gov/corp/corpInformation.aspx",       "llc_fee": 100,  "annual_fee": 25,   "annual_due": "Anniversary", "income_tax": 4.75, "no_income_tax": False},
    "OR": {"name": "Oregon",       "sos": "https://sos.oregon.gov/business/pages/register.aspx",    "llc_fee": 100,  "annual_fee": 100,  "annual_due": "Anniversary", "income_tax": 9.9,  "no_income_tax": False},
    "PA": {"name": "Pennsylvania", "sos": "https://www.dos.pa.gov/BusinessCharities/Business/",     "llc_fee": 125,  "annual_fee": 7,    "annual_due": "Anniversary", "income_tax": 3.07, "no_income_tax": False},
    "RI": {"name": "Rhode Island", "sos": "https://www.sos.ri.gov/divisions/business-services",     "llc_fee": 150,  "annual_fee": 50,   "annual_due": "Nov 1",       "income_tax": 5.99, "no_income_tax": False},
    "SC": {"name": "South Carolina","sos":"https://www.sos.sc.gov/business",                        "llc_fee": 110,  "annual_fee": 0,    "annual_due": "N/A",         "income_tax": 7.0,  "no_income_tax": False},
    "SD": {"name": "South Dakota", "sos": "https://sosenterprise.sd.gov/BusinessServices/",         "llc_fee": 150,  "annual_fee": 50,   "annual_due": "Anniversary", "income_tax": 0.0,  "no_income_tax": True},
    "TN": {"name": "Tennessee",    "sos": "https://tnbear.tn.gov/",                                 "llc_fee": 300,  "annual_fee": 300,  "annual_due": "Anniversary", "income_tax": 0.0,  "no_income_tax": True},
    "TX": {"name": "Texas",        "sos": "https://www.sos.state.tx.us/corp/index.shtml",           "llc_fee": 300,  "annual_fee": 0,    "annual_due": "N/A",         "income_tax": 0.0,  "no_income_tax": True},
    "UT": {"name": "Utah",         "sos": "https://secure.utah.gov/bes/index.html",                 "llc_fee": 54,   "annual_fee": 18,   "annual_due": "Anniversary", "income_tax": 4.55, "no_income_tax": False},
    "VT": {"name": "Vermont",      "sos": "https://sos.vermont.gov/corporations/",                  "llc_fee": 125,  "annual_fee": 35,   "annual_due": "Anniversary", "income_tax": 8.75, "no_income_tax": False},
    "VA": {"name": "Virginia",     "sos": "https://cis.scc.virginia.gov/",                          "llc_fee": 100,  "annual_fee": 50,   "annual_due": "Anniversary", "income_tax": 5.75, "no_income_tax": False},
    "WA": {"name": "Washington",   "sos": "https://www.sos.wa.gov/corps/",                          "llc_fee": 200,  "annual_fee": 60,   "annual_due": "Anniversary", "income_tax": 0.0,  "no_income_tax": True},
    "WV": {"name": "West Virginia","sos": "https://apps.wv.gov/sos/businessentities/",              "llc_fee": 100,  "annual_fee": 25,   "annual_due": "July 1",      "income_tax": 6.5,  "no_income_tax": False},
    "WI": {"name": "Wisconsin",    "sos": "https://www.wdfi.org/corporations/",                     "llc_fee": 130,  "annual_fee": 25,   "annual_due": "March 31",    "income_tax": 7.65, "no_income_tax": False},
    "WY": {"name": "Wyoming",      "sos": "https://wyobiz.wyo.gov/",                                "llc_fee": 100,  "annual_fee": 60,   "annual_due": "Anniversary", "income_tax": 0.0,  "no_income_tax": True},
    "DC": {"name": "Washington DC","sos": "https://dcra.dc.gov/service/business-registration",      "llc_fee": 220,  "annual_fee": 300,  "annual_due": "April 1",     "income_tax": 10.75,"no_income_tax": False},
}

NO_INCOME_TAX_STATES = [s for s, d in STATE_PORTALS.items() if d["no_income_tax"]]

# Best states for holding companies / low-tax formation
FAVORABLE_FORMATION_STATES = {
    "WY": "No state income tax, strong LLC charging-order protection, low fees, privacy-friendly",
    "DE": "Gold standard for corporations; Court of Chancery, precedent-rich business law",
    "NV": "No state income tax, no disclosure of officers/directors, strong asset protection",
    "SD": "No income tax, no inheritance tax, favorable trust law (South Dakota dynasty trusts)",
    "FL": "No income tax, homestead exemption, large business-friendly court system",
    "TX": "No income tax, no franchise tax for most small businesses, business-friendly courts",
}

ATTORNEY_REFERRAL_TEMPLATE = """
ATTORNEY REFERRAL & ENGAGEMENT LETTER TEMPLATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[YOUR NAME]
[ADDRESS]
[CITY, STATE ZIP]
[DATE]

RE: Tax Strategy Implementation — Initial Consultation Request

Dear [Attorney Name]:

I am writing to request an initial consultation regarding the implementation
of several tax planning strategies identified through a comprehensive financial
analysis of my business.

BUSINESS OVERVIEW
─────────────────
Entity Type:    [CURRENT ENTITY]
Annual Revenue: [REVENUE]
Annual Profit:  [PROFIT]
State:          [STATE]

STRATEGIES REQUIRING LEGAL ASSISTANCE
──────────────────────────────────────
The following strategies identified in my tax analysis require attorney-level
review and implementation assistance:

□  [Strategy 1] — Estimated value: $[X]/year
   Relevant code sections: [IRC SECTIONS]

□  [Strategy 2] — Estimated value: $[X]/year
   Relevant code sections: [IRC SECTIONS]

□  [Strategy 3] — Estimated value: $[X]/year
   Relevant code sections: [IRC SECTIONS]

DOCUMENTS TO REVIEW
───────────────────
Please find attached:
1. ZeroTax AI Tax Analysis Report (AI-generated — for reference only)
2. Current entity formation documents
3. Most recent tax returns (3 years)
4. Current operating agreements

QUESTIONS FOR CONSULTATION
───────────────────────────
1. Which strategies are appropriate given my specific circumstances?
2. What is the timeline and estimated cost to implement each?
3. Are there any state-specific issues in [STATE] I should be aware of?
4. What documentation will I need to maintain for IRS audit protection?

I understand that the enclosed AI-generated report is not legal advice and
that your professional review is essential before implementing any strategy.

Please contact me at [EMAIL] or [PHONE] to schedule a consultation.

Respectfully,

[YOUR NAME]
[SIGNATURE]

DISCLAIMER: This letter template was generated by ZeroTax AI. It is provided
as a drafting aid only and does not constitute legal advice. Consult a licensed
tax attorney before taking any action.
"""


def get_state_info(state_code: str) -> dict:
    return STATE_PORTALS.get(state_code.upper(), {
        "name": state_code,
        "sos": "https://www.sos.gov",
        "llc_fee": 0,
        "annual_fee": 0,
        "annual_due": "Varies",
        "income_tax": 0.0,
        "no_income_tax": False,
    })


def get_formation_recommendation(state_code: str, net_worth: float) -> str:
    """Return a formation jurisdiction recommendation."""
    state = state_code.upper()
    current_state = STATE_PORTALS.get(state, {})
    current_tax = current_state.get("income_tax", 5.0)

    if current_tax == 0:
        return f"✅ **{current_state.get('name', state)}** has no state income tax — forming here is likely optimal."
    elif net_worth > 2_000_000:
        return (
            "⚡ **Wyoming** or **South Dakota** recommended for holding company: "
            "strong asset protection, no income tax, favorable trust law."
        )
    elif net_worth > 500_000:
        return (
            "⚡ **Wyoming LLC** recommended for asset holding: "
            "charging-order-only protection, no income tax, $100 formation fee."
        )
    else:
        return (
            f"Form in **{current_state.get('name', state)}** (home state) for simplicity. "
            f"Consider **Wyoming** holding company when net worth exceeds $500K."
        )
