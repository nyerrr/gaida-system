import { beforeEach, describe, expect, it } from 'vitest';
import { count, enqueue, getAll, remove } from './offlineQueue';

const deleteDatabase = () => new Promise((resolve, reject) => {
  const request = indexedDB.deleteDatabase('gaida-offline-queue');
  request.onsuccess = () => resolve();
  request.onerror = () => reject(request.error);
  request.onblocked = () => resolve();
});

beforeEach(async () => {
  await deleteDatabase();
});

describe('offline message queue', () => {
  it('persists queued messages in insertion order and removes delivered entries', async () => {
    const first = await enqueue({ text: 'first', session_id: 'session-1', user_id: 'student-1' });
    const second = await enqueue({ text: 'second', session_id: 'session-1', user_id: 'student-1' });

    expect(await count()).toBe(2);
    expect((await getAll()).map((item) => item.text)).toEqual(['first', 'second']);

    await remove(first);

    expect(await count()).toBe(1);
    expect((await getAll()).map((item) => item.id)).toEqual([second]);
  });
});
