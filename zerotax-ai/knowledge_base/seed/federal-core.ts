// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Federal Core Seed Data
// Pre-written knowledge base entries for the most important IRC sections.
// These are ingested on first run without requiring external API calls.
// Source: Internal Revenue Code, Treasury Regulations, and IRS guidance
// as of tax year 2025 / OBBBA (One Big Beautiful Bill Act).
// ─────────────────────────────────────────────────────────────────────────────

export interface SeedChunk {
  title: string;
  content: string;
  source_type: string;
  jurisdiction: string;
  document_number: string | null;
  document_title: string | null;
  url: string | null;
  effective_date: string | null;
  impact_score: number;
}

export const FEDERAL_SEED_CHUNKS: SeedChunk[] = [
  // ── S-Corporation Election ─────────────────────────────────────────────────
  {
    title: "S-Corporation Election — IRC §§ 1361–1379 and SE Tax Savings",
    source_type: "irc_section",
    jurisdiction: "federal",
    document_number: "IRC §§ 1361–1379",
    document_title: "Subchapter S — Tax Treatment of S Corporations and Their Shareholders",
    url: "https://www.irs.gov/businesses/small-businesses-self-employed/s-corporations",
    effective_date: "2025-01-01",
    impact_score: 9,
    content: `S-Corporation (S-Corp) election under IRC §§ 1361–1379 is the single most impactful tax strategy for profitable sole proprietors and single-member LLCs earning $60,000+ in net profit.

HOW IT WORKS: An LLC or corporation elects S-Corp tax treatment by filing Form 2553. The business income is then split into two components: (1) reasonable W-2 salary to the owner-employee, and (2) pass-through distributions. Only the W-2 salary is subject to self-employment (FICA) tax at 15.3% (up to $176,100 in 2025) and 2.9% above that. Distributions completely avoid self-employment tax.

EXAMPLE SAVINGS: Net profit = $200,000. Reasonable salary set at $80,000. SE tax applies only to $80,000 (saving $18,360 in SE tax vs. sole prop paying SE tax on all $200,000). After accounting for payroll costs (~$3,000), net savings ≈ $15,000/year.

REASONABLE SALARY: Per Rev. Rul. 59-221 and Treasury Reg. § 31.3121(d)-1(c), the IRS requires S-Corp owners to pay themselves a "reasonable" salary comparable to what a third party would earn for the same services. Setting salary too low invites IRS reclassification. Rule of thumb: 40–60% of net profit, or match industry compensation data.

QUALIFICATION REQUIREMENTS (IRC § 1361):
- Domestic corporation only
- Maximum 100 shareholders
- Only one class of stock
- Shareholders must be US citizens/residents, estates, or certain trusts
- Cannot be a financial institution, insurance company, or certain other entities

FILING: Form 2553 must be filed within 2 months and 15 days of the beginning of the tax year for which the election is to be effective, or at any time during the preceding tax year. Late election relief is available under Rev. Proc. 2013-30.

COMBINED WITH QBI: S-Corp income may also qualify for the Section 199A QBI deduction (20% of qualified business income), further reducing effective tax rate. For SSTB (specified service trade or business) owners with income above the threshold, QBI deduction phases out — S-Corp election still saves SE tax but QBI benefit is limited.`,
  },

  // ── Section 199A QBI Deduction ─────────────────────────────────────────────
  {
    title: "Section 199A — 20% Qualified Business Income (QBI) Deduction",
    source_type: "irc_section",
    jurisdiction: "federal",
    document_number: "IRC § 199A",
    document_title: "Deduction for Qualified Business Income (OBBBA: Made Permanent)",
    url: "https://www.irs.gov/newsroom/tax-cuts-and-jobs-act-provision-11011-section-199a-qualified-business-income-deduction-faqs",
    effective_date: "2025-01-01",
    impact_score: 9,
    content: `Section 199A provides a deduction of up to 20% of qualified business income (QBI) from pass-through entities (sole proprietorships, partnerships, S-Corps, LLCs). The One Big Beautiful Bill Act (OBBBA) made this provision permanent (previously set to expire 12/31/2025).

BASIC CALCULATION: Deduction = lesser of (a) 20% × QBI, or (b) 20% × (ordinary taxable income minus net capital gain).

WAGE/PROPERTY LIMITATION (for income above 2025 thresholds of $197,300 single / $394,600 MFJ): The deduction is limited to the greater of: (i) 50% of W-2 wages paid by the business, or (ii) 25% of W-2 wages + 2.5% of unadjusted basis of qualified property.

SSTB PHASE-OUT: For "Specified Service Trades or Businesses" (law, accounting, health, consulting, financial services, athletics, performing arts, brokerage), the deduction phases out for income between $197,300–$247,300 (single) and $394,600–$494,600 (MFJ) for 2025. Above these thresholds, SSTB owners get NO QBI deduction.

STRATEGY: Business owners near the SSTB phase-out can maximize the deduction by: (1) increasing W-2 wages to meet the wage test, (2) contributing to retirement plans to reduce taxable income below the threshold, or (3) restructuring to separate SSTB and non-SSTB activities.

EXAMPLE: Sole proprietor with $300,000 QBI (non-SSTB), income above phase-out. W-2 wages paid to employees: $120,000. Deduction = 50% × $120,000 = $60,000. At 37% marginal rate, this saves $22,200/year.

PLANNING NOTE: S-Corp owners' W-2 salary counts toward the business's W-2 wages for the wage test, meaning S-Corp election and QBI deduction are complementary strategies (Rev. Proc. 2019-11).`,
  },

  // ── Defined Benefit Pension Plans ──────────────────────────────────────────
  {
    title: "Defined Benefit Pension Plans — IRC §§ 412, 415, 404: Shelter Up to $275,000/Year",
    source_type: "irc_section",
    jurisdiction: "federal",
    document_number: "IRC §§ 412, 415, 404",
    document_title: "Defined Benefit Plans — Funding and Contribution Limits",
    url: "https://www.irs.gov/retirement-plans/defined-benefit-plan",
    effective_date: "2025-01-01",
    impact_score: 8,
    content: `A Defined Benefit (DB) pension plan is the most powerful retirement contribution vehicle available to self-employed individuals and small business owners with high income. Unlike 401(k) plans capped at $70,000/year, a DB plan can allow annual contributions of $150,000–$275,000 or more, all tax-deductible.

HOW IT WORKS: A DB plan promises a specific monthly benefit at retirement (typically calculated as a percentage of final salary). The required annual contribution is actuarially calculated to fund that future benefit. For a business owner near retirement (50+), the required contribution can be very large, providing enormous deductions.

2025 LIMITS (IRC § 415): The maximum annual benefit payable from a DB plan is the lesser of (1) $280,000 (2025, indexed for inflation), or (2) 100% of the participant's average compensation for the highest 3 consecutive years.

SOLO DB PLAN EXAMPLE: Business owner age 52, self-employed income $400,000, plans to retire at 65. Actuarial calculation might allow contributions of $180,000–$220,000/year. At 37% marginal rate: $66,600–$81,400 in annual tax savings. Over 13 years to retirement: $864,000–$1,058,000 in cumulative tax savings.

COMBINATION STRATEGY: DB plan + Solo 401(k) "Cash Balance" combination: Many professionals use a Cash Balance plan (a type of DB plan) alongside a 401(k) to maximize both. The 401(k) allows $23,000 employee contribution + $46,000 employer match in 2025. Combined, the total shelter can exceed $275,000/year.

REQUIREMENTS: Must work with an actuary to establish and certify annual contributions. Plan must file Form 5500 annually. Minimum funding standards apply under IRC § 412 — once established, contributions are mandatory (not optional like 401k). Best suited for profitable businesses ($200K+ profit) with no or few employees, stable income, and owner aged 45+.

OBBBA UPDATE: The OBBBA maintained the inflation indexing for DB plan benefit limits and extended the look-back period for highest compensation averaging.`,
  },

  // ── Solo 401(k) ─────────────────────────────────────────────────────────────
  {
    title: "Solo 401(k) — IRC § 401(k): $70,000/Year Tax-Free Retirement Shelter (2025)",
    source_type: "irc_section",
    jurisdiction: "federal",
    document_number: "IRC § 401(k)",
    document_title: "Solo 401(k) — One-Participant 401(k) Plans",
    url: "https://www.irs.gov/retirement-plans/one-participant-401k-plans",
    effective_date: "2025-01-01",
    impact_score: 7,
    content: `A Solo 401(k) (also called Individual 401(k) or One-Participant 401(k)) is available to self-employed individuals and business owners with no full-time employees other than themselves and their spouse. It combines the benefits of a traditional 401(k) with a profit-sharing plan.

2025 CONTRIBUTION LIMITS (IRC §§ 402(g), 415):
- Employee elective deferrals: Up to $23,500 ($31,000 if age 50+, catch-up)
- Employer profit-sharing contribution: Up to 25% of net self-employment income
- Total limit: $70,000 ($77,500 if age 50+)

CALCULATION: Net SE income = net business profit × 0.9235. Employer contribution = SE income × 0.25, capped at $46,500 (for 2025). Employee contribution = $23,500. Combined maximum = $70,000.

EXAMPLE: S-Corp owner, W-2 salary $100,000. Employee deferral: $23,500. Employer contribution: $100,000 × 0.25 = $25,000. Total: $48,500 annual deduction. At 37%: $17,945 in annual tax savings.

ROTH SOLO 401(k): Roth contributions are allowed for the employee portion, creating a Roth balance that grows tax-free. Strategy: high earners who expect tax rates to increase use a mix of traditional (deductible now) and Roth (tax-free later) contributions.

BACKDOOR ROTH CONVERSION: Business owners above Roth IRA income limits ($161,000 single / $240,000 MFJ in 2025) can contribute to a traditional IRA and immediately convert to Roth ("backdoor Roth"). The Solo 401(k) facilitates this by allowing rollover of existing IRA balances to avoid the pro-rata rule.

DEADLINE: Employee contributions must be elected by December 31 of the plan year. Employer contributions can be made up to the tax return due date (including extensions).

SPOUSE EMPLOYMENT: If the owner's spouse performs services for the business, they can also participate in the Solo 401(k), potentially doubling the total contribution ($140,000 combined in 2025).`,
  },

  // ── QSBS Section 1202 ──────────────────────────────────────────────────────
  {
    title: "Section 1202 QSBS — Up to $10 Million Tax-Free on Business Sale (C-Corp Only)",
    source_type: "irc_section",
    jurisdiction: "federal",
    document_number: "IRC § 1202",
    document_title: "Partial Exclusion for Gain from Certain Small Business Stock",
    url: "https://www.irs.gov/pub/irs-drop/n-23-33.pdf",
    effective_date: "2025-01-01",
    impact_score: 10,
    content: `Section 1202 of the IRC allows non-corporate taxpayers to exclude up to 100% of capital gain from the sale of Qualified Small Business Stock (QSBS), subject to caps of $10 million per taxpayer per issuer, or 10× the taxpayer's adjusted basis in the stock — whichever is greater.

EXCLUSION PERCENTAGE: For stock acquired after September 27, 2010: 100% exclusion from federal capital gains tax (subject to the caps above). State conformity varies — California, for example, does NOT conform to the federal exclusion.

QUALIFICATION REQUIREMENTS (IRC § 1202):
1. Must be a domestic C-Corporation (not LLC, S-Corp, or partnership)
2. Corporation must be a "qualified small business" — aggregate gross assets must not exceed $50 million at time of issuance (and immediately after)
3. Stock must be acquired at original issuance (not secondary market)
4. Taxpayer must be non-corporate (individual, trust, or estate)
5. Stock must be held for MORE THAN 5 YEARS
6. Active business requirement: at least 80% of assets used in qualified trades or businesses (most businesses qualify; financial, hospitality, legal, and health businesses may not)

STACKING STRATEGY: Each shareholder can exclude up to $10M (or 10× basis) independently. Gifting shares to family members and irrevocable trusts before sale can multiply the exclusion. A married couple filing jointly can potentially exclude $20M ($10M each if each directly holds stock).

EXAMPLE: Business owner holds 1M shares with $100K basis. Business sells for $12M total gain. 100% exclusion applies: $10M excluded (cap), $2M taxable at 20% LTCG rate = $400K federal tax. Without QSBS: $12M × 20% = $2.4M in tax. Savings: $2M in federal tax.

OBBBA UPDATE: The OBBBA preserved and slightly expanded QSBS provisions. The holding period remains 5 years. Higher exclusion caps have been proposed but not yet enacted.

PLANNING: Convert from LLC/S-Corp to C-Corp early in the company's life to start the 5-year clock. Ensure corporate gross assets stay under $50M at time of stock issuance.`,
  },

  // ── Hiring Children ────────────────────────────────────────────────────────
  {
    title: "Hiring Your Children — IRC § 3121(b)(3): Tax-Free Family Employment Strategy",
    source_type: "irc_section",
    jurisdiction: "federal",
    document_number: "IRC § 3121(b)(3)",
    document_title: "FICA Exemption for Children Employed by Parents",
    url: "https://www.irs.gov/publications/p15",
    effective_date: "2025-01-01",
    impact_score: 7,
    content: `Hiring your children to work in your business is a fully legal tax strategy explicitly authorized by the IRS. Wages paid to children for genuine work performed are deductible business expenses, and when properly structured, can result in zero tax at the child level.

FICA EXEMPTION (IRC § 3121(b)(3)): Services performed by a child under age 18 for a parent's sole proprietorship or single-member LLC owned by the parent are exempt from both the employer and employee portions of Social Security and Medicare taxes (FICA). This is a statutory exemption — not a planning technique. For a parent paying 15.3% SE tax, hiring a child saves 15.3% on every dollar of wages paid, on top of shifting income to the child's lower bracket.

INCOME TAX: Children's wages are includable in their gross income but offset by their standard deduction ($14,600 in 2025). A child earning exactly $14,600 pays zero federal income tax. Wages above the standard deduction are taxed at the child's marginal rate (typically 10%).

ROTH IRA CONTRIBUTION: Once a child has earned income, they can contribute to a Roth IRA (up to $7,000 in 2025 or their earned income, whichever is less). This creates decades of tax-free compounding growth. A parent can fund the child's Roth IRA as a gift.

REQUIREMENTS FOR LEGITIMACY:
1. Child must perform real, documented work appropriate to their age and skills (social media management, filing, photography, data entry, etc.)
2. Pay must be reasonable — comparable to what a third party would charge for the same work
3. Keep records: timesheets, job description, pay stubs, bank deposits
4. Child must actually receive the wages (cannot be a paper transaction)
5. File W-2 if wages ≥ $600; withhold income tax if child owes any

STRUCTURE MATTERS: The FICA exemption applies ONLY if the employing entity is a sole proprietorship or single-member LLC owned solely by the parent. S-Corps and C-Corps do NOT qualify for the FICA exemption — the child's wages are still subject to FICA. However, the income shifting benefit (moving income to child's lower bracket) applies regardless of entity type.

EXAMPLE: Two children ages 15 and 12. Each paid $14,600 for legitimate services. Parent's marginal rate: 37%. Income shifted: $29,200. Tax savings: $29,200 × 37% = $10,804. Plus FICA savings (if sole prop): $29,200 × 15.3% = $4,468. Total annual savings: ~$15,272.`,
  },

  // ── Section 179 + Bonus Depreciation ───────────────────────────────────────
  {
    title: "Section 179 + Bonus Depreciation — IRC §§ 179, 168(k): Immediate Equipment Deductions",
    source_type: "irc_section",
    jurisdiction: "federal",
    document_number: "IRC §§ 179, 168(k)",
    document_title: "Section 179 Expensing and Bonus Depreciation — OBBBA 2025",
    url: "https://www.irs.gov/newsroom/new-rules-and-limitations-for-depreciation-and-expensing-under-the-tax-cuts-and-jobs-act",
    effective_date: "2025-01-01",
    impact_score: 8,
    content: `Section 179 and bonus depreciation allow businesses to immediately deduct the cost of qualifying property in the year placed in service, rather than depreciating over many years.

SECTION 179 (IRC § 179): For 2025, businesses can expense up to $1,160,000 of qualifying property (indexed for inflation). The deduction phases out dollar-for-dollar once total property placed in service exceeds $2,890,000. Section 179 applies to tangible personal property, off-the-shelf software, and certain improvements to non-residential real property. Cannot create or increase a net operating loss (limited to business income).

BONUS DEPRECIATION (IRC § 168(k)) — OBBBA UPDATE: The TCJA originally provided 100% bonus depreciation for qualified property acquired and placed in service after September 27, 2017, phasing down 20% per year starting 2023. The One Big Beautiful Bill Act (OBBBA) RESTORED 100% bonus depreciation for qualifying property placed in service after December 31, 2024. This is one of OBBBA's most significant provisions for business owners.

QUALIFYING PROPERTY: Tangible personal property with a recovery period of 20 years or less (most equipment, vehicles, computers, machinery), qualified film/TV/live theatrical productions, and certain improvements to nonresidential real property.

VEHICLES: Section 179 for heavy SUVs (GVWR > 6,000 lbs) is capped at $30,500 (2025). For passenger vehicles (GVWR ≤ 6,000 lbs), the annual depreciation limits are $12,200 (year 1), $19,500 (year 2), $11,700 (year 3), $7,000 (year 4+) under MACRS. Bonus depreciation can be applied to heavy vehicles for a first-year deduction of up to $30,500 (Section 179 cap) plus bonus depreciation on remaining basis.

COST SEGREGATION: For real property, a cost segregation study can reclassify components (electrical, plumbing, flooring, etc.) as 5-, 7-, or 15-year personal property eligible for bonus depreciation, dramatically accelerating depreciation on commercial real estate.

STRATEGY: Purchase needed equipment before December 31 to secure the full current-year deduction. For high-profit years, accelerate purchases to reduce taxable income. Combine with S-Corp election: the full $1,160,000 deduction flows through to the owner's individual return.`,
  },

  // ── Asset Protection — LLC and DAPT ────────────────────────────────────────
  {
    title: "Asset Protection — LLC Charging Order Protection + Domestic Asset Protection Trusts",
    source_type: "irc_section",
    jurisdiction: "federal",
    document_number: "State LLC Acts; DAPT Statutes",
    document_title: "Asset Protection Structures for High-Net-Worth Business Owners",
    url: "https://www.irs.gov/businesses/small-businesses-self-employed/limited-liability-company-llc",
    effective_date: "2025-01-01",
    impact_score: 8,
    content: `Asset protection structures separate business assets from personal assets and create legal barriers against creditors, lawsuits, and judgments. This is NOT tax evasion — it is legitimate legal planning recognized by courts across the U.S.

OPERATING LLC (CHARGING ORDER PROTECTION): An LLC provides limited liability — creditors of the owner generally cannot reach LLC assets directly. Instead, they can only obtain a "charging order" that entitles them to receive distributions (if and when made). Wyoming, Nevada, and Delaware provide the strongest statutory charging order protections, making charging orders the EXCLUSIVE remedy against a member's interest.

HOLDING COMPANY STRUCTURE: Best practice for business owners with $500K+ in assets:
1. Operating LLC: Runs the actual business; owns minimal assets
2. IP/Royalty LLC: Holds intellectual property; leases it back to Operating LLC
3. Real Estate LLCs: Separate LLC for each property or property group
4. Holding LLC: Owns all subsidiary LLCs; holds excess cash/investments
Formed in Wyoming or Nevada for maximum protection even if business operates elsewhere.

SERIES LLC: Available in Wyoming, Delaware, Nevada, Texas, Illinois, and several other states. A Series LLC creates legally separate "series" within one LLC, each with its own assets, liabilities, and members. Ideal for real estate investors with multiple properties — each property in its own series, all governed by one operating agreement and one annual fee.

DOMESTIC ASSET PROTECTION TRUST (DAPT): Available in Nevada, South Dakota, Wyoming, Delaware, Ohio, and others. A DAPT allows the grantor to be a discretionary beneficiary while still receiving protection from creditors after a seasoning period (typically 2 years). Key features:
- Grantor can be a beneficiary
- Assets are protected from future creditors after the seasoning period
- Transfers to fund the trust must not be fraudulent (no creditors at time of transfer)
- South Dakota DAPTs are generally considered strongest (no state income tax, no statute of limitations for existing creditors after seasoning)

TAX TREATMENT: LLCs are pass-through entities — no additional tax cost. DAPTs are typically grantor trusts — income taxed to the grantor (not the trust), so no trust tax rate disadvantage. The protection is entirely legal and recognized under state law.`,
  },

  // ── Home Office Deduction ──────────────────────────────────────────────────
  {
    title: "Home Office Deduction — IRC § 280A: Deduct a Portion of Your Home Expenses",
    source_type: "irc_section",
    jurisdiction: "federal",
    document_number: "IRC § 280A",
    document_title: "Home Office Deduction — Regular and Exclusive Use",
    url: "https://www.irs.gov/businesses/small-businesses-self-employed/home-office-deduction",
    effective_date: "2025-01-01",
    impact_score: 6,
    content: `IRC § 280A allows self-employed individuals and business owners to deduct a portion of home expenses when part of the home is used regularly and exclusively for business.

REGULAR AND EXCLUSIVE USE: The business area must be used ONLY for business — no personal activities. Even occasional personal use disqualifies the space. The space must be used regularly (not just occasionally).

PRINCIPAL PLACE OF BUSINESS: The home office must be (1) the principal place of business for any business, or (2) used for meeting clients/customers in the normal course of business, or (3) a separate structure used in the business.

CALCULATION METHODS:
1. Simplified Method: $5 per square foot, up to 300 sq ft = max $1,500/year deduction. Easy to calculate, no depreciation recapture risk.
2. Regular Method: Calculate the percentage of home used for business (square footage of office / total home square footage). Apply this percentage to actual home expenses: mortgage interest (or rent), utilities, insurance, repairs, depreciation. Greater deduction but requires more documentation.

DEPRECIATION: Under the regular method, depreciation of the home (based on the business-use percentage) is deductible. However, when the home is sold, the depreciated portion is subject to "depreciation recapture" at up to 25%. Consult a CPA before claiming home office depreciation.

S-CORP ACCOUNTABLE PLAN STRATEGY: S-Corp owners cannot deduct a home office directly through the corporation. Instead, establish an "accountable plan" under Treas. Reg. § 1.62-2: the S-Corp reimburses the owner for home office expenses. The reimbursement is tax-free to the owner AND deductible to the S-Corp. This effectively shifts the deduction to the corporate level.

EXAMPLE: 200 sq ft office in 2,000 sq ft home (10%). Annual home expenses: $24,000 (mortgage interest, utilities, insurance). Home office deduction: $2,400/year. At 37%: $888 annual tax savings. Small but legitimate and well-documented.`,
  },

  // ── Augusta Rule ──────────────────────────────────────────────────────────
  {
    title: 'Augusta Rule — IRC § 280A(g): Rent Your Home to Your Business for 14 Days Tax-Free',
    source_type: "irc_section",
    jurisdiction: "federal",
    document_number: "IRC § 280A(g)",
    document_title: "The Augusta Rule — 14-Day Rental Exclusion",
    url: "https://www.law.cornell.edu/uscode/text/26/280A",
    effective_date: "2025-01-01",
    impact_score: 7,
    content: `IRC § 280A(g) — commonly called the "Augusta Rule" (named after homeowners near Augusta National Golf Club who rent homes during The Masters) — allows homeowners to rent their personal residence for up to 14 days per year and exclude ALL rental income from gross income, with no expenses deductible against it.

THE STRATEGY: A business owner can rent their personal home to their own S-Corp or C-Corp for legitimate business meetings (board meetings, strategic planning sessions, client events). The corporation deducts the rental expense; the owner receives the rental income completely tax-free.

EXAMPLE: S-Corp owner holds 14 board meetings per year at their home. Fair market rental rate for the space: $1,500/day (comparable to a local conference facility). Total rent paid: 14 × $1,500 = $21,000. The S-Corp deducts $21,000 as a business expense. The owner pays ZERO income tax on the $21,000 received. At 37% marginal rate: $7,770 in annual tax savings.

REQUIREMENTS FOR LEGITIMACY:
1. Must document meetings with agendas, minutes, and attendees
2. Rental rate must be at fair market value for comparable facilities in the area (document with comparable quotes or rental platform rates)
3. Rental period cannot exceed 14 days per year
4. Meetings must be genuine business activities
5. The corporation must be legitimately separate (no commingling)

IRS SCRUTINY: The IRS has not broadly challenged properly documented Augusta Rule arrangements. Rev. Rul. 2004-78 confirms that payments made to shareholders for use of personal property can be deductible corporate expenses if at arm's length.

LIMITATION: Only applies to personal residence (primary or vacation home). Cannot be used with property already claimed as rental property on Schedule E. The 14-day limit is strict — any additional day converts the property to "used for rental" and the income becomes taxable.`,
  },

  // ── 2025 Tax Brackets and Key Thresholds ──────────────────────────────────
  {
    title: "2025 Federal Income Tax Brackets, Standard Deductions, and Key Thresholds (OBBBA)",
    source_type: "irs_publication",
    jurisdiction: "federal",
    document_number: "IRS Rev. Proc. 2024-61",
    document_title: "2025 Tax Year — Inflation Adjustments and Key Thresholds",
    url: "https://www.irs.gov/newsroom/irs-provides-tax-inflation-adjustments-for-tax-year-2025",
    effective_date: "2025-01-01",
    impact_score: 8,
    content: `Key 2025 federal income tax thresholds for business owners and high earners.

2025 INCOME TAX BRACKETS — MARRIED FILING JOINTLY:
- 10%:   $0 – $23,850
- 12%:   $23,851 – $96,950
- 22%:   $96,951 – $206,700
- 24%:   $206,701 – $394,600
- 32%:   $394,601 – $501,050
- 35%:   $501,051 – $751,600
- 37%:   Over $751,600

2025 INCOME TAX BRACKETS — SINGLE FILERS:
- 10%:   $0 – $11,925
- 12%:   $11,926 – $48,475
- 22%:   $48,476 – $103,350
- 24%:   $103,351 – $197,300
- 32%:   $197,301 – $250,525
- 35%:   $250,526 – $626,350
- 37%:   Over $626,350

STANDARD DEDUCTION 2025: $30,000 MFJ / $15,000 single / $22,500 head of household.

SELF-EMPLOYMENT TAX 2025:
- Social Security: 12.4% on first $176,100 of net SE income
- Medicare: 2.9% on all net SE income (no ceiling)
- Additional Medicare Tax: 0.9% on earned income above $200,000 (single) / $250,000 (MFJ)
- Self-employed deduct half of SE tax (IRC § 164(f))

CAPITAL GAINS RATES 2025:
- 0%:   Taxable income up to $96,700 MFJ / $48,350 single
- 15%:  $96,701–$583,750 MFJ / $48,351–$519,000 single
- 20%:  Above $583,750 MFJ / $519,000 single
- Net Investment Income Tax (NIIT): 3.8% on lesser of NII or excess over $250,000 MFJ / $200,000 single

RETIREMENT PLAN LIMITS 2025 (IRC § 415):
- 401(k) Employee Deferral: $23,500 ($31,000 age 50+)
- Solo 401(k) Total: $70,000 ($77,500 age 50+)
- SEP-IRA: Lesser of $70,000 or 25% of compensation
- SIMPLE IRA: $16,500 ($20,000 age 50+)
- IRA Contribution: $7,000 ($8,000 age 50+)
- DB Plan Limit: $280,000

GIFT AND ESTATE TAX 2025 (OBBBA: Exemptions Made Permanent):
- Annual gift exclusion: $19,000 per recipient
- Lifetime exemption: $13,990,000 per person ($27,980,000 MFJ with portability)
- Estate tax rate: 40% above exemption

OBBBA NOTE: The One Big Beautiful Bill Act permanently extended most TCJA provisions including the individual income tax rates above, the doubled standard deduction, the $10,000 SALT cap (modified), and the increased estate/gift tax exemptions.`,
  },
];
