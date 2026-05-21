<template>
  <div id="app-layout">
    <nav class="nav-bar">
      <router-link to="/movies" class="nav-brand">
        <div class="brand-mark">T</div>
        <span>豆瓣 Top 250</span>
      </router-link>
      <div class="nav-links">
        <router-link to="/movies">电影列表</router-link>
        <router-link to="/versions">版本对比</router-link>
        <router-link to="/settings">设置</router-link>
      </div>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Noto+Sans+SC:wght@300;400;500;600&display=swap');

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', 'Noto Sans SC', system-ui, -apple-system, sans-serif;
  background: #fafafa;
  color: #27272a;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.nav-bar {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(228, 228, 231, 0.6);
  padding: 0 24px;
  display: flex;
  align-items: center;
  height: 48px;
  position: sticky;
  top: 0;
  z-index: 100;
  gap: 8px;
  flex-wrap: nowrap;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #18181b;
  text-decoration: none;
  letter-spacing: -0.3px;
  flex-shrink: 0;
}

.brand-mark {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  background: #18181b;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: -0.5px;
  flex-shrink: 0;
}

.nav-links {
  display: flex;
  gap: 2px;
}

.nav-links a {
  text-decoration: none;
  color: #a1a1aa;
  font-size: 13px;
  font-weight: 500;
  padding: 5px 10px;
  border-radius: 6px;
  transition: all 0.15s;
  white-space: nowrap;
}

.nav-links a:hover {
  color: #3f3f46;
  background: rgba(244, 244, 245, 0.8);
}

.nav-links a.router-link-active {
  color: #6366f1;
  background: #eef2ff;
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 28px 24px;
}

@media (max-width: 640px) {
  .nav-bar {
    padding: 0 16px;
    height: 44px;
  }
  .nav-brand span {
    display: none;
  }
  .nav-links {
    gap: 0;
  }
  .nav-links a {
    font-size: 12px;
    padding: 5px 8px;
  }
  .main-content {
    padding: 20px 16px;
  }
}
</style>
