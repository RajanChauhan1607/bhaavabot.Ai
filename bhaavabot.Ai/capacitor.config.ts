import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.bhaavabot.app',
  appName: 'BhaavaBot',
  webDir: 'out',
  server: {
    // Connects the Android app to your live Next.js dev server:
    url: 'http://10.200.10.110:3000',
    androidScheme: 'https',
    cleartext: true
  },
  android: {
    allowMixedContent: true
  }
};

export default config;
