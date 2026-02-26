// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Knowledge Base Feed Sources
// Equivalent to the sources config in update_knowledge.py.
// Each source maps to a feed that is fetched and embedded every 24h.
// ─────────────────────────────────────────────────────────────────────────────

export type SourceType =
  | "irs_publication"
  | "irc_section"
  | "obbba"
  | "revenue_ruling"
  | "tax_court"
  | "state_bulletin"
  | "treasury_reg"
  | "cca"
  | "plr";

export interface FeedSource {
  id: string;
  name: string;
  url: string;
  type: "rss" | "atom" | "api";
  source_type: SourceType;
  jurisdiction: string; // 'federal' or state code e.g. 'CA'
  category: string;
  is_active: boolean;
  fetch_interval_hours: number;
  /** impact_score >= this threshold → flag for human review */
  impact_threshold: number;
  description: string;
}

// ─── Federal Sources ──────────────────────────────────────────────────────────

const FEDERAL_SOURCES: FeedSource[] = [
  {
    id: "irs_news_releases",
    name: "IRS Newsroom — News Releases",
    url: "https://www.irs.gov/newsroom/news-releases-for-current-month.rss",
    type: "rss",
    source_type: "irs_publication",
    jurisdiction: "federal",
    category: "news",
    is_active: true,
    fetch_interval_hours: 24,
    impact_threshold: 6,
    description: "Official IRS news releases — tax law changes, enforcement updates, deadline extensions",
  },
  {
    id: "irs_guidance",
    name: "IRS Guidance & Publications",
    url: "https://www.irs.gov/newsroom/irs-guidance-and-publications.rss",
    type: "rss",
    source_type: "irs_publication",
    jurisdiction: "federal",
    category: "guidance",
    is_active: true,
    fetch_interval_hours: 24,
    impact_threshold: 7,
    description: "Updated IRS publications, revenue procedures, and notices",
  },
  {
    id: "irs_tax_pros",
    name: "IRS — What's Hot for Tax Professionals",
    url: "https://www.irs.gov/newsroom/whats-hot.rss",
    type: "rss",
    source_type: "revenue_ruling",
    jurisdiction: "federal",
    category: "professional",
    is_active: true,
    fetch_interval_hours: 24,
    impact_threshold: 6,
    description: "Priority updates for tax professionals — practice changes and alerts",
  },
  {
    id: "federal_register_irs",
    name: "Federal Register — IRS & Treasury Rules",
    url: "https://www.federalregister.gov/api/v1/documents.rss?agencies[]=internal-revenue-service&agencies[]=department-of-the-treasury&type[]=Rule&type[]=Proposed+Rule",
    type: "rss",
    source_type: "treasury_reg",
    jurisdiction: "federal",
    category: "regulations",
    is_active: true,
    fetch_interval_hours: 24,
    impact_threshold: 8,
    description: "Final and proposed Treasury Regulations from the Federal Register",
  },
  {
    id: "tax_foundation",
    name: "Tax Foundation — Research & Analysis",
    url: "https://taxfoundation.org/feed/",
    type: "rss",
    source_type: "treasury_reg",
    jurisdiction: "federal",
    category: "analysis",
    is_active: true,
    fetch_interval_hours: 48,
    impact_threshold: 5,
    description: "Independent tax policy research and analysis from the Tax Foundation",
  },
  {
    id: "congress_tax_bills",
    name: "Congress.gov — Tax Legislation",
    url: "https://www.congress.gov/rss/legislation.xml",
    type: "rss",
    source_type: "irc_section",
    jurisdiction: "federal",
    category: "legislation",
    is_active: true,
    fetch_interval_hours: 24,
    impact_threshold: 9,
    description: "New and amended tax legislation from Congress — highest review priority",
  },
];

// ─── State Sources ────────────────────────────────────────────────────────────
// Only states with confirmed public RSS feeds are marked is_active: true.
// Others are included for future activation once URLs are verified.

const STATE_SOURCES: FeedSource[] = [
  // High-tax / high-population states first
  {
    id: "state_ca",
    name: "California Franchise Tax Board — News",
    url: "https://www.ftb.ca.gov/about-ftb/newsroom/news-releases/rss.xml",
    type: "rss",
    source_type: "state_bulletin",
    jurisdiction: "CA",
    category: "state_news",
    is_active: true,
    fetch_interval_hours: 48,
    impact_threshold: 6,
    description: "California FTB news releases — conformity updates, rate changes, enforcement",
  },
  {
    id: "state_ny",
    name: "New York Department of Taxation — News",
    url: "https://www.tax.ny.gov/rss/rss.xml",
    type: "rss",
    source_type: "state_bulletin",
    jurisdiction: "NY",
    category: "state_news",
    is_active: true,
    fetch_interval_hours: 48,
    impact_threshold: 6,
    description: "New York DTF updates — tax law changes and guidance",
  },
  {
    id: "state_tx",
    name: "Texas Comptroller — Tax News",
    url: "https://comptroller.texas.gov/news/rss.xml",
    type: "rss",
    source_type: "state_bulletin",
    jurisdiction: "TX",
    category: "state_news",
    is_active: true,
    fetch_interval_hours: 48,
    impact_threshold: 5,
    description: "Texas Comptroller tax updates (no state income tax, but sales/franchise tax)",
  },
  {
    id: "state_fl",
    name: "Florida Department of Revenue — News",
    url: "https://floridarevenue.com/taxes/industry/Pages/rss.aspx",
    type: "rss",
    source_type: "state_bulletin",
    jurisdiction: "FL",
    category: "state_news",
    is_active: false, // URL needs verification
    fetch_interval_hours: 48,
    impact_threshold: 5,
    description: "Florida DOR updates",
  },
  {
    id: "state_il",
    name: "Illinois Department of Revenue — News",
    url: "https://tax.illinois.gov/news.rss",
    type: "rss",
    source_type: "state_bulletin",
    jurisdiction: "IL",
    category: "state_news",
    is_active: false,
    fetch_interval_hours: 48,
    impact_threshold: 6,
    description: "Illinois IDOR updates",
  },
  {
    id: "state_wa",
    name: "Washington Department of Revenue — News",
    url: "https://dor.wa.gov/news/rss.xml",
    type: "rss",
    source_type: "state_bulletin",
    jurisdiction: "WA",
    category: "state_news",
    is_active: false,
    fetch_interval_hours: 48,
    impact_threshold: 5,
    description: "Washington DOR — no income tax but B&O and other taxes",
  },
  {
    id: "state_ma",
    name: "Massachusetts DOR — News",
    url: "https://www.mass.gov/rss/news/mador",
    type: "rss",
    source_type: "state_bulletin",
    jurisdiction: "MA",
    category: "state_news",
    is_active: false,
    fetch_interval_hours: 48,
    impact_threshold: 6,
    description: "Massachusetts DOR updates",
  },
  {
    id: "state_nj",
    name: "New Jersey Division of Taxation — News",
    url: "https://www.nj.gov/rss/treasury/taxation_news.xml",
    type: "rss",
    source_type: "state_bulletin",
    jurisdiction: "NJ",
    category: "state_news",
    is_active: false,
    fetch_interval_hours: 48,
    impact_threshold: 6,
    description: "NJ Division of Taxation updates",
  },
];

// ─── Aggregated export ────────────────────────────────────────────────────────

export const FEED_SOURCES: FeedSource[] = [
  ...FEDERAL_SOURCES,
  ...STATE_SOURCES,
];

export const ACTIVE_SOURCES = FEED_SOURCES.filter((s) => s.is_active);

/** Lookup source by ID */
export function getSourceById(id: string): FeedSource | undefined {
  return FEED_SOURCES.find((s) => s.id === id);
}

/** Get all sources for a given jurisdiction */
export function getSourcesByJurisdiction(jurisdiction: string): FeedSource[] {
  return FEED_SOURCES.filter(
    (s) => s.jurisdiction === jurisdiction && s.is_active
  );
}
