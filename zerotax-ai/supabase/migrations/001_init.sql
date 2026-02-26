-- ============================================================
-- ZeroTax AI — Initial Schema Migration
-- ============================================================

-- Extensions
create extension if not exists "uuid-ossp";
create extension if not exists vector;

-- ============================================================
-- PROFILES
-- ============================================================
create table public.profiles (
  id              uuid primary key references auth.users(id) on delete cascade,
  email           text not null,
  full_name       text,
  avatar_url      text,
  stripe_customer_id text unique,
  subscription_tier text not null default 'free'
    check (subscription_tier in ('free', 'premium', 'enterprise')),
  subscription_status text not null default 'inactive'
    check (subscription_status in ('active', 'inactive', 'trialing', 'canceled')),
  subscription_period_end timestamptz,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- Auto-create profile on auth.users insert
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name, avatar_url)
  values (
    new.id,
    new.email,
    new.raw_user_meta_data->>'full_name',
    new.raw_user_meta_data->>'avatar_url'
  );
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Auto-update updated_at
create or replace function public.handle_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger profiles_updated_at
  before update on public.profiles
  for each row execute procedure public.handle_updated_at();

-- ============================================================
-- BUSINESSES
-- ============================================================
create table public.businesses (
  id              uuid primary key default uuid_generate_v4(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  name            text,
  is_active       boolean not null default true,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create trigger businesses_updated_at
  before update on public.businesses
  for each row execute procedure public.handle_updated_at();

create index on public.businesses(user_id);

-- ============================================================
-- QUESTIONNAIRE RESPONSES
-- ============================================================
create table public.questionnaire_responses (
  id              uuid primary key default uuid_generate_v4(),
  business_id     uuid not null references public.businesses(id) on delete cascade,
  user_id         uuid not null references public.profiles(id) on delete cascade,

  business_stage  text check (business_stage in ('idea', 'startup', 'growth', 'established', 'mature')),
  industry        text,
  entity_type_current text,
  state_of_formation text,
  states_operating text[],

  annual_revenue  numeric(15,2),
  annual_profit   numeric(15,2),
  w2_wages_paid   numeric(15,2),
  owner_draws     numeric(15,2),
  reasonable_salary numeric(15,2),
  other_income    numeric(15,2),
  other_income_type text,

  num_owners      integer,
  married_filing_jointly boolean,
  spouse_works    boolean,
  spouse_income   numeric(15,2),
  children_count  integer,
  ages_children   integer[],
  family_in_business boolean,

  real_estate_value   numeric(15,2),
  business_assets_value numeric(15,2),
  investment_portfolio  numeric(15,2),
  retirement_accounts   numeric(15,2),
  total_net_worth       numeric(15,2),
  has_qsbs_stock        boolean default false,
  year_business_founded integer,

  goal_minimize_taxes     boolean default false,
  goal_asset_protection   boolean default false,
  goal_estate_planning    boolean default false,
  goal_exit_strategy      boolean default false,
  goal_retirement_planning boolean default false,
  goal_hire_family        boolean default false,

  planning_horizon text check (planning_horizon in ('immediate', '1_year', '3_year', '5_plus')),
  exit_timeline_years integer,

  additional_data jsonb default '{}',
  completed_at    timestamptz,
  step_completed  integer not null default 0,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create trigger questionnaire_updated_at
  before update on public.questionnaire_responses
  for each row execute procedure public.handle_updated_at();

create index on public.questionnaire_responses(user_id);
create index on public.questionnaire_responses(business_id);

-- ============================================================
-- RECOMMENDATIONS
-- ============================================================
create table public.recommendations (
  id              uuid primary key default uuid_generate_v4(),
  business_id     uuid not null references public.businesses(id) on delete cascade,
  user_id         uuid not null references public.profiles(id) on delete cascade,
  questionnaire_id uuid references public.questionnaire_responses(id),

  title           text not null,
  executive_summary text,
  recommended_entity_structure text,
  entity_rationale text,

  current_estimated_tax   numeric(15,2),
  optimized_estimated_tax numeric(15,2),
  projected_annual_savings numeric(15,2),
  projected_10yr_savings  numeric(15,2),
  savings_breakdown       jsonb,

  model_used      text not null default 'claude-sonnet-4-6',
  rag_chunks_used integer default 0,
  raw_ai_response text,

  status          text not null default 'draft'
    check (status in ('draft', 'complete', 'outdated', 'archived')),
  law_version_date date,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create trigger recommendations_updated_at
  before update on public.recommendations
  for each row execute procedure public.handle_updated_at();

create index on public.recommendations(user_id);
create index on public.recommendations(business_id);

-- ============================================================
-- STRATEGIES
-- ============================================================
create table public.strategies (
  id              uuid primary key default uuid_generate_v4(),
  recommendation_id uuid not null references public.recommendations(id) on delete cascade,
  user_id         uuid not null references public.profiles(id) on delete cascade,

  category        text not null check (category in (
    'entity_structure', 'retirement', 'depreciation', 'deductions',
    'real_estate', 'estate_planning', 'asset_protection', 'exit',
    'family_employment', 'qsbs', 'opportunity_zone', 'credits', 'state_tax'
  )),

  title           text not null,
  description     text not null,
  detailed_explanation text,

  irc_sections    text[],
  obbba_sections  text[],
  state_law_refs  text[],
  irs_publications text[],

  estimated_annual_savings numeric(15,2),
  implementation_cost      numeric(15,2),
  payback_period_months    integer,

  priority        text not null default 'medium'
    check (priority in ('critical', 'high', 'medium', 'low')),
  complexity      text not null default 'medium'
    check (complexity in ('simple', 'medium', 'complex', 'attorney_required')),
  timeline_days   integer,
  requires_attorney boolean default false,
  requires_cpa    boolean default false,

  action_items    jsonb default '[]',
  user_status     text default 'pending'
    check (user_status in ('pending', 'in_progress', 'completed', 'skipped')),
  completed_at    timestamptz,

  sort_order      integer not null default 0,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create trigger strategies_updated_at
  before update on public.strategies
  for each row execute procedure public.handle_updated_at();

create index on public.strategies(recommendation_id);
create index on public.strategies(user_id, user_status);

-- ============================================================
-- PDF REPORTS
-- ============================================================
create table public.pdf_reports (
  id              uuid primary key default uuid_generate_v4(),
  recommendation_id uuid not null references public.recommendations(id) on delete cascade,
  user_id         uuid not null references public.profiles(id) on delete cascade,
  storage_path    text not null,
  file_size_bytes integer,
  generated_at    timestamptz not null default now()
);

create index on public.pdf_reports(user_id);

-- ============================================================
-- SUBSCRIPTIONS
-- ============================================================
create table public.subscriptions (
  id              text primary key,
  user_id         uuid not null references public.profiles(id) on delete cascade,
  price_id        text not null,
  status          text not null,
  cancel_at_period_end boolean default false,
  current_period_start timestamptz,
  current_period_end   timestamptz,
  trial_end       timestamptz,
  metadata        jsonb default '{}',
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create trigger subscriptions_updated_at
  before update on public.subscriptions
  for each row execute procedure public.handle_updated_at();

create index on public.subscriptions(user_id);
