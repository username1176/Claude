-- ============================================================
-- Row Level Security Policies
-- ============================================================

-- Profiles
alter table public.profiles enable row level security;

create policy "users_own_profile"
  on public.profiles for all
  using (auth.uid() = id);

-- Businesses
alter table public.businesses enable row level security;

create policy "users_own_businesses"
  on public.businesses for all
  using (auth.uid() = user_id);

-- Questionnaire responses
alter table public.questionnaire_responses enable row level security;

create policy "users_own_questionnaire"
  on public.questionnaire_responses for all
  using (auth.uid() = user_id);

-- Recommendations
alter table public.recommendations enable row level security;

create policy "users_own_recommendations"
  on public.recommendations for all
  using (auth.uid() = user_id);

-- Strategies
alter table public.strategies enable row level security;

create policy "users_own_strategies"
  on public.strategies for all
  using (auth.uid() = user_id);

-- PDF Reports
alter table public.pdf_reports enable row level security;

create policy "users_own_pdf_reports"
  on public.pdf_reports for all
  using (auth.uid() = user_id);

-- Subscriptions
alter table public.subscriptions enable row level security;

create policy "users_own_subscriptions"
  on public.subscriptions for all
  using (auth.uid() = user_id);

-- Knowledge base (read-only for authenticated users; write via service role)
alter table public.knowledge_base enable row level security;

create policy "authenticated_read_kb"
  on public.knowledge_base for select
  using (auth.role() = 'authenticated');

alter table public.knowledge_base_sources enable row level security;

create policy "authenticated_read_kb_sources"
  on public.knowledge_base_sources for select
  using (auth.role() = 'authenticated');
