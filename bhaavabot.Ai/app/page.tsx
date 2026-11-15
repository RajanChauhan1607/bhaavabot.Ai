'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import type React from 'react'
import Link from 'next/link'
import { authClient } from '@/lib/auth-client'
import { AuthForm } from '@/components/auth-form'
import {
  sendChatMessage,
  recordCheckin,
  fetchReflections,
  toggleFavorite as apiToggleFavorite,
  fetchFavorites as apiFetchFavorites,
  fetchEmpathyQuestions,
  submitEmpathyAssessment,
  fetchEmpathyProfile,
  fetchThemes,
  fetchBooks,
  fetchMusic,
  type BookItem,
  type MusicItem,
  fetchConversations,
  createConversation,
  fetchConversationMessages,
  deleteConversation,
  fetchEmergencyContact,
  type EmergencyContact,
  type ReflectionItem,
  type EmpathyProfile,
  type EmpathyQuestion,
  type ThemeItem,
  type ChatMessage,
  type ConversationItem,
} from '@/lib/api'
import { EmergencyContactModal } from '@/components/emergency-contact-modal'
import {
  ArrowUp, Bell, BookOpen, ChevronDown, CircleHelp, Heart,
  Home, Mic, MoreHorizontal, Music2, Paperclip, Play,
  Plus, Send, Settings, ShieldCheck, Sparkles, Square, X, Check,
  MessageSquare, Menu, Trash2, PanelLeft, PanelLeftClose, ArrowLeft,
  ArrowUpRight, ChevronRight, Sun, Moon, CloudRain, Coffee,
  AlertCircle, Phone, Pause, Volume2, VolumeX,
} from 'lucide-react'

const starters = [
  { icon: '☼', title: 'I feel anxious', text: 'I have been feeling anxious lately.' },
  { icon: '◌', title: 'Help me reflect', text: 'Can you help me reflect on my day?' },
  { icon: '♪', title: 'Suggest music', text: 'Suggest something calming to listen to.' },
  { icon: '📖', title: 'Suggest a book', text: 'Suggest something comforting and gentle to read.' },
]

const initialMessages: ChatMessage[] = [
  { from: 'bot', text: 'Hi Alex, I’m BhaavaBot. I’m here to listen, without judgment. What’s on your mind today?', time: '10:42 AM' },
  { from: 'user', text: 'I’ve been feeling a little overwhelmed with everything lately.', time: '10:43 AM' },
  { from: 'bot', text: 'That sounds like a lot to carry. You don’t have to solve everything at once. Would it help to talk through what feels heaviest right now?', time: '10:43 AM' },
]

function formatAudioTime(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`
}

const musicItems: (MusicItem & { author?: string })[] = [
  {
    id: 'music-forest-rain',
    title: 'Gentle Forest Rain',
    artist: 'Earth Acoustics',
    kind: 'Nature · 60 min',
    category: 'Nature',
    icon: 'rain',
    tone: 'mint',
    source: 'Open Audio Nature Archive',
    license: 'Public Domain / CC0',
    attribution: 'Field recording of soothing gentle summer rain on green leaves',
    url: '/audio/gentle-forest-rain.wav',
    audio_url: '/audio/gentle-forest-rain.wav',
    duration_seconds: 3600,
  },
  {
    id: 'music-soft-rain',
    title: 'Soft Rain',
    artist: 'Calm Studio',
    kind: 'Sleep · 45 min',
    category: 'Sleep',
    icon: 'rain',
    tone: 'lavender',
    source: 'Pixabay Audio Library',
    license: 'CC0 / Pixabay Content License',
    attribution: 'Continuous soft rainfall for deep sleep and relaxation',
    url: '/audio/soft-rain.wav',
    audio_url: '/audio/soft-rain.wav',
    duration_seconds: 2700,
  },
  {
    id: 'music-ocean-waves',
    title: 'Ocean Waves',
    artist: 'Pacific Shore',
    kind: 'Nature · 50 min',
    category: 'Nature',
    icon: 'sun',
    tone: 'blue',
    source: 'Wikimedia Commons Natural Sounds',
    license: 'CC0 / Public Domain',
    attribution: 'Gentle rhythmic ocean tides washing against soft shore',
    url: '/audio/ocean-waves.wav',
    audio_url: '/audio/ocean-waves.wav',
    duration_seconds: 3000,
  },
  {
    id: 'music-forest-ambience',
    title: 'Forest Ambience',
    artist: 'Green Canopy',
    kind: 'Nature · 40 min',
    category: 'Nature',
    icon: 'moon',
    tone: 'mint',
    source: 'Nature Reserve Soundscapes',
    license: 'CC0 / Public Domain',
    attribution: 'Deep woodland atmosphere with breeze and gentle rustle',
    url: '/audio/forest-ambience.wav',
    audio_url: '/audio/forest-ambience.wav',
    duration_seconds: 2400,
  },
  {
    id: 'music-birds-nature',
    title: 'Birds in Nature',
    artist: 'Wild Sanctuary',
    kind: 'Nature · 35 min',
    category: 'Nature',
    icon: 'sun',
    tone: 'peach',
    source: 'Open Wildlife Field Recordings',
    license: 'CC0 / Public Domain',
    attribution: 'Morning songbirds in peaceful untouched natural sanctuary',
    url: '/audio/birds-in-nature.wav',
    audio_url: '/audio/birds-in-nature.wav',
    duration_seconds: 2100,
  },
  {
    id: 'music-peaceful-piano',
    title: 'Peaceful Piano',
    artist: 'Gentle Keys',
    kind: 'Sleep · 48 min',
    category: 'Sleep',
    icon: 'moon',
    tone: 'lavender',
    source: 'Musopen Open Classical Archive',
    license: 'Public Domain / CC0',
    attribution: 'Slow acoustic piano chords and warm harmonic overtones',
    url: '/audio/peaceful-piano.wav',
    audio_url: '/audio/peaceful-piano.wav',
    duration_seconds: 2880,
  },
  {
    id: 'music-calm-ambient',
    title: 'Calm Ambient Music',
    artist: 'The Sunday Room',
    kind: 'Focus · 38 min',
    category: 'Focus',
    icon: 'coffee',
    tone: 'blue',
    source: 'Creative Commons Archive',
    license: 'CC-BY 4.0 / Free License',
    attribution: 'Warm evolving synthesizer pad for deep mindfulness and calm',
    url: '/audio/calm-ambient.wav',
    audio_url: '/audio/calm-ambient.wav',
    duration_seconds: 2280,
  },
  {
    id: 'music-night-crickets',
    title: 'Night Crickets',
    artist: 'Summer Meadow',
    kind: 'Sleep · 60 min',
    category: 'Sleep',
    icon: 'moon',
    tone: 'lavender',
    source: 'Summer Evening Sound Archive',
    license: 'CC0 / Public Domain',
    attribution: 'Steady rhythmic evening field crickets under a quiet night sky',
    url: '/audio/night-crickets.wav',
    audio_url: '/audio/night-crickets.wav',
    duration_seconds: 3600,
  },
  {
    id: 'music-flowing-water',
    title: 'Flowing Water',
    artist: 'Mountain Stream',
    kind: 'Nature · 45 min',
    category: 'Nature',
    icon: 'rain',
    tone: 'mint',
    source: 'Natural Waterway Audio Archive',
    license: 'CC0 / Public Domain',
    attribution: 'Crisp freshwater stream flowing gently over river stones',
    url: '/audio/flowing-water.wav',
    audio_url: '/audio/flowing-water.wav',
    duration_seconds: 2700,
  },
  {
    id: 'music-deep-focus',
    title: 'Deep Focus Ambience',
    artist: 'BhaavaBot Sessions',
    kind: 'Focus · 42 min',
    category: 'Focus',
    icon: 'coffee',
    tone: 'peach',
    source: 'Royalty Free Community Soundscape',
    license: 'CC0 / Free License',
    attribution: '432Hz ambient drone tuned for sustained calm concentration',
    url: '/audio/deep-focus.wav',
    audio_url: '/audio/deep-focus.wav',
    duration_seconds: 2520,
  },
  {
    id: 'music-ambient-1',
    title: 'Quiet corners',
    artist: 'BhaavaBot sessions',
    kind: 'Focus · 42 min',
    category: 'Focus',
    icon: 'moon',
    tone: 'mint',
    source: 'Royalty Free Community Soundscape',
    license: 'CC0',
    attribution: 'Freely licensed royalty-free ambient soundscape',
    url: '/audio/deep-focus.wav',
    audio_url: '/audio/deep-focus.wav',
    duration_seconds: 2520,
  },
  {
    id: 'music-ambient-2',
    title: 'Soft landing',
    artist: 'The Sunday Room',
    kind: 'Ambient · 38 min',
    category: 'Sleep',
    icon: 'sun',
    tone: 'lavender',
    source: 'Creative Commons',
    license: 'CC-BY',
    attribution: 'Composed for mindfulness and slow breathing',
    url: '/audio/calm-ambient.wav',
    audio_url: '/audio/calm-ambient.wav',
    duration_seconds: 2280,
  },
  {
    id: 'music-ambient-3',
    title: 'Evening tea',
    artist: 'Low Tide Club',
    kind: 'Lo-fi · 46 min',
    category: 'Focus',
    icon: 'coffee',
    tone: 'blue',
    source: 'Royalty Free Community Archive',
    license: 'CC0',
    attribution: 'Gentle acoustic and lo-fi textures',
    url: '/audio/peaceful-piano.wav',
    audio_url: '/audio/peaceful-piano.wav',
    duration_seconds: 2760,
  },
]

const bookItems: (BookItem & { artist?: string })[] = [
  {
    id: 'book-bhagavad-gita',
    title: 'Bhagavad Gita',
    author: 'Vyasa (Translated by Sir Edwin Arnold)',
    artist: 'Vyasa · Edwin Arnold',
    kind: 'Philosophy · Spiritual Wisdom',
    category: 'Philosophy',
    tradition: 'Hinduism',
    language: 'English (Verse from Sanskrit)',
    icon: 'sun',
    tone: 'peach',
    description: 'A profound dialogue between Prince Arjuna and Krishna addressing duty, devotion, selflessness, and inner peace on the battlefield of life.',
    reading_url: 'https://www.gutenberg.org/ebooks/2388',
    url: 'https://www.gutenberg.org/ebooks/2388',
    source_name: 'Project Gutenberg',
    source: 'Project Gutenberg',
    license: 'Public Domain',
  },
  {
    id: 'book-ramayana',
    title: 'Ramayana',
    author: 'Valmiki (Translated by Ralph T. H. Griffith)',
    artist: 'Valmiki · Ralph T. H. Griffith',
    kind: 'Epic · Dharma · Devotion',
    category: 'Epic',
    tradition: 'Hinduism',
    language: 'English (Verse from Sanskrit)',
    icon: 'moon',
    tone: 'mint',
    description: 'The ancient Indian epic chronicling Rama\'s journey of righteousness, devotion, compassion, and courage amidst exile and adversity.',
    reading_url: 'https://www.gutenberg.org/ebooks/24869',
    url: 'https://www.gutenberg.org/ebooks/24869',
    source_name: 'Project Gutenberg',
    source: 'Project Gutenberg',
    license: 'Public Domain',
  },
  {
    id: 'book-mahabharata',
    title: 'Mahabharata',
    author: 'Krishna-Dwaipayana Vyasa (Translated by Kisari Mohan Ganguli)',
    artist: 'Vyasa · Kisari Mohan Ganguli',
    kind: 'Epic · Ethics · Wisdom',
    category: 'Epic',
    tradition: 'Hinduism',
    language: 'English (Prose from Sanskrit)',
    icon: 'sun',
    tone: 'lavender',
    description: 'The monumental epic exploring human destiny, conflict resolution, dharma, statecraft, and the search for liberation and truth.',
    reading_url: 'https://www.gutenberg.org/ebooks/15474',
    url: 'https://www.gutenberg.org/ebooks/15474',
    source_name: 'Project Gutenberg',
    source: 'Project Gutenberg',
    license: 'Public Domain',
  },
  {
    id: 'book-bible',
    title: 'The Holy Bible',
    author: 'King James Version',
    artist: 'King James Version',
    kind: 'Sacred Text · Faith · Compassion',
    category: 'Sacred Text',
    tradition: 'Christianity',
    language: 'English (King James Version)',
    icon: 'coffee',
    tone: 'peach',
    description: 'The sacred scriptures of Christianity, offering timeless teachings on faith, unconditional love, solace, and spiritual redemption.',
    reading_url: 'https://www.gutenberg.org/ebooks/10',
    url: 'https://www.gutenberg.org/ebooks/10',
    source_name: 'Project Gutenberg',
    source: 'Project Gutenberg',
    license: 'Public Domain',
  },
  {
    id: 'book-quran',
    title: 'The Holy Quran',
    author: 'Translated by J. M. Rodwell',
    artist: 'J. M. Rodwell Translation',
    kind: 'Sacred Text · Mercy · Guidance',
    category: 'Sacred Text',
    tradition: 'Islam',
    language: 'English (Translation from Arabic)',
    icon: 'rain',
    tone: 'mint',
    description: 'The central religious text of Islam, illuminating the path of patience, gratitude, moral integrity, divine mercy, and reflection.',
    reading_url: 'https://www.gutenberg.org/ebooks/2800',
    url: 'https://www.gutenberg.org/ebooks/2800',
    source_name: 'Project Gutenberg',
    source: 'Project Gutenberg',
    license: 'Public Domain',
  },
]

function CompanionMark() {
  return <div className="companion-mark" aria-hidden="true"><span /><span /><span /></div>
}

function renderArtworkIcon(iconKey: string, isMusic: boolean) {
  if (iconKey === 'moon') return <Moon style={{ width: 38, height: 38, strokeWidth: 1.75 }} />
  if (iconKey === 'sun') return <Sun style={{ width: 40, height: 40, strokeWidth: 1.75 }} />
  if (iconKey === 'coffee') return <Coffee style={{ width: 36, height: 36, strokeWidth: 1.75 }} />
  if (iconKey === 'rain') return <CloudRain style={{ width: 38, height: 38, strokeWidth: 1.75 }} />
  if (iconKey === 'book' || !isMusic) return <BookOpen style={{ width: 36, height: 36, strokeWidth: 1.75 }} />
  return <Music2 style={{ width: 36, height: 36, strokeWidth: 1.75 }} />
}

function MediaView({
  type,
  filter,
  setFilter,
  activeMedia,
  setActiveMedia,
  favorites,
  onToggleFavorite,
  onSwitchType,
  showToast,
}: {
  type: 'Music' | 'Books'
  filter: string
  setFilter: (filter: string) => void
  activeMedia: string | null
  setActiveMedia: (title: string | null) => void
  favorites: string[]
  onToggleFavorite: (title: string, itemType?: 'book' | 'music') => void
  onSwitchType: (type: 'Music' | 'Books') => void
  showToast?: (msg: string) => void
}) {
  const [books, setBooks] = useState<BookItem[]>([])
  const [musicList, setMusicList] = useState<MusicItem[]>([])
  const [isLoadingBooks, setIsLoadingBooks] = useState(false)
  const [bookError, setBookError] = useState<string | null>(null)

  // Audio playback state
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTrack, setCurrentTrack] = useState<any | null>(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isMuted, setIsMuted] = useState(false)

  const isMusic = type === 'Music'
  const targetDuration = currentTrack?.duration_seconds || (duration > 0 ? duration : 3600)

  // Session playback timer: smoothly tracks the full session length (e.g. 60 min) while ambient audio loops seamlessly
  useEffect(() => {
    if (!isPlaying || !currentTrack) return
    const targetDur = currentTrack.duration_seconds || 3600

    const timer = setInterval(() => {
      setCurrentTime((prev) => {
        if (prev + 1 >= targetDur) {
          const audio = audioRef.current
          if (audio) audio.pause()
          setIsPlaying(false)
          showToast?.(`${currentTrack.title} session completed.`)
          return targetDur
        }
        return prev + 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [isPlaying, currentTrack, showToast])

  // Load books from backend or fallback
  useEffect(() => {
    let isMounted = true
    async function loadBooks() {
      setIsLoadingBooks(true)
      setBookError(null)
      try {
        const data = await fetchBooks('For you')
        if (isMounted) {
          if (data && data.length > 0) {
            setBooks(data)
          } else {
            setBooks(bookItems)
          }
        }
      } catch (err) {
        if (isMounted) {
          console.warn('Could not load books from API:', err)
          setBookError('Unable to load reading resources. Tap to retry.')
        }
      } finally {
        if (isMounted) setIsLoadingBooks(false)
      }
    }

    if (!isMusic) {
      loadBooks()
    }

    return () => {
      isMounted = false
    }
  }, [isMusic])

  // Load music from backend or fallback
  useEffect(() => {
    let isMounted = true
    async function loadMusic() {
      try {
        const data = await fetchMusic('For you')
        if (isMounted && data && data.length > 0) {
          setMusicList(data)
        }
      } catch {
        // Fallback already defaults to musicItems
      }
    }

    if (isMusic) {
      loadMusic()
    }

    return () => {
      isMounted = false
    }
  }, [isMusic])

  const items = isMusic
    ? (musicList.length > 0 ? musicList : musicItems)
    : (books.length > 0 ? books : bookItems)

  const filters = isMusic
    ? ['For you', 'Focus', 'Sleep', 'Nature']
    : ['For you', 'Philosophy', 'Epic', 'Sacred Text']
  const featured = items[0]

  const displayedItems =
    filter === 'Saved' || filter === 'My list'
      ? items.filter((item) => favorites.includes(item.title))
      : filter === 'For you'
      ? items
      : items.filter((item: any) => {
          const f = filter.toLowerCase().trim()
          return (
            (item.kind && item.kind.toLowerCase().includes(f)) ||
            (item.category && item.category.toLowerCase().includes(f)) ||
            (item.tradition && item.tradition.toLowerCase().includes(f))
          )
        })

  function playTrack(item: any) {
    const audio = audioRef.current
    if (!audio) return

    // Toggle play/pause if this track is already selected
    if (currentTrack && currentTrack.title === item.title) {
      if (!audio.paused) {
        audio.pause()
      } else {
        audio
          .play()
          .then(() => setIsPlaying(true))
          .catch((e) => {
            console.warn('Play prevented:', e)
            setIsPlaying(false)
            showToast?.('Click play to start listening.')
          })
      }
      return
    }

    // Switch to new track
    setCurrentTrack(item)
    setActiveMedia(item.title)
    setCurrentTime(0)

    const audioSource = item.audio_url || item.url || '/audio/gentle-forest-rain.wav'
    audio.src = audioSource
    audio.currentTime = 0
    audio.load()
    audio
      .play()
      .then(() => {
        setIsPlaying(true)
        showToast?.(`Now playing: ${item.title}`)
      })
      .catch((err) => {
        console.warn('Playback error / Autoplay prevented:', err)
        setIsPlaying(false)
        showToast?.('Click play on the bottom bar to listen.')
      })
  }

  function togglePlayPause() {
    const audio = audioRef.current
    if (!audio || !currentTrack) return
    if (!audio.paused) {
      audio.pause()
    } else {
      audio
        .play()
        .then(() => setIsPlaying(true))
        .catch((e) => {
          console.warn('Play failed:', e)
          setIsPlaying(false)
        })
    }
  }

  function handleSeek(val: number) {
    setCurrentTime(val)
    const audio = audioRef.current
    if (audio && audio.duration && isFinite(audio.duration) && audio.duration > 0) {
      audio.currentTime = val % audio.duration
    }
  }

  function toggleMute() {
    const audio = audioRef.current
    if (audio) {
      audio.muted = !isMuted
      setIsMuted(!isMuted)
    }
  }

  function handleClosePlayer() {
    const audio = audioRef.current
    if (audio) {
      audio.pause()
      audio.src = ''
    }
    setIsPlaying(false)
    setCurrentTrack(null)
    setActiveMedia(null)
    setCurrentTime(0)
  }

  function handleSelectMedia(item: any) {
    if (isMusic) {
      playTrack(item)
    } else {
      setActiveMedia(item.title)
      const targetUrl = item.reading_url || item.url
      if (targetUrl && (targetUrl.startsWith('http://') || targetUrl.startsWith('https://'))) {
        try {
          const win = window.open(targetUrl, '_blank', 'noopener,noreferrer')
          if (!win) {
            showToast?.('Please allow popups to open the reading text.')
          }
        } catch {
          showToast?.('Unable to open reading link.')
        }
      } else {
        showToast?.('Reading link is currently unavailable for this title.')
      }
    }
  }

  return (
    <div className="resources-view">
      {/* Native HTML5 Audio Element with Seamless Ambient Looping */}
      <audio
        ref={audioRef}
        preload="auto"
        loop
        onLoadedMetadata={(e) => {
          const d = e.currentTarget.duration
          if (d && !isNaN(d) && isFinite(d)) {
            setDuration(d)
          }
        }}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onError={(e) => {
          console.warn('Audio element playback error:', e)
          setIsPlaying(false)
        }}
      />
      {/* Subtle Category Switcher */}
      <div className="resource-type-toggle">
        <button
          type="button"
          className={`resource-type-btn ${isMusic ? 'active' : ''}`}
          onClick={() => {
            onSwitchType('Music')
            setFilter('For you')
          }}
        >
          <Music2 style={{ width: 14, height: 14 }} />
          <span>Soundscapes</span>
        </button>
        <button
          type="button"
          className={`resource-type-btn ${!isMusic ? 'active' : ''}`}
          onClick={() => {
            onSwitchType('Books')
            setFilter('For you')
          }}
        >
          <BookOpen style={{ width: 14, height: 14 }} />
          <span>Readings</span>
        </button>
      </div>

      {/* 1. Hero Banner Card */}
      <div className="resource-hero-card">
        <span className="resource-hero-eyebrow">
          {isMusic ? 'A GENTLE LISTEN' : 'SACRED TEXTS & READINGS'}
        </span>
        <h2 className="resource-hero-title">
          {isMusic ? 'Let the room get quieter.' : 'Timeless wisdom for your inner world.'}
        </h2>
        <p className="resource-hero-desc">
          {isMusic
            ? 'A collection of licensed ambient soundscapes, nature rain, and peaceful acoustic harmonies.'
            : 'Explore public domain sacred texts and epics including the Bhagavad Gita, Ramayana, Mahabharata, Bible, and Quran.'}
        </p>
        <button
          className="resource-hero-btn"
          onClick={() => {
            if (featured) {
              handleSelectMedia(featured)
            }
          }}
          type="button"
        >
          {isMusic && isPlaying && currentTrack?.title === featured?.title ? (
            <Pause style={{ width: 13, height: 13 }} />
          ) : (
            <Play style={{ width: 13, height: 13 }} />
          )}
          <span>
            {isMusic
              ? isPlaying && currentTrack?.title === featured?.title
                ? 'Pause soundscape'
                : currentTrack?.title === featured?.title
                ? 'Resume listening'
                : 'Start listening'
              : activeMedia === featured?.title
              ? 'Reading now'
              : 'Start reading'}
          </span>
        </button>
      </div>

      {/* 2. Filter & Saved Bar */}
      <div className="resource-filter-bar">
        <div className="resource-filter-chips">
          {filters.map((item) => (
            <button
              key={item}
              type="button"
              className={`resource-filter-chip ${filter === item ? 'active' : ''}`}
              onClick={() => setFilter(item)}
            >
              {item}
            </button>
          ))}
        </div>
        <button
          type="button"
          className={`resource-saved-btn ${filter === 'Saved' ? 'active' : ''}`}
          onClick={() => setFilter(filter === 'Saved' ? 'For you' : 'Saved')}
          aria-label={`Saved items (${favorites.length})`}
        >
          <Heart
            style={{
              width: 16,
              height: 16,
              fill: filter === 'Saved' ? '#cf6674' : 'none',
              color: filter === 'Saved' ? '#cf6674' : 'currentColor',
            }}
          />
          <span>{favorites.length}</span>
        </button>
      </div>

      {/* 3. Curated Section Header */}
      <div className="resource-section-heading">
        <span className="resource-section-eyebrow">CURATED FOR YOU</span>
        <h3 className="resource-section-title">
          {isMusic ? 'A softer soundtrack' : 'A quiet little library'}
        </h3>
      </div>

      {/* 4. Responsive Card Grid */}
      <div className="resource-grid">
        {!isMusic && isLoadingBooks ? (
          <div style={{ gridColumn: '1 / -1', padding: '36px', textAlign: 'center', color: '#7e9692' }}>
            <div className="new-conversation-orb" style={{ margin: '0 auto 12px auto', width: 36, height: 36 }}>
              <BookOpen style={{ width: 18, height: 18, color: '#3ea684' }} />
            </div>
            <p style={{ fontSize: '13px', letterSpacing: '0.02em' }}>Loading sacred texts and quiet readings...</p>
          </div>
        ) : !isMusic && bookError && books.length === 0 ? (
          <div style={{ gridColumn: '1 / -1', padding: '36px', textAlign: 'center', color: '#c57878' }}>
            <p style={{ fontSize: '13px', marginBottom: '12px' }}>{bookError}</p>
            <button
              type="button"
              className="resource-filter-chip active"
              style={{ margin: '0 auto', display: 'inline-flex' }}
              onClick={() => {
                setIsLoadingBooks(true)
                setBookError(null)
                fetchBooks('For you')
                  .then((data) => setBooks(data && data.length > 0 ? data : bookItems))
                  .catch(() => setBookError('Unable to load reading resources. Tap to retry.'))
                  .finally(() => setIsLoadingBooks(false))
              }}
            >
              Retry
            </button>
          </div>
        ) : displayedItems.length === 0 ? (
          <div style={{ gridColumn: '1 / -1', padding: '24px', textAlign: 'center', color: '#7e9692' }}>
            <p>
              {filter === 'Saved'
                ? 'No saved items yet. Tap the heart on any card to save it.'
                : 'No items found matching this category.'}
            </p>
          </div>
        ) : (
          displayedItems.map((item: any) => {
            const isFav = favorites.includes(item.title)
            const readingLink = item.reading_url || item.url
            const isThisTrackPlaying = isMusic && currentTrack?.title === item.title
            return (
              <article
                key={item.id || item.title}
                className={`resource-card ${isThisTrackPlaying ? 'is-playing' : ''}`}
                onClick={() => handleSelectMedia(item)}
                style={{ cursor: 'pointer' }}
              >
                <div className={`resource-artwork ${item.tone || 'peach'}`}>
                  <button
                    type="button"
                    className={`resource-fav-btn ${isFav ? 'active' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation()
                      onToggleFavorite(item.title, isMusic ? 'music' : 'book')
                    }}
                    aria-label={`Save ${item.title}`}
                  >
                    <Heart
                      style={{
                        width: 14,
                        height: 14,
                        fill: isFav ? '#cf6674' : 'none',
                        color: isFav ? '#cf6674' : '#50726d',
                      }}
                    />
                  </button>
                  <div className="resource-artwork-center">
                    {renderArtworkIcon(item.icon, isMusic)}
                  </div>
                  {isThisTrackPlaying && (
                    <div className="resource-card-playing-badge">
                      {isPlaying ? (
                        <>
                          <div className="playing-bars">
                            <span className="playing-bar" />
                            <span className="playing-bar" />
                            <span className="playing-bar" />
                          </div>
                          <span>Playing</span>
                        </>
                      ) : (
                        <span>Paused</span>
                      )}
                    </div>
                  )}
                </div>
                <div className="resource-card-info">
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '4px' }}>
                    <h4 className="resource-card-title">{item.title}</h4>
                    {!isMusic && readingLink && (
                      <ArrowUpRight
                        style={{ width: 14, height: 14, color: '#7e9692', flexShrink: 0 }}
                        aria-hidden="true"
                      />
                    )}
                  </div>
                  <p className="resource-card-artist">{item.author || item.artist}</p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                    <span className="resource-card-meta">{item.kind}</span>
                    {item.language && (
                      <span className="resource-card-meta" style={{ opacity: 0.8 }}>· {item.language}</span>
                    )}
                  </div>
                </div>
              </article>
            )
          })
        )}
      </div>

      {/* 5. Now Playing Floating Bar with Native HTML5 Controls */}
      {((isMusic && currentTrack) || (!isMusic && activeMedia)) && (
        <div className="now-playing">
          <div className="now-playing-top">
            <div className="now-playing-mark">
              {isMusic ? (isPlaying ? <Volume2 /> : <Music2 />) : <BookOpen />}
            </div>
            <div className="now-playing-info">
              <strong className="now-playing-title">
                {isMusic ? (currentTrack?.title || activeMedia) : activeMedia}
              </strong>
              <span className="now-playing-subtitle">
                {isMusic
                  ? `${currentTrack?.artist || 'BhaavaBot'} · ${currentTrack?.kind || 'Soundscape'}`
                  : 'Reading selection · opened in new tab'}
              </span>
            </div>
            {isMusic && (
              <>
                <button
                  type="button"
                  className="now-playing-btn"
                  onClick={togglePlayPause}
                  aria-label={isPlaying ? 'Pause' : 'Play'}
                >
                  {isPlaying ? <Pause /> : <Play style={{ marginLeft: 2 }} />}
                </button>
                <button
                  type="button"
                  className="now-playing-volume-btn"
                  onClick={toggleMute}
                  aria-label={isMuted ? 'Unmute' : 'Mute'}
                >
                  {isMuted ? <VolumeX /> : <Volume2 />}
                </button>
              </>
            )}
            {!isMusic && (
              <button
                type="button"
                className="resource-filter-chip"
                style={{ padding: '4px 10px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}
                onClick={() => {
                  const current = (items as any[]).find((i) => i.title === activeMedia)
                  const url = current?.reading_url || current?.url
                  if (url && (url.startsWith('http://') || url.startsWith('https://'))) {
                    window.open(url, '_blank', 'noopener,noreferrer')
                  } else {
                    showToast?.('Reading link is currently unavailable for this resource.')
                  }
                }}
              >
                <span>Re-open</span>
                <ArrowUpRight style={{ width: 12, height: 12 }} />
              </button>
            )}
            <button
              className="now-playing-close"
              onClick={handleClosePlayer}
              aria-label="Close selection"
            >
              <X style={{ width: 15, height: 15 }} />
            </button>
          </div>
          {isMusic && (targetDuration > 0 || currentTrack) && (
            <div className="now-playing-scrubber">
              <span className="now-playing-time">{formatAudioTime(currentTime)}</span>
              <input
                type="range"
                className="now-playing-progress"
                min={0}
                max={targetDuration}
                step={1}
                value={currentTime}
                onChange={(e) => handleSeek(parseFloat(e.target.value))}
                aria-label="Audio progress scrubber"
              />
              <span className="now-playing-time">{formatAudioTime(targetDuration)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const moodOptions = [
  { label: 'Calm', desc: 'settled and steady', dotColor: '#3ea684' },
  { label: 'Tired', desc: 'low on energy', dotColor: '#6398b6' },
  { label: 'Heavy', desc: 'weighed down', dotColor: '#9886b6' },
  { label: 'Hopeful', desc: 'a little lighter', dotColor: '#d69772' },
]

const defaultThemes: ThemeItem[] = [
  { id: 't1', title: 'I just want someone to listen', icon: '🌸', tagline: '', description: '' },
  { id: 't2', title: 'Help me calm down', icon: '🌿', tagline: '', description: '' },
  { id: 't3', title: 'I need to get this out', icon: '💬', tagline: '', description: '' },
  { id: 't4', title: 'I want to take my mind off things', icon: '📖', tagline: '', description: '' },
  { id: 't5', title: 'Help me understand', icon: '🔍', tagline: '', description: '' },
]

function HomeDashboard({
  onStart,
  onMoodCheckin,
  lastCheckin,
  themes,
  selectedTheme,
  onSelectTheme,
  conversations,
  onSelectConversation,
  onGoToReflections,
}: {
  onStart: () => void
  onMoodCheckin: (mood: string) => void
  lastCheckin: string | null
  themes: ThemeItem[]
  selectedTheme: string
  onSelectTheme: (theme: string) => void
  conversations: ConversationItem[]
  onSelectConversation: (conv: ConversationItem) => void
  onGoToReflections: () => void
}) {
  const allThemes = themes.length > 0 ? themes : defaultThemes

  return (
    <div className="home-dashboard">
      {/* 1. DAILY CHECK-IN 2x2 PILL CARDS */}
      <section className="home-checkin-section">
        <div className="home-section-header">
          <span className="home-section-eyebrow">DAILY CHECK-IN</span>
          <span className="home-section-meta">Tap one</span>
        </div>
        <div className="home-mood-grid">
          {moodOptions.map((m) => (
            <button
              key={m.label}
              onClick={() => onMoodCheckin(m.label)}
              className={`home-mood-card ${lastCheckin === m.label ? 'active' : ''}`}
              type="button"
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                <span className="mood-dot" style={{ background: m.dotColor }} />
                <span className="mood-label">{m.label}</span>
              </div>
              <span className="mood-desc">{m.desc}</span>
            </button>
          ))}
        </div>
      </section>

      {/* 2. A MOMENT FOR YOU HERO CARD */}
      <section
        className="home-moment-card"
        onClick={onStart}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter') onStart()
        }}
      >
        <div className="home-moment-left">
          <div className="home-moment-eyebrow">
            <Sparkles style={{ width: 13, height: 13 }} />
            <span>A MOMENT FOR YOU</span>
          </div>
          <h2 className="home-moment-title">Start a conversation</h2>
          <p className="home-moment-desc">I&apos;m here to listen, without judgment.</p>
        </div>
        <div className="home-moment-btn" aria-label="Start a conversation">
          <ArrowUpRight style={{ width: 20, height: 20 }} />
        </div>
      </section>

      {/* 3. SESSION FOCUS */}
      <section className="home-focus-section">
        <div className="home-section-header">
          <span className="home-section-eyebrow">SESSION FOCUS</span>
        </div>
        <div className="home-focus-chips">
          {allThemes.map((t) => (
            <button
              key={t.title}
              onClick={() => onSelectTheme(t.title)}
              className={`home-focus-chip ${selectedTheme === t.title ? 'active' : ''}`}
              type="button"
            >
              <span className="home-focus-icon">{t.icon}</span>
              <span>{t.title}</span>
            </button>
          ))}
        </div>
      </section>

      {/* 4. CONTINUE (PAST CONVERSATIONS) */}
      <section className="home-continue-section">
        <div className="home-section-header">
          <span className="home-section-eyebrow">CONTINUE</span>
          <span className="home-section-meta">{conversations.length} saved</span>
        </div>
        <div className="home-continue-list">
          {conversations.length === 0 ? (
            <div className="home-continue-empty">
              <p>No saved conversations yet. Tap above to begin.</p>
            </div>
          ) : (
            conversations.slice(0, 3).map((conv) => (
              <div
                key={conv.id}
                className="home-continue-card"
                onClick={() => onSelectConversation(conv)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') onSelectConversation(conv)
                }}
              >
                <div className="home-continue-info">
                  <div className="home-continue-top">
                    <h4 className="home-continue-title">{conv.title || 'A Quiet Conversation'}</h4>
                    <span className="home-continue-date">
                      {conv.created_at
                        ? new Date(conv.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })
                        : 'Recent'}
                    </span>
                  </div>
                  <p className="home-continue-preview">
                    {conv.preview || 'Feeling a little overwhelmed lately...'}
                  </p>
                </div>
                <ChevronRight className="home-continue-arrow" />
              </div>
            ))
          )}
        </div>
      </section>

      {/* 5. A SMALL STEP · 2 MIN */}
      <section
        className="home-step-card"
        onClick={onGoToReflections}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter') onGoToReflections()
        }}
      >
        <div className="home-step-sun">
          <Sun style={{ width: 22, height: 22 }} />
        </div>
        <div className="home-step-body">
          <span className="home-step-eyebrow">A SMALL STEP · 2 MIN</span>
          <h3 className="home-step-title">Put it into words</h3>
          <p className="home-step-desc">What has been taking up space in your mind?</p>
          <div className="home-step-link">
            <span>Write a reflection</span>
            <ChevronRight style={{ width: 14, height: 14 }} />
          </div>
        </div>
      </section>
    </div>
  )
}

function NewConversationView({ onPrompt }: { onPrompt: (prompt: string) => void }) {
  return (
    <div className="new-conversation-view">
      <div className="new-conversation-orb"><CompanionMark /></div>
      <span className="eyebrow">A PRIVATE MOMENT</span>
      <h2>Start a new conversation.</h2>
      <p>This space is yours. You can talk about what is happening right now, or begin with one of the prompts below.</p>
      <div className="new-prompt-list">
        {['Something has been on my mind…', 'Help me make sense of my feelings', 'I just need someone to listen'].map((prompt) => (
          <button key={prompt} onClick={() => onPrompt(prompt)}>
            <Sparkles />
            <span>{prompt}</span>
            <ArrowUp />
          </button>
        ))}
      </div>
    </div>
  )
}

function ResourcesView(props: Omit<React.ComponentProps<typeof MediaView>, 'type' | 'onSwitchType'>) {
  const [category, setCategory] = useState<'Music' | 'Books'>('Music')
  return <MediaView {...props} type={category} onSwitchType={setCategory} />
}

function formatReflectionDate(dateStr: string): string {
  if (!dateStr) return 'Just now'
  if (dateStr.includes(' · ')) return dateStr
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr

    const now = new Date()
    const isToday =
      d.getDate() === now.getDate() &&
      d.getMonth() === now.getMonth() &&
      d.getFullYear() === now.getFullYear()

    const yesterday = new Date(now)
    yesterday.setDate(now.getDate() - 1)
    const isYesterday =
      d.getDate() === yesterday.getDate() &&
      d.getMonth() === yesterday.getMonth() &&
      d.getFullYear() === yesterday.getFullYear()

    const timeStr = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
    if (isToday) return `Today · ${timeStr}`
    if (isYesterday) return `Yesterday · ${timeStr}`

    const monthStr = d.toLocaleDateString([], { month: 'short', day: 'numeric' })
    return `${monthStr} · ${timeStr}`
  } catch {
    return dateStr
  }
}

function ReflectionsView({
  reflections,
  onAddReflection,
}: {
  reflections: ReflectionItem[]
  onAddReflection: (mood: string, note: string) => Promise<boolean>
}) {
  const [isAdding, setIsAdding] = useState(false)
  const [selectedMood, setSelectedMood] = useState('Calm')
  const [noteText, setNoteText] = useState('')
  const [saving, setSaving] = useState(false)

  const moodColors: Record<string, string> = {
    Calm: '#3ea684',
    Hopeful: '#d69772',
    Heavy: '#9886b6',
    Tired: '#6398b6',
  }

  async function handleSave() {
    if (saving) return
    setSaving(true)
    const ok = await onAddReflection(selectedMood, noteText.trim())
    setSaving(false)
    if (ok) {
      setNoteText('')
      setIsAdding(false)
    }
  }

  return (
    <div className="reflections-container">
      {/* + Add a reflection button */}
      <button
        className="reflections-add-btn"
        onClick={() => setIsAdding(true)}
        type="button"
      >
        <Plus style={{ width: 18, height: 18 }} />
        <span>Add a reflection</span>
      </button>

      {/* Add Reflection Modal */}
      {isAdding && (
        <div className="panel-backdrop" style={{ zIndex: 100 }} onClick={() => setIsAdding(false)}>
          <div className="reflection-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="reflection-modal-header">
              <div>
                <span className="reflection-modal-eyebrow">CAPTURE A MOMENT</span>
                <h3 className="reflection-modal-title">New reflection</h3>
                <p className="reflection-modal-desc">How are you feeling right now?</p>
              </div>
              <button
                className="close-panel"
                onClick={() => setIsAdding(false)}
                aria-label="Close"
              >
                <X />
              </button>
            </div>

            {/* Mood options */}
            <div className="reflection-mood-picker">
              {['Calm', 'Hopeful', 'Heavy', 'Tired'].map((m) => (
                <button
                  key={m}
                  type="button"
                  className={`reflection-mood-option ${selectedMood === m ? 'active' : ''}`}
                  onClick={() => setSelectedMood(m)}
                >
                  <span className="reflection-dot" style={{ background: moodColors[m] }} />
                  <span>{m}</span>
                </button>
              ))}
            </div>

            {/* Note text */}
            <div className="reflection-input-group">
              <label htmlFor="reflection-note-input">What has been taking up space in your mind?</label>
              <textarea
                id="reflection-note-input"
                rows={4}
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="Paused to take deep breaths in the garden..."
                className="reflection-textarea"
                autoFocus
              />
            </div>

            <div className="reflection-modal-actions">
              <button
                type="button"
                className="reflection-cancel-btn"
                onClick={() => setIsAdding(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="reflection-save-btn"
                disabled={saving}
                onClick={handleSave}
              >
                {saving ? 'Saving...' : 'Save reflection'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Section Title */}
      <h2 className="reflections-section-title">My reflections</h2>

      {/* Reflections List */}
      <div className="reflections-list">
        {reflections.length === 0 ? (
          <div className="reflections-empty">
            <Heart style={{ width: 28, height: 28, color: '#8da4a0', margin: '0 auto 10px' }} />
            <h4>A clear page can be a kind beginning.</h4>
            <p>Tap &quot;Add a reflection&quot; above or complete a daily check-in to record your moments.</p>
          </div>
        ) : (
          reflections.map((item) => (
            <article key={item.id} className="reflection-card">
              <div className="reflection-card-header">
                <div className="reflection-mood-group">
                  <span
                    className="reflection-dot"
                    style={{ background: moodColors[item.mood] || '#3ea684' }}
                  />
                  <strong className="reflection-mood">{item.mood}</strong>
                </div>
                <span className="reflection-date">
                  {formatReflectionDate(item.created_at)}
                </span>
              </div>
              {item.note ? (
                <p className="reflection-note">{item.note}</p>
              ) : (
                <p className="reflection-note muted">Daily inner weather check-in.</p>
              )}
            </article>
          ))
        )}
      </div>
    </div>
  )
}

function ProfileView({
  onSettings,
  onSafety,
  onOpenAssessment,
  profile,
}: {
  onSettings: () => void
  onSafety: () => void
  onOpenAssessment: () => void
  profile: EmpathyProfile | null
}) {
  return (
    <div className="simple-page">
      <span className="eyebrow">YOUR SPACE</span>
      <h2>Profile</h2>
      <p>Make BhaavaBot feel right for your personal rhythm.</p>

      <button className="profile-action" onClick={onOpenAssessment}>
        <Sparkles />
        <span>
          <strong>Empathy & companion style</strong>
          <small>
            {profile
              ? `Style: ${profile.communication_style} · ${profile.preferred_pacing} pacing`
              : 'Take the guided assessment to personalize companion pacing'}
          </small>
        </span>
        <ChevronDown />
      </button>

      <button className="profile-action" onClick={onSettings}>
        <Settings />
        <span>
          <strong>Settings</strong>
          <small>Preferences and reminders</small>
        </span>
        <ChevronDown />
      </button>

      <button className="profile-action" onClick={onSafety}>
        <ShieldCheck />
        <span>
          <strong>Safety & privacy</strong>
          <small>Crisis hotlines and privacy commitments</small>
        </span>
        <ChevronDown />
      </button>
    </div>
  )
}

function EmpathyAssessmentModal({
  onClose,
  onCompleted,
  userId,
}: {
  onClose: () => void
  onCompleted: (profile: EmpathyProfile) => void
  userId: string
}) {
  const [questions, setQuestions] = useState<EmpathyQuestion[]>([])
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [page, setPage] = useState(0)

  useEffect(() => {
    fetchEmpathyQuestions().then((q) => {
      setQuestions(q)
      setLoading(false)
    })
  }, [])

  const pageSize = 5
  const totalPages = Math.ceil(questions.length / pageSize)
  const currentQuestions = questions.slice(page * pageSize, (page + 1) * pageSize)

  const handleScore = (questionId: number, score: number) => {
    setAnswers((prev) => ({ ...prev, [questionId]: score }))
  }

  const isCurrentPageComplete = currentQuestions.every((q) => answers[q.id] !== undefined)
  const isAllComplete = questions.length > 0 && questions.every((q) => answers[q.id] !== undefined)

  async function handleSubmit() {
    setSubmitting(true)
    const formatted = Object.entries(answers).map(([qid, sc]) => ({
      question_id: Number(qid),
      score: sc,
    }))
    const res = await submitEmpathyAssessment(formatted, userId)
    setSubmitting(false)
    if (res) {
      onCompleted(res)
      onClose()
    }
  }

  const likertLabels = ['Never', 'Rarely', 'Sometimes', 'Often', 'Always']

  return (
    <div className="panel-backdrop" style={{ zIndex: 100 }} onClick={onClose}>
      <section
        className="info-panel"
        style={{ width: 'min(580px, 95%)', maxHeight: '90vh', overflowY: 'auto' }}
        onClick={(e) => e.stopPropagation()}
      >
        <button className="close-panel" onClick={onClose} aria-label="Close">
          <X />
        </button>
        <Sparkles className="panel-icon" />
        <h2>Personalize Your Companion</h2>
        <p style={{ marginBottom: '18px' }}>
          This guided self-reflection assessment helps Bhavabot adapt its emotional responsiveness, explanation depth, and pacing to you without judgment.
        </p>

        {loading ? (
          <p style={{ color: '#7d9691', fontSize: '13px' }}>Loading questions...</p>
        ) : (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px', fontSize: '11px', color: '#6d8985' }}>
              <span>Step {page + 1} of {totalPages}</span>
              <span>{Object.keys(answers).length} of {questions.length} answered</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              {currentQuestions.map((q) => (
                <div key={q.id} style={{ borderBottom: '1px solid #edf3f0', paddingBottom: '14px' }}>
                  <p style={{ margin: '0 0 10px', fontSize: '13px', color: '#2d5957', fontWeight: 550, lineHeight: 1.5 }}>
                    {q.id}. {q.text}
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '6px' }}>
                    {likertLabels.map((lbl, idx) => {
                      const isSelected = answers[q.id] === idx
                      return (
                        <button
                          key={lbl}
                          type="button"
                          onClick={() => handleScore(q.id, idx)}
                          style={{
                            padding: '8px 2px',
                            borderRadius: '10px',
                            border: `1px solid ${isSelected ? '#338f8c' : '#dce9e5'}`,
                            background: isSelected ? '#e6f4f1' : '#fff',
                            color: isSelected ? '#278d8a' : '#6d8985',
                            fontWeight: isSelected ? 700 : 500,
                            fontSize: '11px',
                            cursor: 'pointer',
                          }}
                        >
                          {lbl}
                        </button>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '24px' }}>
              <button
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                style={{
                  border: '1px solid #dce9e5',
                  background: '#fff',
                  borderRadius: '10px',
                  padding: '8px 16px',
                  color: '#6d8985',
                  cursor: page === 0 ? 'not-allowed' : 'pointer',
                  opacity: page === 0 ? 0.5 : 1,
                  fontSize: '12px',
                }}
              >
                Previous
              </button>

              {page < totalPages - 1 ? (
                <button
                  disabled={!isCurrentPageComplete}
                  onClick={() => setPage((p) => p + 1)}
                  className="panel-action"
                  style={{
                    opacity: !isCurrentPageComplete ? 0.5 : 1,
                    cursor: !isCurrentPageComplete ? 'not-allowed' : 'pointer',
                  }}
                >
                  Next step
                </button>
              ) : (
                <button
                  disabled={!isAllComplete || submitting}
                  onClick={handleSubmit}
                  className="panel-action"
                  style={{
                    opacity: !isAllComplete || submitting ? 0.5 : 1,
                    cursor: !isAllComplete || submitting ? 'not-allowed' : 'pointer',
                  }}
                >
                  {submitting ? 'Saving style...' : 'Complete personalization'}
                </button>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  )
}

export default function Page() {
  const [view, setView] = useState<'home' | 'chat' | 'reflections' | 'new' | 'resources' | 'profile'>('home')
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages)
  const [conversations, setConversations] = useState<ConversationItem[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string>('conv-welcome')
  const [draft, setDraft] = useState('')
  const [thinking, setThinking] = useState(false)
  const [listening, setListening] = useState(false)
  const [panel, setPanel] = useState<'settings' | 'safety' | 'assessment' | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior, block: 'end' })
    } else if (typeof window !== 'undefined') {
      window.scrollTo({ top: document.body.scrollHeight, behavior })
    }
  }, [])

  // Auto-scroll to show recent message and typing bar when in chat,
  // OR scroll smoothly to the very top when navigating to any other view (Home, Reflections, Resources, etc.)
  useEffect(() => {
    if (view === 'chat') {
      scrollToBottom('auto')
      const t1 = setTimeout(() => scrollToBottom('smooth'), 50)
      const t2 = setTimeout(() => scrollToBottom('smooth'), 200)
      return () => {
        clearTimeout(t1)
        clearTimeout(t2)
      }
    } else {
      if (typeof window !== 'undefined') {
        window.scrollTo({ top: 0, behavior: 'auto' })
      }
    }
  }, [view, activeConversationId, messages.length, thinking, scrollToBottom])

  // Open sidebar by default on desktop; keep closed as off-canvas drawer on phone
  useEffect(() => {
    if (typeof window !== 'undefined' && window.innerWidth > 760) {
      setSidebarOpen(true)
    }
  }, [])

  const [activeMedia, setActiveMedia] = useState<string | null>(null)
  const [favorites, setFavorites] = useState<string[]>([])
  const [mediaFilter, setMediaFilter] = useState('For you')
  const [reflections, setReflections] = useState<ReflectionItem[]>([])
  const [lastCheckin, setLastCheckin] = useState<string | null>(null)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [themes, setThemes] = useState<ThemeItem[]>([])
  const [selectedTheme, setSelectedTheme] = useState('I just want someone to listen')
  const [empathyProfile, setEmpathyProfile] = useState<EmpathyProfile | null>(null)
  const [emergencyContact, setEmergencyContact] = useState<EmergencyContact | null>(null)
  const [contactLoading, setContactLoading] = useState(true)
  const [editingContact, setEditingContact] = useState(false)
  const [crisisAlertBanner, setCrisisAlertBanner] = useState<string | null>(null)

  const { data: session, isPending } = authClient.useSession()
  const [guestMode, setGuestMode] = useState(false)

  // Load initial backend state on mount
  useEffect(() => {
    async function loadData() {
      const uid = session?.user?.id || 'guest'
      const [favs, refls, thms, prof, convs, contact] = await Promise.all([
        apiFetchFavorites(uid),
        fetchReflections(uid),
        fetchThemes(),
        fetchEmpathyProfile(uid),
        fetchConversations(uid),
        fetchEmergencyContact(uid),
      ])
      if (favs) setFavorites(favs)
      if (refls && refls.length > 0) setReflections(refls)
      if (thms) setThemes(thms)
      if (prof) setEmpathyProfile(prof)
      if (contact) setEmergencyContact(contact)
      setContactLoading(false)
      if (convs && convs.length > 0) {
        setConversations(convs)
        setActiveConversationId(convs[0].id)
        const initialMsgs = await fetchConversationMessages(convs[0].id)
        if (initialMsgs && initialMsgs.length > 0) {
          setMessages(initialMsgs)
        }
      }
    }
    loadData()
  }, [session?.user?.id, guestMode])

  async function startNewConversation(starterText?: string) {
    const uid = session?.user?.id || 'guest'
    const newConv = await createConversation('A Quiet Conversation', uid)
    if (newConv) {
      setConversations((prev) => [newConv, ...prev.filter((c) => c.id !== newConv.id)])
      setActiveConversationId(newConv.id)
    } else {
      const tempId = `conv-${Date.now()}`
      setActiveConversationId(tempId)
    }
    setMessages([])
    setView('chat')
    if (typeof window !== 'undefined' && window.innerWidth <= 760) setSidebarOpen(false)
    if (starterText) {
      handleSendMessage(starterText, newConv?.id)
    }
  }

  async function handleSelectConversation(conv: ConversationItem) {
    setActiveConversationId(conv.id)
    setView('chat')
    if (typeof window !== 'undefined' && window.innerWidth <= 760) setSidebarOpen(false)
    const msgs = await fetchConversationMessages(conv.id)
    setMessages(msgs)
  }

  async function handleDeleteConversation(e: React.MouseEvent, convId: string) {
    e.stopPropagation()
    await deleteConversation(convId)
    const remaining = conversations.filter((c) => c.id !== convId)
    setConversations(remaining)
    showToast('Conversation deleted')
    if (activeConversationId === convId) {
      if (remaining.length > 0) {
        handleSelectConversation(remaining[0])
      } else {
        startNewConversation()
      }
    }
  }

  async function handleSendMessage(value = draft, targetConvId?: string) {
    const text = value.trim()
    if (!text) return

    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    setMessages((current) => [...current, { from: 'user', text, time: now }])
    setDraft('')
    setThinking(true)

    const convId = targetConvId || activeConversationId || 'conv-welcome'
    const uid = session?.user?.id || 'guest'

    // Update conversation title if still generic
    const currentConv = conversations.find((c) => c.id === convId)
    if (currentConv && (currentConv.title === 'A Quiet Conversation' || currentConv.title === 'A fresh start')) {
      const newTitle = text.length > 28 ? `${text.slice(0, 26)}...` : text
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, title: newTitle } : c))
      )
    }

    // Call live FastAPI backend with adaptive context
    const res = await sendChatMessage(
      text,
      messages,
      convId,
      uid,
      selectedTheme,
      session?.user?.name || undefined
    )

    setMessages((current) => [
      ...current,
      {
        from: 'bot',
        text: res.reply,
        time: res.time || 'Just now',
        detected_emotion: res.detected_emotion,
        safety_level: res.safety_level,
      },
    ])
    setThinking(false)

    // If safety engine detected CRISIS or recommended crisis modal, open immediately
    if (res.suggested_action === 'show_crisis_modal' || res.safety_level === 'CRISIS') {
      setPanel('safety')
    }

    // If emergency alert was dispatched, notify user
    if (res.emergency_alert_dispatched) {
      const recipient = res.contact_notified || emergencyContact?.name || 'your emergency contact'
      setCrisisAlertBanner(`Emergency safety alert sent via Telegram to ${recipient}. A trusted loved one has been notified to check in on you.`)
      showToast(`🚨 Priority safety alert dispatched to ${recipient}`)
    }
  }

  async function handleMoodCheckin(mood: string) {
    setLastCheckin(mood)
    showToast(`Inner weather marked as ${mood}`)
    const res = await recordCheckin(mood, '', session?.user?.id || 'guest')
    if (res) {
      setReflections((prev) => [res, ...prev.filter((r) => r.id !== res.id)])
    }
  }

  async function handleAddReflection(mood: string, note: string): Promise<boolean> {
    const uid = session?.user?.id || 'guest'
    const res = await recordCheckin(mood, note, uid)
    if (res) {
      setReflections((prev) => [res, ...prev.filter((r) => r.id !== res.id)])
      showToast('Reflection saved to your inner world')
      return true
    } else {
      const fallback: ReflectionItem = {
        id: `refl-${Date.now()}`,
        mood,
        note,
        created_at: `Today · ${new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`,
      }
      setReflections((prev) => [fallback, ...prev])
      showToast('Reflection saved')
      return true
    }
  }

  async function handleToggleFavorite(title: string, itemType: 'book' | 'music' = 'music') {
    const isFav = favorites.includes(title)
    setFavorites(isFav ? favorites.filter((t) => t !== title) : [...favorites, title])
    await apiToggleFavorite(title, itemType, session?.user?.id || 'guest')
    showToast(isFav ? `Removed from saved list` : `Saved to your list`)
  }

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg)
    window.setTimeout(() => setToastMessage(null), 2500)
  }, [])

  // If session is still verifying or checking contact, show a gentle loading state
  if (isPending || ((session?.user || guestMode) && contactLoading)) {
    return (
      <main className="auth-page" style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
          <div className="new-conversation-orb">
            <CompanionMark />
          </div>
          <p style={{ color: '#6d8985', fontSize: '13px', letterSpacing: '0.04em' }}>
            Preparing your calm space...
          </p>
        </div>
      </main>
    )
  }

  // The first page that appears is the Login / Sign Up page
  if (!session?.user && !guestMode) {
    return (
      <main className="auth-page">
        <AuthForm mode="sign-in" onContinueGuest={() => setGuestMode(true)} />
      </main>
    )
  }

  // Mandatory Emergency Contact gating: User cannot access the app without a trusted contact
  if (!emergencyContact) {
    return (
      <main className="auth-page" style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '16px' }}>
        <EmergencyContactModal
          userId={session?.user?.id || 'guest'}
          userName={session?.user?.name || 'Mitwa Ninama'}
          isMandatory={true}
          onSaved={(contact) => {
            setEmergencyContact(contact)
            showToast(`Welcome! Emergency contact saved: ${contact.name}`)
          }}
        />
      </main>
    )
  }

  return (
    <main className={`app-shell ${view === 'chat' ? 'in-chat-view' : ''}`}>
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 4px 18px' }}>
          <div className="brand" style={{ padding: 0 }}>
            <CompanionMark />
            <div>
              <strong>BhaavaBot</strong>
              <span>your calm companion</span>
            </div>
          </div>
          <button
            className="sidebar-close-btn"
            onClick={() => setSidebarOpen(false)}
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose style={{ width: 17, height: 17 }} />
          </button>
        </div>
        <button
          className="new-chat"
          onClick={() => startNewConversation()}
        >
          <Plus data-icon="inline-start" /> New conversation
        </button>

        <div className="sidebar-section">
          <div className="sidebar-section-header">
            <span className="sidebar-section-title">Past conversations</span>
            <span style={{ fontSize: '11px', color: '#9aa9a6', fontWeight: 600 }}>{conversations.length}</span>
          </div>
          <div className="sidebar-conversations">
            {conversations.length === 0 ? (
              <div className="sidebar-empty">
                No past conversations yet.
              </div>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  role="button"
                  tabIndex={0}
                  className={`sidebar-conv-item ${activeConversationId === conv.id && view === 'chat' ? 'active' : ''}`}
                  onClick={() => handleSelectConversation(conv)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSelectConversation(conv)
                  }}
                  title={conv.title}
                >
                  <MessageSquare className="sidebar-conv-icon" />
                  <div className="sidebar-conv-content">
                    <span className="sidebar-conv-title">{conv.title || 'A Quiet Conversation'}</span>
                    <span className="sidebar-conv-time">
                      {conv.created_at ? new Date(conv.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' }) : 'Recent'}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="sidebar-conv-delete"
                    onClick={(e) => handleDeleteConversation(e, conv.id)}
                    title="Delete conversation"
                    aria-label="Delete conversation"
                  >
                    <Trash2 style={{ width: 12, height: 12 }} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="side-bottom">
          <button className="nav-item" onClick={() => setPanel('safety')}>
            <ShieldCheck data-icon="inline-start" /> Safety & privacy
          </button>
          <button className="nav-item" onClick={() => setPanel('settings')}>
            <Settings data-icon="inline-start" /> Settings
          </button>
          <div className="profile">
            <div className="avatar">{session?.user?.name?.slice(0, 1) ?? 'A'}</div>
            <div>
              <strong>{session?.user?.name ?? 'Guest explorer'}</strong>
              <span>
                {empathyProfile
                  ? `${empathyProfile.communication_style} · ${empathyProfile.preferred_pacing}`
                  : 'FastAPI + Supabase connected'}
              </span>
            </div>
            <MoreHorizontal />
          </div>
        </div>
      </aside>

      <section className="conversation">
        <header className="topbar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {view === 'chat' && (
              <button
                className="mobile-back-btn"
                onClick={() => setView('home')}
                aria-label="Back to home"
                title="Back to home"
              >
                <ArrowLeft style={{ width: 18, height: 18 }} />
              </button>
            )}
            <button
              className="sidebar-toggle-btn"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-label="Toggle sidebar"
              title={sidebarOpen ? "Collapse sidebar" : "Open sidebar"}
            >
              {sidebarOpen ? <PanelLeftClose /> : <PanelLeft />}
            </button>
            <div
              className="mobile-brand"
              onClick={() => setView('home')}
              style={{ cursor: 'pointer' }}
              title="Go to Home"
            >
              <CompanionMark />
              <strong>BhaavaBot</strong>
            </div>
          </div>
          <div className="top-actions">
            <button className="icon-button" aria-label="Notifications"><Bell /></button>
            {session?.user ? (
              <button className="account-link" onClick={() => authClient.signOut()}>Sign out</button>
            ) : (
              <Link className="account-link" href="/sign-in">Sign in</Link>
            )}
          </div>
        </header>

        <div className="conversation-inner">
          {view !== 'resources' && (
            <div className="conversation-heading">
              <div>
                <p className="eyebrow">
                  {view === 'chat'
                    ? 'COMPANION CHAT'
                    : view === 'reflections'
                    ? 'YOUR INNER WORLD'
                    : view === 'profile'
                    ? 'YOUR SPACE'
                    : 'TODAY’S COMPANION'}
                </p>
                <h1>
                  {view === 'reflections'
                    ? 'Notice what has changed'
                    : view === 'profile'
                    ? 'Your calm space.'
                    : view === 'chat'
                    ? (conversations.find((c) => c.id === activeConversationId)?.title || 'A quiet conversation.')
                    : view === 'new'
                    ? 'A fresh place to begin.'
                    : 'How are you feeling today?'}
                </h1>
                <p className="subheading">
                  {view === 'reflections'
                    ? 'Your daily check-ins and captured moments.'
                    : view === 'chat'
                    ? 'Take your time. There is no rush or judgment here.'
                    : 'Take a breath. There’s no rush here.'}
                </p>
              </div>
              {view !== 'reflections' && (
                <button className="help-button" onClick={() => setPanel('safety')}>
                  <CircleHelp /> <span>Need help?</span>
                </button>
              )}
            </div>
          )}

          {view === 'home' ? (
            <HomeDashboard
              onStart={() => startNewConversation()}
              onMoodCheckin={handleMoodCheckin}
              lastCheckin={lastCheckin}
              themes={themes}
              selectedTheme={selectedTheme}
              onSelectTheme={(t) => {
                setSelectedTheme(t)
                showToast(`Session focus set to: ${t}`)
              }}
              conversations={conversations}
              onSelectConversation={handleSelectConversation}
              onGoToReflections={() => setView('reflections')}
            />
          ) : view === 'chat' ? (
            <div className="chat-view-container">
              <div className="conversation-label" style={{ marginTop: 0 }}>
                <Sparkles /> {conversations.find((c) => c.id === activeConversationId)?.title || 'CONVERSATION'}
              </div>

              {crisisAlertBanner && (
                <div
                  style={{
                    margin: '8px 16px 12px',
                    padding: '12px 16px',
                    borderRadius: '14px',
                    backgroundColor: '#fef2f2',
                    border: '1px solid #fecaca',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    color: '#991b1b',
                    boxShadow: '0 4px 12px rgba(220, 38, 38, 0.08)',
                  }}
                >
                  <AlertCircle style={{ width: 22, height: 22, flexShrink: 0, color: '#dc2626' }} />
                  <div style={{ flex: 1, fontSize: '12.5px', lineHeight: 1.5 }}>
                    <strong style={{ display: 'block', fontSize: '13px', color: '#7f1d1d' }}>
                      Emergency Safety Alert Dispatched
                    </strong>
                    {crisisAlertBanner}
                  </div>
                  <button
                    onClick={() => setCrisisAlertBanner(null)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#991b1b',
                      cursor: 'pointer',
                      padding: '4px',
                      display: 'grid',
                      placeItems: 'center',
                    }}
                    aria-label="Dismiss alert"
                  >
                    <X style={{ width: 16, height: 16 }} />
                  </button>
                </div>
              )}
              <div className="message-area" aria-live="polite">
                {messages.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-orb"><CompanionMark /></div>
                    <h2>A fresh start</h2>
                    <p>What would you like to explore together?</p>
                  </div>
                ) : (
                  messages.map((message, index) => (
                    <div className={`message-row ${message.from}`} key={`${message.time}-${index}`}>
                      <div className="message-avatar">
                        {message.from === 'bot' ? <CompanionMark /> : (session?.user?.name?.slice(0, 1) ?? 'A')}
                      </div>
                      <div className="message-content">
                        <div className="message-bubble">{message.text}</div>
                        <span className="message-time">
                          {message.time}
                          {message.detected_emotion && message.detected_emotion !== 'neutral' && (
                            <span style={{ marginLeft: '8px', color: '#79918e', fontSize: '10px' }}>
                              • emotion: {message.detected_emotion}
                            </span>
                          )}
                        </span>
                      </div>
                    </div>
                  ))
                )}
                {thinking && (
                  <div className="message-row bot">
                    <div className="message-avatar"><CompanionMark /></div>
                    <div className="thinking"><i /><i /><i /></div>
                  </div>
                )}
              </div>

              {messages.length > 0 && (
                <div className="quick-prompts">
                  <span>Try asking</span>
                  {starters.slice(0, 3).map((item) => (
                    <button key={item.title} onClick={() => handleSendMessage(item.text)}>
                      {item.icon} {item.title}
                    </button>
                  ))}
                </div>
              )}

              {messages.length === 0 && (
                <div className="starter-grid">
                  {starters.map((item) => (
                    <button
                      key={item.title}
                      className="starter-card"
                      onClick={() => handleSendMessage(item.text)}
                    >
                      <b>{item.icon}</b>
                      <span>{item.title}</span>
                      <small>{item.text}</small>
                      <ArrowUp />
                    </button>
                  ))}
                </div>
              )}

              <div
                ref={messagesEndRef}
                style={{ height: '1px', scrollMarginBottom: '210px' }}
                aria-hidden="true"
              />

              <div className="composer-wrap">
                <div className="composer">
                  <button className="composer-icon" aria-label="Attach file">
                    <Paperclip />
                  </button>
                  <input
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.preventDefault()
                        handleSendMessage()
                      }
                    }}
                    placeholder="Share how you're feeling right now..."
                    aria-label="Message BhaavaBot"
                  />
                  <button
                    className={`mic-button ${listening ? 'listening' : ''}`}
                    onClick={() => {
                      if (listening) {
                        setListening(false)
                      } else {
                        setListening(true)
                        showToast('Voice session active')
                      }
                    }}
                    aria-label="Voice input"
                  >
                    <Mic />
                  </button>
                  <button
                    className="send-button"
                    onClick={() => handleSendMessage()}
                    aria-label="Send message"
                  >
                    <Send />
                  </button>
                </div>
                <p className="composer-note">
                  <ShieldCheck /> Your conversations are private and protected with clinical safety safeguards
                </p>
              </div>
            </div>
          ) : view === 'new' ? (
            <NewConversationView
              onPrompt={(prompt) => {
                startNewConversation(prompt)
              }}
            />
          ) : view === 'resources' ? (
            <ResourcesView
              filter={mediaFilter}
              setFilter={setMediaFilter}
              activeMedia={activeMedia}
              setActiveMedia={setActiveMedia}
              favorites={favorites}
              onToggleFavorite={handleToggleFavorite}
              showToast={showToast}
            />
          ) : view === 'reflections' ? (
            <ReflectionsView
              reflections={reflections}
              onAddReflection={handleAddReflection}
            />
          ) : (
            <ProfileView
              onSettings={() => setPanel('settings')}
              onSafety={() => setPanel('safety')}
              onOpenAssessment={() => setPanel('assessment')}
              profile={empathyProfile}
            />
          )}
        </div>
      </section>

      <nav className="bottom-nav" aria-label="Primary navigation">
        <button
          className={`bottom-nav-item ${view === 'home' ? 'active' : ''}`}
          onClick={() => setView('home')}
        >
          <Home /><span>Home</span>
        </button>
        <button
          className={`bottom-nav-item ${view === 'chat' ? 'active' : ''}`}
          onClick={() => setView('chat')}
        >
          <MessageSquare /><span>Chat</span>
        </button>
        <button
          className="bottom-nav-new"
          onClick={() => startNewConversation()}
          aria-label="New conversation"
        >
          <Plus /><span>New</span>
        </button>
        <button
          className={`bottom-nav-item ${view === 'reflections' ? 'active' : ''}`}
          onClick={() => setView('reflections')}
        >
          <Heart /><span>Reflections</span>
        </button>
        <button
          className={`bottom-nav-item ${view === 'resources' ? 'active' : ''}`}
          onClick={() => setView('resources')}
        >
          <BookOpen /><span>Resources</span>
        </button>
      </nav>

      <div className={`scrim ${sidebarOpen ? 'visible' : ''}`} onClick={() => setSidebarOpen(false)} />

      {listening && (
        <div className="voice-toast">
          <div className="voice-pulse"><Mic /></div>
          <div>
            <strong>Listening...</strong>
            <span>Tell me what’s on your mind</span>
          </div>
          <button onClick={() => setListening(false)} aria-label="Stop listening">
            <Square />
          </button>
        </div>
      )}

      {toastMessage && (
        <div
          style={{
            position: 'fixed',
            bottom: '80px',
            left: '50%',
            transform: 'translateX(-50%)',
            background: '#2d5957',
            color: '#fff',
            padding: '10px 18px',
            borderRadius: '20px',
            fontSize: '12px',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            boxShadow: '0 4px 14px rgba(0,0,0,0.15)',
          }}
        >
          <Check style={{ width: '14px', height: '14px' }} />
          <span>{toastMessage}</span>
        </div>
      )}

      {panel === 'assessment' && (
        <EmpathyAssessmentModal
          onClose={() => setPanel(null)}
          onCompleted={(prof) => {
            setEmpathyProfile(prof)
            showToast(`Companion personalized to ${prof.communication_style} style!`)
          }}
          userId={session?.user?.id || 'guest'}
        />
      )}

      {panel && panel !== 'assessment' && (
        <div className="panel-backdrop" style={{ zIndex: 100 }} onClick={() => setPanel(null)}>
          <section className="info-panel" onClick={(event) => event.stopPropagation()}>
            <button className="close-panel" onClick={() => setPanel(null)} aria-label="Close">
              <X />
            </button>
            {panel === 'settings' ? (
              <>
                <Settings className="panel-icon" />
                <h2>Your settings</h2>
                <p>Choose the way BhaavaBot shows up for you. Your preferences are saved on this device.</p>
                <label className="setting-row">
                  <span>Gentle reminders</span>
                  <input type="checkbox" defaultChecked />
                </label>
                <label className="setting-row">
                  <span>Sound effects</span>
                  <input type="checkbox" />
                </label>
              </>
            ) : (
              <>
                <ShieldCheck className="panel-icon" />
                <h2>A safe space</h2>
                <p>
                  BhaavaBot is an emotional support companion, not a doctor, licensed therapist, or emergency service. It never diagnoses mental health conditions.
                </p>

                {/* Trusted Emergency Contact Card */}
                <div style={{ marginTop: '16px', padding: '14px', borderRadius: '14px', background: '#f0f7f4', border: '1px solid #d4e7de' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <strong style={{ color: '#27584d', fontSize: '12.5px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Heart style={{ width: 14, height: 14, color: '#2b5647' }} />
                      Trusted Safety Contact
                    </strong>
                    <button
                      type="button"
                      onClick={() => {
                        setPanel(null)
                        setEditingContact(true)
                      }}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#2b5647',
                        fontSize: '12px',
                        fontWeight: 650,
                        cursor: 'pointer',
                        textDecoration: 'underline',
                      }}
                    >
                      Update
                    </button>
                  </div>
                  {emergencyContact ? (
                    <div style={{ fontSize: '12px', color: '#44665f', lineHeight: 1.6 }}>
                      <div><strong>Name:</strong> {emergencyContact.name} ({emergencyContact.relationship || 'Loved one'})</div>
                      {emergencyContact.phone && <div><strong>Phone:</strong> {emergencyContact.phone}</div>}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
                        <strong>Telegram Alert:</strong>
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 650,
                            padding: '2px 8px',
                            borderRadius: '999px',
                            backgroundColor:
                              emergencyContact.telegram_status === 'CONNECTED'
                                ? '#d4edda'
                                : emergencyContact.telegram_status === 'PENDING'
                                ? '#fff3cd'
                                : '#e9ecef',
                            color:
                              emergencyContact.telegram_status === 'CONNECTED'
                                ? '#155724'
                                : emergencyContact.telegram_status === 'PENDING'
                                ? '#856404'
                                : '#6c757d',
                          }}
                        >
                          {emergencyContact.telegram_status === 'CONNECTED'
                            ? `✓ Connected (${emergencyContact.telegram_username ? '@' + emergencyContact.telegram_username : 'Active'})`
                            : emergencyContact.telegram_status === 'PENDING'
                            ? 'Pairing Pending'
                            : 'Not Paired'}
                        </span>
                      </div>
                      {emergencyContact.telegram_status === 'CONNECTED' && emergencyContact.telegram_username && (
                        <div style={{ fontSize: '11px', color: '#55766e', marginTop: '2px' }}>
                          Alerts will be sent to Telegram account: <strong>@{emergencyContact.telegram_username}</strong>. If this is your own account, click Update above to connect your relative's phone.
                        </div>
                      )}
                      <div style={{ fontSize: '11px', color: '#6d8985', marginTop: '6px' }}>
                        ✓ Real-time crisis alerts are dispatched via our Telegram bot if acute distress or suicidal thoughts are detected.
                      </div>
                    </div>
                  ) : (
                    <div style={{ fontSize: '12px', color: '#a84d5b' }}>
                      No contact registered.{' '}
                      <button
                        type="button"
                        onClick={() => {
                          setPanel(null)
                          setEditingContact(true)
                        }}
                        style={{ color: '#2b5647', fontWeight: 650, textDecoration: 'underline', background: 'none', border: 'none', cursor: 'pointer' }}
                      >
                        Add contact
                      </button>
                    </div>
                  )}
                </div>

                <div style={{ marginTop: '14px', padding: '14px', borderRadius: '14px', background: '#fdf3f4', border: '1px solid #f9d6d9' }}>
                  <strong style={{ color: '#a75d68', fontSize: '12px', display: 'block', marginBottom: '6px' }}>
                    Immediate Crisis & Human Support:
                  </strong>
                  <p style={{ fontSize: '11px', color: '#555', lineHeight: 1.6, margin: 0 }}>
                    • <strong>988 Suicide & Crisis Lifeline:</strong> Call or text <strong>988</strong> (24/7, free, confidential)<br />
                    • <strong>Crisis Text Line:</strong> Text <strong>HOME</strong> to <strong>741741</strong><br />
                    • <strong>Global Directory:</strong> Visit <a href="https://findahelpline.com" target="_blank" rel="noreferrer" style={{ color: '#338f8c', textDecoration: 'underline' }}>findahelpline.com</a>
                  </p>
                </div>
                <button className="panel-action" style={{ marginTop: '18px' }} onClick={() => setPanel(null)}>
                  I understand
                </button>
              </>
            )}
          </section>
        </div>
      )}

      {editingContact && (
        <EmergencyContactModal
          userId={session?.user?.id || 'guest'}
          userName={session?.user?.name || 'Mitwa Ninama'}
          initialContact={emergencyContact}
          isMandatory={false}
          onCancel={() => setEditingContact(false)}
          onSaved={(contact) => {
            setEmergencyContact(contact)
            setEditingContact(false)
            showToast(`Emergency contact updated to ${contact.name}`)
          }}
        />
      )}
    </main>
  )
}
