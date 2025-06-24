import { createRouter, createWebHistory } from 'vue-router'
import DanmuQuery from '../views/DanmuQuery.vue'

const routes = [
  {
    path: '/',
    name: 'DanmuQuery',
    component: DanmuQuery,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router