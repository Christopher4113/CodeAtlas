-- Run this in your Supabase project: SQL Editor → New query → paste and run.
-- Creates a table to store GitHub Personal Access Tokens per user (for repo analysis when not using GitHub OAuth).

create table if not exists public.user_github_tokens (
  user_id uuid primary key references auth.users(id) on delete cascade,
  github_token text not null,
  updated_at timestamptz not null default now()
);

alter table public.user_github_tokens enable row level security;

create policy "Users can manage own token"
  on public.user_github_tokens
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
