import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import AuthGate from './pages/AuthGate';
import Home from './pages/Home';
import Hazards from './pages/Hazards';
import Settings from './pages/Settings';
import LocationMap from './pages/LocationMap';
import TabBar from './components/TabBar';
import GuestBanner from './components/GuestBanner';
import { api, isBackendConfigured, session } from './lib/api';

/** FCM push registration calls into Firebase; without google-services.json the native app can crash. */
const ENABLE_NATIVE_PUSH = process.env.REACT_APP_ENABLE_PUSH === '1';

function useGate() {
  const [decided, setDecided] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [guest, setGuest] = useState(false);

  useEffect(() => {
    const acceptedGuest = localStorage.getItem('rrwm.guestAccepted') === '1';
    setAuthed(session.isAuthed());
    setGuest(acceptedGuest);
    setDecided(true);
  }, []);

  return { decided, authed, guest, setAuthed, setGuest };
}

export default function App() {
  const { decided, authed, guest, setAuthed, setGuest } = useGate();
  const location = useLocation();
  const hideTabs = location.pathname.startsWith('/auth') || location.pathname.startsWith('/locations/new');

  /** Best-effort: record latest device coordinates once per app session (MongoDB via FastAPI). */
  useEffect(() => {
    if (!decided || (!authed && !guest)) return;
    if (!isBackendConfigured() || typeof sessionStorage === 'undefined') return;
    if (sessionStorage.getItem('rrwm.deviceLocationAttempted')) return;
    sessionStorage.setItem('rrwm.deviceLocationAttempted', '1');
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          await api.reportDeviceLocation({
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy_m: Number.isFinite(pos.coords.accuracy) ? pos.coords.accuracy : undefined,
          });
        } catch {
          /* ignore */
        }
      },
      () => {},
      { enableHighAccuracy: false, timeout: 15000, maximumAge: 300000 }
    );
  }, [decided, authed, guest]);

  /** Native only: register FCM token (opt-in — set REACT_APP_ENABLE_PUSH=1 when Firebase is configured). */
  useEffect(() => {
    if (!ENABLE_NATIVE_PUSH) return;
    if (!decided || (!authed && !guest)) return;
    if (!isBackendConfigured()) return;
    let cancelled = false;
    (async () => {
      try {
        const { Capacitor } = await import('@capacitor/core');
        if (!Capacitor.isNativePlatform()) return;
        const { PushNotifications } = await import('@capacitor/push-notifications');
        const perm = await PushNotifications.requestPermissions();
        if (perm.receive !== 'granted') return;
        await PushNotifications.addListener('registration', async ({ value }) => {
          if (cancelled || !value) return;
          try {
            await api.registerPushToken({ token: value, platform: Capacitor.getPlatform() });
          } catch (e) {
            console.warn('registerPushToken', e);
          }
        });
        await PushNotifications.addListener('registrationError', (err) => {
          console.warn('push registrationError', err);
        });
        await PushNotifications.register();
      } catch (e) {
        console.warn('push setup', e);
      }
    })();
    return () => {
      cancelled = true;
      (async () => {
        try {
          const { Capacitor } = await import('@capacitor/core');
          if (!Capacitor.isNativePlatform()) return;
          const { PushNotifications } = await import('@capacitor/push-notifications');
          await PushNotifications.removeAllListeners();
        } catch {
          /* ignore */
        }
      })();
    };
  }, [decided, authed, guest]);

  if (!decided) return <div className="h-screen w-screen bg-app" />;
  if (!authed && !guest) {
    return (
      <Routes>
        <Route
          path="*"
          element={
            <AuthGate
              onSignedIn={() => setAuthed(true)}
              onContinueGuest={() => {
                localStorage.setItem('rrwm.guestAccepted', '1');
                setGuest(true);
              }}
            />
          }
        />
      </Routes>
    );
  }

  return (
    <div className="min-h-screen bg-app text-white pb-20">
      <GuestBanner />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/hazards" element={<Hazards />} />
        <Route path="/settings" element={<Settings onSignedOut={() => { setAuthed(false); setGuest(false); }} />} />
        <Route path="/locations/new" element={<LocationMap />} />
        <Route path="/auth" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      {!hideTabs && <TabBar />}
    </div>
  );
}
