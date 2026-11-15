import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.bhaavabot.app',
  appName: 'BhaavaBot',
  webDir: 'out',
  server: {
    // Production Cloud URL
    url: 'https://bhaavabot.vercel.app',
    androidScheme: 'https',
    cleartext: false,
    allowNavigation: [
      'bhaavabot.vercel.app',
      'accounts.google.com',
      '*.google.com',
      '*.googleusercontent.com'
    ]
  },
  android: {
    allowMixedContent: false
  }
};

export default config;
