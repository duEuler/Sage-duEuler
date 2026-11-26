import { initializeApp } from 'https://www.gstatic.com/firebasejs/13.4.0/firebase-app.js';
import { getAuth, signInAnonymously } from 'https://www.gstatic.com/firebasejs/13.4.0/firebase-auth.js';
import { deleteDoc, doc, getFirestore, setDoc } from 'https://www.gstatic.com/firebasejs/13.4.0/firebase-firestore-lite.js';
import { deleteToken, getMessaging, getToken, isSupported } from 'https://www.gstatic.com/firebasejs/13.4.0/firebase-messaging.js';
import { firebaseConfig, vapidKey } from './push-config.js';

const app = initializeApp(firebaseConfig, 'sage-familia-push');
const auth = getAuth(app);
const db = getFirestore(app);

export async function subscribe() {
  if (!await isSupported()) throw new Error('PUSH_UNSUPPORTED');
  const serviceWorkerRegistration = await navigator.serviceWorker.ready;
  const messaging = getMessaging(app);
  const token = await getToken(messaging, { vapidKey, serviceWorkerRegistration });
  await auth.authStateReady();
  const user = auth.currentUser || (await signInAnonymously(auth)).user;
  try {
    await setDoc(doc(db, 'sagePushSubscriptions', user.uid), { token });
  } catch (error) {
    await deleteToken(messaging).catch(() => {});
    throw error;
  }
}

export async function unsubscribe() {
  await auth.authStateReady();
  if (auth.currentUser) await deleteDoc(doc(db, 'sagePushSubscriptions', auth.currentUser.uid));
  if (await isSupported()) await deleteToken(getMessaging(app)).catch(() => {});
}
