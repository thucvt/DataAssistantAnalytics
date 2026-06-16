<script setup>
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <span class="logo">DA</span>
        <span>Data <b>Assistant</b></span>
      </div>
      <nav>
        <router-link to="/">Dashboard</router-link>
        <a class="soon">AI Settings <small>(Phase 2)</small></a>
        <a class="soon">Chi phí AI <small>(Phase 2)</small></a>
        <a class="soon">Data Sources <small>(Phase 3)</small></a>
      </nav>
    </aside>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.layout { display: flex; min-height: 100vh; }
.sidebar {
  width: 240px; background: var(--bg-card);
  border-right: 1px solid var(--border); padding: 24px 16px;
}
.brand { display: flex; align-items: center; gap: 10px; font-size: 16px; margin-bottom: 32px; }
.brand .logo {
  width: 34px; height: 34px; border-radius: 9px;
  background: linear-gradient(145deg, var(--gold-soft), var(--gold));
  color: #1a1a1a; font-weight: 800; display: grid; place-items: center;
}
nav { display: flex; flex-direction: column; gap: 4px; }
nav a {
  padding: 10px 12px; border-radius: 8px; color: var(--text-dim);
  text-decoration: none; font-size: 14px;
}
nav a.router-link-active { background: rgba(212,175,55,0.1); color: var(--gold-soft); }
nav a.soon { opacity: .5; cursor: default; }
nav a.soon small { font-size: 10px; }
.content { flex: 1; padding: 32px 40px; }
</style>
