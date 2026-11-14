-- ==========================================================
-- BHAAVABOT SUPABASE DATABASE SCHEMA (VERSION 2.0)
-- Execute this script in your Supabase Project -> SQL Editor
-- ==========================================================

-- 1. Enable UUID generation extension
create extension if not exists "uuid-ossp";

-- 2. User Profiles Table (Linked to auth.users)
create table if not exists public.profiles (
  id uuid references auth.users on delete cascade primary key,
  email text,
  display_name text,
  avatar_url text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

alter table public.profiles enable row level security;

create policy "Users can view own profile"
  on public.profiles for select
  using ( auth.uid() = id );

create policy "Users can update own profile"
  on public.profiles for update
  using ( auth.uid() = id );

-- 3. Conversations Table
create table if not exists public.conversations (
  id text primary key default uuid_generate_v4()::text,
  user_id text not null default 'guest',
  title text not null default 'A Quiet Conversation',
  summary text default '',
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

alter table public.conversations enable row level security;

create policy "Allow all operations for user conversations"
  on public.conversations for all
  using ( true );

-- 4. Messages Table (With emotion and safety metadata)
create table if not exists public.messages (
  id text primary key default uuid_generate_v4()::text,
  conversation_id text not null references public.conversations(id) on delete cascade,
  user_id text not null default 'guest',
  role text not null check (role in ('user', 'bot', 'system')),
  content text not null,
  detected_emotion text default 'neutral',
  emotion_confidence numeric default 0.8,
  emotion_intensity numeric default 0.5,
  safety_level text default 'NORMAL',
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

alter table public.messages enable row level security;

create policy "Allow all operations for user messages"
  on public.messages for all
  using ( true );

-- 5. Empathy Profiles Table (Toronto Empathy Questionnaire Profiling)
create table if not exists public.empathy_profiles (
  user_id text primary key,
  total_empathy_score numeric not null,
  emotional_empathy_score numeric not null,
  cognitive_empathy_score numeric not null,
  dispersion_score numeric not null,
  consistency_level text not null, -- 'high', 'low'
  profile_type text not null, -- 'PROFILE_A', 'PROFILE_B', 'PROFILE_C', 'PROFILE_D'
  emotional_style text not null,
  cognitive_style text not null,
  communication_style text not null,
  preferred_pacing text not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

alter table public.empathy_profiles enable row level security;

create policy "Allow all operations on empathy_profiles"
  on public.empathy_profiles for all
  using ( true );

-- 6. User Preferences Table
create table if not exists public.user_preferences (
  user_id text primary key,
  preferred_theme text default 'I just want someone to listen',
  preferred_content_type text default 'all',
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

alter table public.user_preferences enable row level security;

create policy "Allow all operations on user_preferences"
  on public.user_preferences for all
  using ( true );

-- 7. Daily Reflections & Inner Weather Check-Ins
create table if not exists public.reflections (
  id text primary key default uuid_generate_v4()::text,
  user_id text not null default 'guest',
  mood text not null, -- 'Calm', 'Tired', 'Heavy', 'Hopeful'
  note text default '',
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

alter table public.reflections enable row level security;

create policy "Allow all operations on reflections"
  on public.reflections for all
  using ( true );

-- 8. Favorites (Saved Books & Music)
create table if not exists public.favorites (
  id text primary key default uuid_generate_v4()::text,
  user_id text not null default 'guest',
  title text not null,
  item_type text not null check (item_type in ('book', 'music')),
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  unique(user_id, title)
);

alter table public.favorites enable row level security;

create policy "Allow all operations on favorites"
  on public.favorites for all
  using ( true );

-- 9. Curated Books Resource Table (Public Domain & Sacred Texts References)
create table if not exists public.books (
  id text primary key default uuid_generate_v4()::text,
  title text not null unique,
  author text not null,
  tradition text,
  category text,
  kind text not null,
  language text default 'English',
  description text,
  pages text,
  year text,
  icon text default 'book',
  tone text default 'peach',
  cover_image_url text,
  reading_url text,
  url text,
  source_name text default 'Project Gutenberg',
  source text default 'Project Gutenberg',
  license text default 'Public Domain',
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Seed Initial Curated Books (Ramayana, Mahabharata, Bible, Quran, Bhagavad Gita)
insert into public.books (id, title, author, tradition, category, kind, language, description, pages, year, icon, tone, cover_image_url, reading_url, url, source_name, source, license)
values
  ('book-bhagavad-gita', 'Bhagavad Gita', 'Vyasa (Translated by Sir Edwin Arnold)', 'Hinduism', 'Philosophy', 'Philosophy · Spiritual Wisdom', 'English (Verse translation from Sanskrit)', 'A profound dialogue between Prince Arjuna and Krishna addressing duty, devotion, selflessness, and inner peace on the battlefield of life.', '18 Chapters · ~700 Verses', 'c. 2nd Century BCE', 'sun', 'peach', 'https://www.gutenberg.org/cache/epub/2388/pg2388.cover.medium.jpg', 'https://www.gutenberg.org/ebooks/2388', 'https://www.gutenberg.org/ebooks/2388', 'Project Gutenberg', 'Project Gutenberg', 'Public Domain'),
  ('book-ramayana', 'Ramayana', 'Valmiki (Translated by Ralph T. H. Griffith)', 'Hinduism', 'Epic', 'Epic · Dharma · Devotion', 'English (Verse translation from Sanskrit)', 'The ancient Indian epic chronicling Rama''s journey of righteousness, devotion, compassion, and courage amidst exile and adversity.', '7 Kandas · ~24,000 Verses', 'c. 5th Century BCE', 'moon', 'mint', 'https://www.gutenberg.org/cache/epub/24869/pg24869.cover.medium.jpg', 'https://www.gutenberg.org/ebooks/24869', 'https://www.gutenberg.org/ebooks/24869', 'Project Gutenberg', 'Project Gutenberg', 'Public Domain'),
  ('book-mahabharata', 'Mahabharata', 'Krishna-Dwaipayana Vyasa (Translated by Kisari Mohan Ganguli)', 'Hinduism', 'Epic', 'Epic · Ethics · Wisdom', 'English (Prose translation from Sanskrit)', 'The monumental epic exploring human destiny, conflict resolution, dharma, statecraft, and the search for liberation and truth.', '18 Parvas · Extensive Epic', 'c. 4th Century BCE', 'sun', 'lavender', 'https://www.gutenberg.org/cache/epub/15474/pg15474.cover.medium.jpg', 'https://www.gutenberg.org/ebooks/15474', 'https://www.gutenberg.org/ebooks/15474', 'Project Gutenberg', 'Project Gutenberg', 'Public Domain'),
  ('book-bible', 'The Holy Bible', 'King James Version', 'Christianity', 'Sacred Text', 'Sacred Text · Faith · Compassion', 'English (King James Version)', 'The sacred scriptures of Christianity, offering timeless teachings on faith, unconditional love, solace, and spiritual redemption.', '66 Books · Old & New Testaments', '1611 AD', 'coffee', 'peach', 'https://www.gutenberg.org/cache/epub/10/pg10.cover.medium.jpg', 'https://www.gutenberg.org/ebooks/10', 'https://www.gutenberg.org/ebooks/10', 'Project Gutenberg', 'Project Gutenberg', 'Public Domain'),
  ('book-quran', 'The Holy Quran', 'Translated by J. M. Rodwell', 'Islam', 'Sacred Text', 'Sacred Text · Mercy · Guidance', 'English (Translation from Arabic)', 'The central religious text of Islam, illuminating the path of patience, gratitude, moral integrity, divine mercy, and reflection.', '114 Surahs', 'c. 610–632 AD', 'rain', 'mint', 'https://www.gutenberg.org/cache/epub/2800/pg2800.cover.medium.jpg', 'https://www.gutenberg.org/ebooks/2800', 'https://www.gutenberg.org/ebooks/2800', 'Project Gutenberg', 'Project Gutenberg', 'Public Domain')
on conflict (title) do update set
  reading_url = excluded.reading_url,
  url = excluded.url,
  description = excluded.description,
  tradition = excluded.tradition,
  category = excluded.category,
  language = excluded.language,
  source_name = excluded.source_name,
  license = excluded.license,
  updated_at = timezone('utc'::text, now());

-- 9. Curated Audio Tracks & Soundscapes
create table if not exists public.audio_tracks (
  id text primary key,
  title text not null unique,
  artist text not null,
  kind text,
  category text default 'Nature',
  icon text default 'rain',
  tone text default 'mint',
  source text default 'Creative Commons',
  license text default 'CC0 / Public Domain',
  attribution text,
  url text,
  audio_url text,
  duration_seconds integer,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Seed Initial Curated Audio Tracks
insert into public.audio_tracks (id, title, artist, kind, category, icon, tone, source, license, attribution, url, audio_url, duration_seconds)
values
  ('music-forest-rain', 'Gentle Forest Rain', 'Earth Acoustics', 'Nature · 60 min', 'Nature', 'rain', 'mint', 'Open Audio Nature Archive', 'Public Domain / CC0', 'Field recording of soothing gentle summer rain on green leaves', '/audio/gentle-forest-rain.wav', '/audio/gentle-forest-rain.wav', 3600),
  ('music-soft-rain', 'Soft Rain', 'Calm Studio', 'Sleep · 45 min', 'Sleep', 'rain', 'lavender', 'Pixabay Audio Library', 'CC0 / Pixabay Content License', 'Continuous soft rainfall for deep sleep and relaxation', '/audio/soft-rain.wav', '/audio/soft-rain.wav', 2700),
  ('music-ocean-waves', 'Ocean Waves', 'Pacific Shore', 'Nature · 50 min', 'Nature', 'sun', 'blue', 'Wikimedia Commons Natural Sounds', 'CC0 / Public Domain', 'Gentle rhythmic ocean tides washing against soft shore', '/audio/ocean-waves.wav', '/audio/ocean-waves.wav', 3000),
  ('music-forest-ambience', 'Forest Ambience', 'Green Canopy', 'Nature · 40 min', 'Nature', 'moon', 'mint', 'Nature Reserve Soundscapes', 'CC0 / Public Domain', 'Deep woodland atmosphere with breeze and gentle rustle', '/audio/forest-ambience.wav', '/audio/forest-ambience.wav', 2400),
  ('music-birds-nature', 'Birds in Nature', 'Wild Sanctuary', 'Nature · 35 min', 'Nature', 'sun', 'peach', 'Open Wildlife Field Recordings', 'CC0 / Public Domain', 'Morning songbirds in peaceful untouched natural sanctuary', '/audio/birds-in-nature.wav', '/audio/birds-in-nature.wav', 2100),
  ('music-peaceful-piano', 'Peaceful Piano', 'Gentle Keys', 'Sleep · 48 min', 'Sleep', 'moon', 'lavender', 'Musopen Open Classical Archive', 'Public Domain / CC0', 'Slow acoustic piano chords and warm harmonic overtones', '/audio/peaceful-piano.wav', '/audio/peaceful-piano.wav', 2880),
  ('music-calm-ambient', 'Calm Ambient Music', 'The Sunday Room', 'Focus · 38 min', 'Focus', 'coffee', 'blue', 'Creative Commons Archive', 'CC-BY 4.0 / Free License', 'Warm evolving synthesizer pad for deep mindfulness and calm', '/audio/calm-ambient.wav', '/audio/calm-ambient.wav', 2280),
  ('music-night-crickets', 'Night Crickets', 'Summer Meadow', 'Sleep · 60 min', 'Sleep', 'moon', 'lavender', 'Summer Evening Sound Archive', 'CC0 / Public Domain', 'Steady rhythmic evening field crickets under a quiet night sky', '/audio/night-crickets.wav', '/audio/night-crickets.wav', 3600),
  ('music-flowing-water', 'Flowing Water', 'Mountain Stream', 'Nature · 45 min', 'Nature', 'rain', 'mint', 'Natural Waterway Audio Archive', 'CC0 / Public Domain', 'Crisp freshwater stream flowing gently over river stones', '/audio/flowing-water.wav', '/audio/flowing-water.wav', 2700),
  ('music-deep-focus', 'Deep Focus Ambience', 'BhaavaBot Sessions', 'Focus · 42 min', 'Focus', 'coffee', 'peach', 'Royalty Free Community Soundscape', 'CC0 / Free License', '432Hz ambient drone tuned for sustained calm concentration', '/audio/deep-focus.wav', '/audio/deep-focus.wav', 2520)
on conflict (title) do update set
  artist = excluded.artist,
  kind = excluded.kind,
  category = excluded.category,
  icon = excluded.icon,
  tone = excluded.tone,
  source = excluded.source,
  license = excluded.license,
  attribution = excluded.attribution,
  url = excluded.url,
  audio_url = excluded.audio_url,
  duration_seconds = excluded.duration_seconds,
  updated_at = timezone('utc'::text, now());
