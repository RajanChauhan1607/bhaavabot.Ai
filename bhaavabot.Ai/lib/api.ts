const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface ChatMessage {
  from: 'bot' | 'user'
  text: string
  time?: string
  detected_emotion?: string
  safety_level?: string
}

export interface ChatResponse {
  reply: string
  conversation_id: string
  time: string
  detected_emotion?: string
  emotion_confidence?: number
  emotion_intensity?: number
  safety_level?: string
  suggested_action?: string | null
  pacing?: string
  emergency_alert_dispatched?: boolean
  contact_notified?: string | null
}

export interface BookItem {
  id: string
  title: string
  author: string
  year?: string
  kind: string
  pages?: string
  icon: string
  tone: string
  description?: string
  source?: string
  license?: string
  url?: string | null
  tradition?: string | null
  category?: string | null
  language?: string | null
  cover_image_url?: string | null
  reading_url?: string | null
  source_name?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface MusicItem {
  id: string
  title: string
  artist: string
  kind: string
  icon: string
  tone: string
  category?: string | null
  source?: string
  license?: string
  attribution?: string
  url?: string | null
  audio_url?: string | null
  duration_seconds?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export interface ThemeItem {
  id: string
  title: string
  tagline: string
  description: string
  icon: string
  recommended_media_type?: string
}

export interface RecommendationResponse {
  theme?: string | null
  detected_emotion?: string | null
  emotion_intensity?: number | null
  books: BookItem[]
  music: MusicItem[]
  suggested_activity?: string | null
}

export interface EmpathyQuestion {
  id: number
  text: string
  dimension: string
  reverse_scored: boolean
}

export interface EmpathyAnswer {
  question_id: number
  score: number
}

export interface EmpathyProfile {
  user_id: string
  total_empathy_score: number
  emotional_empathy_score: number
  cognitive_empathy_score: number
  dispersion_score: number
  consistency_level: string
  profile_type: string
  emotional_style: string
  cognitive_style: string
  communication_style: string
  preferred_pacing: string
  updated_at: string
}

export interface ReflectionItem {
  id: string
  mood: string
  note: string
  created_at: string
}

export interface ConversationItem {
  id: string
  title: string
  user_id: string
  created_at: string
  updated_at: string
  preview?: string
}

export async function sendChatMessage(
  message: string,
  history: ChatMessage[] = [],
  conversationId = 'default',
  userId = 'guest',
  theme?: string,
  userName?: string
): Promise<ChatResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        history,
        conversation_id: conversationId,
        user_id: userId,
        user_name: userName || undefined,
        theme: theme || undefined,
      }),
    })
    if (!res.ok) {
      throw new Error(`API error: ${res.statusText}`)
    }
    return await res.json()
  } catch (err) {
    console.warn('FastAPI backend unreachable, using graceful fallback:', err)
    return {
      reply:
        'Thank you for sharing that with me. I am right here beside you. We can take this one small thought at a time. What feels heaviest right now?',
      conversation_id: conversationId,
      time: 'Just now',
      detected_emotion: 'neutral',
      safety_level: 'NORMAL',
      pacing: 'normal',
    }
  }
}

export async function fetchEmpathyQuestions(): Promise<EmpathyQuestion[]> {
  try {
    const res = await fetch(`${API_BASE}/api/empathy/questions`)
    if (!res.ok) throw new Error('Fetch questions failed')
    return await res.json()
  } catch (err) {
    console.warn('Using local question fallback:', err)
    return []
  }
}

export async function submitEmpathyAssessment(
  answers: EmpathyAnswer[],
  userId = 'guest'
): Promise<EmpathyProfile | null> {
  try {
    const res = await fetch(`${API_BASE}/api/empathy/assessment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, answers }),
    })
    if (!res.ok) throw new Error('Assessment submission failed')
    return await res.json()
  } catch (err) {
    console.error('Error submitting assessment:', err)
    return null
  }
}

export async function fetchEmpathyProfile(userId = 'guest'): Promise<EmpathyProfile | null> {
  try {
    const res = await fetch(`${API_BASE}/api/empathy/profile?user_id=${userId}`)
    if (!res.ok) throw new Error('Fetch profile failed')
    return await res.json()
  } catch (err) {
    console.warn('Could not fetch empathy profile:', err)
    return null
  }
}

export async function fetchThemes(): Promise<ThemeItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/content/themes`)
    if (!res.ok) throw new Error('Fetch themes failed')
    return await res.json()
  } catch (err) {
    return [
      { id: 'theme-listen', title: 'I just want someone to listen', tagline: 'A space to be heard', description: 'Share what is on your heart.', icon: '👂' },
      { id: 'theme-calm', title: 'Help me calm down', tagline: 'Grounding techniques', description: 'Slow pacing and soft breathing.', icon: '🌿' },
      { id: 'theme-distract', title: 'I want to take my mind off things', tagline: 'Gentle stories', description: 'Immerse in comforting worlds.', icon: '📖' },
      { id: 'theme-hope', title: 'I want to feel hopeful', tagline: 'Warmth and renewal', description: 'Gentle reminders of your strength.', icon: '☼' },
    ]
  }
}

export async function fetchRecommendations(
  emotion = 'neutral',
  intensity = 0.5,
  theme?: string,
  userId = 'guest'
): Promise<RecommendationResponse | null> {
  try {
    const params = new URLSearchParams({
      emotion,
      intensity: intensity.toString(),
      user_id: userId,
    })
    if (theme) params.append('theme', theme)
    const res = await fetch(`${API_BASE}/api/recommendations?${params.toString()}`)
    if (!res.ok) throw new Error('Fetch recommendations failed')
    return await res.json()
  } catch (err) {
    return null
  }
}

export async function recordCheckin(
  mood: string,
  note = '',
  userId = 'guest'
): Promise<ReflectionItem | null> {
  try {
    const res = await fetch(`${API_BASE}/api/checkin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mood, note, user_id: userId }),
    })
    if (!res.ok) throw new Error('Checkin failed')
    const data = await res.json()
    return data.entry
  } catch (err) {
    console.warn('Could not save checkin to backend:', err)
    return null
  }
}

export async function fetchReflections(userId = 'guest'): Promise<ReflectionItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/reflections?user_id=${userId}`)
    if (!res.ok) throw new Error('Fetch reflections failed')
    return await res.json()
  } catch (err) {
    console.warn('Using local reflections:', err)
    return []
  }
}

export async function fetchBooks(category = 'For you'): Promise<BookItem[]> {
  try {
    const url =
      category === 'For you'
        ? `${API_BASE}/api/resources/books`
        : `${API_BASE}/api/resources/books?category=${encodeURIComponent(category)}`
    const res = await fetch(url)
    if (!res.ok) throw new Error('Fetch books failed')
    return await res.json()
  } catch (err) {
    console.warn('Using default books fallback:', err)
    return [
      {
        id: 'book-bhagavad-gita',
        title: 'Bhagavad Gita',
        author: 'Vyasa (Translated by Sir Edwin Arnold)',
        year: 'c. 2nd Century BCE',
        kind: 'Philosophy · Spiritual Wisdom',
        tradition: 'Hinduism',
        category: 'Philosophy',
        pages: '18 Chapters · ~700 Verses',
        icon: 'sun',
        tone: 'peach',
        description: 'A profound dialogue between Prince Arjuna and Krishna addressing duty, devotion, selflessness, and inner peace on the battlefield of life.',
        language: 'English (Verse translation from Sanskrit)',
        cover_image_url: 'https://www.gutenberg.org/cache/epub/2388/pg2388.cover.medium.jpg',
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
        year: 'c. 5th Century BCE',
        kind: 'Epic · Dharma · Devotion',
        tradition: 'Hinduism',
        category: 'Epic',
        pages: '7 Kandas · ~24,000 Verses',
        icon: 'moon',
        tone: 'mint',
        description: 'The ancient Indian epic chronicling Rama\'s journey of righteousness, devotion, compassion, and courage amidst exile and adversity.',
        language: 'English (Verse translation from Sanskrit)',
        cover_image_url: 'https://www.gutenberg.org/cache/epub/24869/pg24869.cover.medium.jpg',
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
        year: 'c. 4th Century BCE',
        kind: 'Epic · Ethics · Wisdom',
        tradition: 'Hinduism',
        category: 'Epic',
        pages: '18 Parvas · Extensive Epic',
        icon: 'sun',
        tone: 'lavender',
        description: 'The monumental epic exploring human destiny, conflict resolution, dharma, statecraft, and the search for liberation and truth.',
        language: 'English (Prose translation from Sanskrit)',
        cover_image_url: 'https://www.gutenberg.org/cache/epub/15474/pg15474.cover.medium.jpg',
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
        year: '1611 AD',
        kind: 'Sacred Text · Faith · Compassion',
        tradition: 'Christianity',
        category: 'Sacred Text',
        pages: '66 Books · Old & New Testaments',
        icon: 'coffee',
        tone: 'peach',
        description: 'The sacred scriptures of Christianity, offering timeless teachings on faith, unconditional love, solace, and spiritual redemption.',
        language: 'English (King James Version)',
        cover_image_url: 'https://www.gutenberg.org/cache/epub/10/pg10.cover.medium.jpg',
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
        year: 'c. 610–632 AD',
        kind: 'Sacred Text · Mercy · Guidance',
        tradition: 'Islam',
        category: 'Sacred Text',
        pages: '114 Surahs',
        icon: 'rain',
        tone: 'mint',
        description: 'The central religious text of Islam, illuminating the path of patience, gratitude, moral integrity, divine mercy, and reflection.',
        language: 'English (Translation from Arabic)',
        cover_image_url: 'https://www.gutenberg.org/cache/epub/2800/pg2800.cover.medium.jpg',
        reading_url: 'https://www.gutenberg.org/ebooks/2800',
        url: 'https://www.gutenberg.org/ebooks/2800',
        source_name: 'Project Gutenberg',
        source: 'Project Gutenberg',
        license: 'Public Domain',
      },
    ]
  }
}

export async function fetchMusic(category = 'For you'): Promise<MusicItem[]> {
  try {
    const url =
      category === 'For you'
        ? `${API_BASE}/api/resources/music`
        : `${API_BASE}/api/resources/music?category=${encodeURIComponent(category)}`
    const res = await fetch(url)
    if (!res.ok) throw new Error('Fetch music failed')
    return await res.json()
  } catch (err) {
    return []
  }
}

export async function toggleFavorite(
  title: string,
  itemType: 'book' | 'music' = 'book',
  userId = 'guest'
): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/favorites/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, item_type: itemType, user_id: userId }),
    })
    if (!res.ok) throw new Error('Toggle favorite failed')
    const data = await res.json()
    return data.favorited
  } catch (err) {
    console.warn('Toggle favorite error:', err)
    return false
  }
}

export async function fetchFavorites(userId = 'guest'): Promise<string[]> {
  try {
    const res = await fetch(`${API_BASE}/api/favorites?user_id=${userId}`)
    if (!res.ok) throw new Error('Fetch favorites failed')
    const data = await res.json()
    return data.favorites || []
  } catch (err) {
    return []
  }
}

export async function fetchConversations(userId = 'guest'): Promise<ConversationItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/conversations?user_id=${encodeURIComponent(userId)}`)
    if (!res.ok) throw new Error('Fetch conversations failed')
    return await res.json()
  } catch (err) {
    console.warn('Using local fallback conversations:', err)
    return [
      {
        id: 'conv-welcome',
        title: 'A Quiet Beginning',
        user_id: userId,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: 'conv-peace',
        title: 'Unwinding After a Long Day',
        user_id: userId,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]
  }
}

export async function createConversation(
  title = 'A Quiet Conversation',
  userId = 'guest'
): Promise<ConversationItem | null> {
  try {
    const res = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, user_id: userId }),
    })
    if (!res.ok) throw new Error('Create conversation failed')
    return await res.json()
  } catch (err) {
    console.warn('Fallback creating conversation locally:', err)
    return {
      id: `conv-${Date.now()}`,
      title,
      user_id: userId,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
  }
}

export async function fetchConversationMessages(convId: string): Promise<ChatMessage[]> {
  try {
    const res = await fetch(`${API_BASE}/api/conversations/${encodeURIComponent(convId)}/messages`)
    if (!res.ok) throw new Error('Fetch messages failed')
    const data = await res.json()
    return data.map((m: any) => ({
      from: m.role === 'user' ? 'user' : 'bot',
      text: m.content || m.text || '',
      time: m.created_at
        ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : 'Earlier',
      detected_emotion: m.detected_emotion,
      safety_level: m.safety_level,
    }))
  } catch (err) {
    console.warn('Using empty messages fallback:', err)
    return []
  }
}

export async function deleteConversation(convId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/conversations/${encodeURIComponent(convId)}`, {
      method: 'DELETE',
    })
    if (!res.ok) throw new Error('Delete conversation failed')
    const data = await res.json()
    return data.deleted ?? true
  } catch (err) {
    console.warn('Delete conversation failed:', err)
    return true
  }
}

// --- Emergency Contact & Safety Onboarding ---

export interface EmergencyContact {
  user_id: string
  name: string
  phone: string
  relationship: string
  telegram_chat_id?: string | null
  telegram_username?: string | null
  telegram_status?: 'NOT_CONNECTED' | 'PENDING' | 'CONNECTED'
  pairing_code_expires_at?: string | null
  connected_at?: string | null
  consent_at?: string | null
  created_at?: string
  updated_at?: string
}

export interface PairingCodeResponse {
  success: boolean
  pairing_code: string
  bot_username: string
  pairing_link: string
  expires_in_seconds: number
  expires_at: string
  status: string
}

export interface TelegramBotInfo {
  status: string
  mode: string
  configured: boolean
  bot_username?: string | null
}

export async function fetchEmergencyContact(userId = 'guest'): Promise<EmergencyContact | null> {
  try {
    const res = await fetch(`${API_BASE}/api/user/emergency-contact?user_id=${encodeURIComponent(userId)}`)
    if (!res.ok) return null
    return await res.json()
  } catch (err) {
    console.warn('Could not fetch emergency contact:', err)
    return null
  }
}

export async function saveEmergencyContact(
  userId = 'guest',
  name: string,
  phone: string,
  relationship = 'Family / Friend'
): Promise<EmergencyContact | null> {
  try {
    const res = await fetch(`${API_BASE}/api/user/emergency-contact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, name, phone, relationship }),
    })
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}))
      throw new Error(errData.detail || 'Failed to save emergency contact')
    }
    return await res.json()
  } catch (err) {
    console.warn('Error saving emergency contact:', err)
    throw err
  }
}

export async function generatePairingCode(
  userId = 'guest',
  name = '',
  phone = '',
  relationship = 'Family / Friend',
  userName = 'Mitwa Ninama'
): Promise<PairingCodeResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/api/user/emergency-contact/pairing-code`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, name, phone, relationship, user_name: userName }),
    })
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}))
      throw new Error(errData.detail || 'Failed to generate Telegram pairing code')
    }
    return await res.json()
  } catch (err) {
    console.warn('Error generating Telegram pairing code:', err)
    throw err
  }
}

export async function disconnectEmergencyContact(userId = 'guest'): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/user/emergency-contact/disconnect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    })
    if (!res.ok) return false
    const data = await res.json()
    return data.success ?? false
  } catch (err) {
    console.warn('Error unlinking Telegram emergency contact:', err)
    return false
  }
}

export async function fetchTelegramBotInfo(): Promise<TelegramBotInfo | null> {
  try {
    const res = await fetch(`${API_BASE}/api/telegram/bot-info`)
    if (!res.ok) return null
    return await res.json()
  } catch (err) {
    console.warn('Could not fetch Telegram bot info:', err)
    return null
  }
}

export async function sendTestTelegramAlert(userId = 'guest'): Promise<{ success: boolean; message: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/safety/test-telegram`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, confirm: true }),
    })
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.detail || 'Test alert failed')
    }
    return { success: data.success, message: data.message }
  } catch (err: any) {
    return { success: false, message: err?.message || 'Failed to dispatch test alert' }
  }
}


