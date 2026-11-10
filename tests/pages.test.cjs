const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

function browser(storage = new Map()) {
  const context = vm.createContext({window: {}, location: {href: 'https://example.test/KAA/'},
    URL, structuredClone, localStorage: {
      getItem: key => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: key => storage.delete(key)
    }});
  vm.runInContext(fs.readFileSync('public/pages.js', 'utf8'), context);
  return context.window.KAA_STATIC.request;
}

test('Pages profile and lesson progress survive a reload and can be cleared', async () => {
  const storage = new Map();
  const api = browser(storage);
  assert.equal((await api('state')).profile.name, 'Student');
  await api('profile', {name: 'Test Student', language: 'ko'});
  await api('state', {progress: {'1': {score: 100}}, checklist: {'arc:0': true}});
  const reload = browser(storage);
  assert.equal((await reload('state')).profile.language, 'ko');
  assert.equal((await reload('state')).state.progress['1'].score, 100);
  await reload('delete-account', {});
  assert.equal((await browser(storage)('state')).profile.name, 'Student');
  assert.equal(storage.size, 0);
});

test('Pages never pretends to authenticate or generate an AI response', async () => {
  const api = browser();
  await assert.rejects(api('login', {}), /hosted server/);
  await assert.rejects(api('register', {}), /hosted server/);
  assert.equal((await api('state')).aiConfigured, false);
  assert.equal((await api('chat', {question: 'Hi'})).mode, 'offline-guide');
});

test('Corrupt browser storage recovers without preventing startup', async () => {
  const api = browser(new Map([['kaa-pages-v1:/KAA/', '{broken']]));
  assert.equal((await api('state')).profile.name, 'Student');
});
