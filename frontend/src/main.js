import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router/index.js'
import { useAuthStore } from './stores/auth.js'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// Initialize auth from stored token before mounting
const authStore = useAuthStore()
authStore.init().then(() => {
  app.mount('#app')
})
