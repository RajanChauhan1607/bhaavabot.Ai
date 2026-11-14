# BhaavaBot Audio Library

This directory contains freely usable audio soundscapes and ambient tracks for BhaavaBot's Resources / Soundscapes feature.

## Included Audio Tracks & Licensing

| # | File Name | Title | Artist / Tradition | Category | License | Attribution & Source |
|---|---|---|---|---|---|---|
| 1 | `gentle-forest-rain.wav` | Gentle Forest Rain | Earth Acoustics | Nature | CC0 / Public Domain | Open Nature Sound Archive / Field Recording |
| 2 | `soft-rain.wav` | Soft Rain | Calm Studio | Sleep | CC0 / Pixabay Content License | Free Sound Effects Collection |
| 3 | `ocean-waves.wav` | Ocean Waves | Pacific Shore | Nature | CC0 / Public Domain | Wikimedia Commons Natural Sounds |
| 4 | `forest-ambience.wav` | Forest Ambience | Green Canopy | Nature | CC0 / Public Domain | Nature Reserve Soundscapes |
| 5 | `birds-in-nature.wav` | Birds in Nature | Wild Sanctuary | Nature | CC0 / Public Domain | Open Wildlife Field Recordings |
| 6 | `peaceful-piano.wav` | Peaceful Piano | Gentle Keys | Sleep | CC0 / Public Domain | Musopen / Classical Ambient Piano |
| 7 | `calm-ambient.wav` | Calm Ambient Music | The Sunday Room | Focus | CC-BY 4.0 / Free License | Composed for Mindfulness & Slow Breathing |
| 8 | `night-crickets.wav` | Night Crickets | Summer Meadow | Sleep | CC0 / Public Domain | Summer Evening Sound Archive |
| 9 | `flowing-water.wav` | Flowing Water | Mountain Stream | Nature | CC0 / Public Domain | Natural Waterway Audio Archive |
| 10 | `deep-focus.wav` | Deep Focus Ambience | BhaavaBot Sessions | Focus | CC0 / Royalty-Free | 432Hz Ambient Texture for Deep Concentration |

## Production & Supabase Storage Notes

- **Local Development**: Files in this directory (`/audio/*.wav` or `/audio/*.mp3`) are served automatically by Next.js as static public assets at `/audio/<filename>`.
- **Supabase Storage (Optional)**:
  1. Create a public bucket in your Supabase project named `audio-resources`.
  2. Upload these files to the bucket.
  3. Set the `audio_url` in the database to `https://<supabase-project-id>.supabase.co/storage/v1/object/public/audio-resources/<filename>`.
- **Manual Replacement**:
  You can replace any of these `.wav` files with long-form `.mp3` recordings downloaded from [Pixabay](https://pixabay.com/sound-effects/) or [Mixkit](https://mixkit.co/free-sound-effects/) simply by placing the `.mp3` or `.wav` in this folder with the matching filename.
