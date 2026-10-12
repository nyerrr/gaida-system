/**
 * offlineQueue.js
 * ─────────────────────────────────────────────────────────────
 * Durable outbox for messages a student writes while offline.
 *
 * A message composed with no connection is stored here (IndexedDB, so it
 * survives a reload or an app restart) and replayed in order to
 * `/virtual-agent/stream` the moment the browser fires the `online`
 * event. This is what lets the installed PWA keep its promise — "your
 * messages are saved and will send when you reconnect" — instead of
 * throwing a connection error at a student who is already having a hard
 * time.
 *
 * The store deliberately lives in the IndexedDB database
 * `gaida-offline-queue`, which `clearSensitiveLocalData()` (api.js)
 * deletes on logout and on session end. Queued text therefore never
 * outlives the login that created it on a shared device.
 *
 * There is NO transcript cache here. Only messages the student has not
 * yet had a chance to send are persisted; everything already delivered
 * stays server-side, exactly as before.
 *
 * A connection is opened per operation and closed immediately after, so
 * `indexedDB.deleteDatabase('gaida-offline-queue')` is never blocked by a
 * live handle. If IndexedDB is unavailable (private mode, hardened
 * policy) the queue degrades to an in-memory list for the life of the
 * tab rather than throwing.
 * ─────────────────────────────────────────────────────────────
 */

const DB_NAME = 'gaida-offline-queue';
const STORE = 'messages';
const DB_VERSION = 1;

// Used only when IndexedDB is unavailable. Cleared on reload.
let memory = [];
let memoryNextId = 1;

const listeners = new Set();

function idbAvailable() {
  try {
    return typeof indexedDB !== 'undefined' && indexedDB !== null;
  } catch {
    return false;
  }
}

function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: 'id', autoIncrement: true });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function requestToPromise(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function closeQuietly(db) {
  try { db?.close(); } catch { /* already closed */ }
}

function notify() {
  count()
    .then((n) => listeners.forEach((cb) => { try { cb(n); } catch { /* listener error */ } }))
    .catch(() => {});
}

function normalize(item) {
  return {
    text: String(item?.text ?? ''),
    session_id: item?.session_id ?? null,
    user_id: item?.user_id ?? null,
    intent: item?.intent ?? 'unknown',
    vent_mode: !!item?.vent_mode,
    queued_at: Date.now(),
  };
}

function memoryAdd(record) {
  const id = `mem-${memoryNextId++}`;
  memory.push({ ...record, id });
  notify();
  return id;
}

/**
 * Persist one message. Returns its queue id.
 */
export async function enqueue(item) {
  const record = normalize(item);
  if (!idbAvailable()) return memoryAdd(record);

  let db;
  try {
    db = await openDb();
    const id = await requestToPromise(
      db.transaction(STORE, 'readwrite').objectStore(STORE).add(record),
    );
    return id;
  } catch {
    return memoryAdd(record);
  } finally {
    closeQuietly(db);
  }
}

/**
 * All queued messages, oldest first (IndexedDB key order).
 */
export async function getAll() {
  if (!idbAvailable()) return [...memory];

  let db;
  try {
    db = await openDb();
    return await requestToPromise(
      db.transaction(STORE, 'readonly').objectStore(STORE).getAll(),
    );
  } catch {
    return [...memory];
  } finally {
    closeQuietly(db);
  }
}

/**
 * Remove one message after it has been delivered (or abandoned).
 */
export async function remove(id) {
  if (!idbAvailable()) {
    memory = memory.filter((r) => r.id !== id);
    notify();
    return;
  }

  let db;
  try {
    db = await openDb();
    await requestToPromise(
      db.transaction(STORE, 'readwrite').objectStore(STORE).delete(id),
    );
  } catch {
    /* nothing persisted to delete */
  } finally {
    closeQuietly(db);
    notify();
  }
}

/**
 * Number of messages still waiting to send.
 */
export async function count() {
  if (!idbAvailable()) return memory.length;

  let db;
  try {
    db = await openDb();
    return await requestToPromise(
      db.transaction(STORE, 'readonly').objectStore(STORE).count(),
    );
  } catch {
    return memory.length;
  } finally {
    closeQuietly(db);
  }
}

/**
 * Subscribe to queue-size changes. The callback is invoked immediately with
 * the current size, then again after every enqueue/remove. Returns an
 * unsubscribe function.
 */
export function subscribe(callback) {
  listeners.add(callback);
  count()
    .then((n) => { try { callback(n); } catch { /* listener error */ } })
    .catch(() => {});
  return () => listeners.delete(callback);
}
