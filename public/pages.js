'use strict';
// Loaded only by the GitHub Pages build. The Python app keeps its server API.
window.KAA_STATIC = (() => {
  const key = 'kaa-pages-v1:' + new URL('.', location.href).pathname;
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem(key)); } catch {}
  if (!saved?.profile || !saved?.state) saved = null;
  const fresh = () => ({
    profile: {name: 'Student', preferredName: 'Student', university: 'snu',
      language: 'en', koreanLevel: 'Beginner', demo: true, aiConsent: false},
    state: {}, aiConfigured: false, searchConfigured: false
  });
  function save(value) {
    try { localStorage.setItem(key, JSON.stringify(value)); }
    catch { throw Error('Your browser could not save this change. Free some site storage or allow browser storage and try again.'); }
    saved = value;
  }
  return {
    async request(path, data) {
      if (path === 'content') {
        const response = await fetch('content.json');
        if (!response.ok) throw Error('App content could not load. Please retry.');
        return response.json();
      }
      if (path === 'demo') { if (!saved) save(fresh()); return {ok: true}; }
      if (path === 'logout') return {ok: true};
      if (path === 'delete-account') { localStorage.removeItem(key); saved = null; return {ok: true}; }
      if (path === 'login' || path === 'register') throw Error('Accounts require a hosted server. Use Explore app on this site.');
      if (!saved) saved = fresh();
      if (path === 'state' && data === undefined) return structuredClone(saved);
      if (path === 'state') save({...saved, state: structuredClone(data)});
      else if (path === 'profile') save({...saved, profile: {...saved.profile, ...data}});
      else if (path === 'avatar') {
        save({...saved, profile: {...saved.profile, avatar: data.avatar || null}});
        return {url: data.avatar || null};
      }
      else if (path === 'chat') return {
        answer: 'Live AI is not connected on this site. You can explore Korean lessons, university links, and the planning tools. AI chat requires a hosted backend.',
        sources: [], mode: 'offline-guide'
      };
      else throw Error('This feature requires a hosted server.');
      return {ok: true};
    }
  };
})();
