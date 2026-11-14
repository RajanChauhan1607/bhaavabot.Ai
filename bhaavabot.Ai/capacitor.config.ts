import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.bhaavabot.app',
  appName: 'BhaavaBot',
  webDir: 'out',
  server: {
    // Production Cloud URL - No computer or local server needed!
    url: 'https://bhaavabot-ai-nx5t.vercel.app',
    androidScheme: 'https',
    cleartext: false
  },
  android: {
    allowMixedContent: false
  }
};

export default config;
