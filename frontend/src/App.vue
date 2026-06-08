<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth.js'

const router = useRouter()
const authStore = useAuthStore()

function onLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div id="app-layout">
    <nav class="nav-bar">
      <router-link to="/movies" class="nav-brand">
        <div class="brand-mark">T</div>
        <span>Top250 Tracker</span>
      </router-link>
      <div class="nav-links">
        <router-link to="/explore">探索</router-link>
        <router-link to="/movies">版本列表</router-link>
        <router-link to="/compare">版本对比</router-link>
        <router-link v-if="authStore.isLoggedIn" to="/settings">控制台</router-link>
      </div>
      <div class="nav-right">
        <template v-if="authStore.isLoggedIn">
          <span class="nav-user">{{ authStore.user.username }}</span>
          <button class="nav-logout" @click="onLogout">退出</button>
        </template>
        <router-link v-else to="/login" class="nav-login">登录</router-link>
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

:root {
  --bg: #fafafa;
  --card-bg: #ffffff;
  --border: rgba(228, 228, 231, 0.6);
  --text: #27272a;
  --accent: #6366f1;
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

.nav-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.nav-user {
  font-size: 13px;
  font-weight: 500;
  color: #3f3f46;
}

.nav-logout {
  background: none;
  border: 1px solid #e4e4e7;
  color: #71717a;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s;
}

.nav-logout:hover {
  background: #f4f4f5;
  color: #3f3f46;
}

.nav-login {
  text-decoration: none;
  color: #6366f1;
  font-size: 13px;
  font-weight: 500;
  padding: 4px 12px;
  border: 1px solid #6366f1;
  border-radius: 6px;
  transition: all 0.15s;
}

.nav-login:hover {
  background: #6366f1;
  color: #fff;
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
