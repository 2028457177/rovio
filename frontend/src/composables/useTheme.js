import { ref, onMounted } from 'vue'

const THEME_KEY = 'lc-course-theme'
const theme = ref('light')

export function useTheme() {
  const apply = (value) => {
    theme.value = value
    document.documentElement.setAttribute('data-theme', value)
    localStorage.setItem(THEME_KEY, value)
  }

  const toggle = () => apply(theme.value === 'light' ? 'dark' : 'light')

  onMounted(() => {
    const stored = localStorage.getItem(THEME_KEY)
    if (stored === 'dark' || stored === 'light') {
      apply(stored)
      return
    }
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    apply(prefersDark ? 'dark' : 'light')
  })

  return { theme, toggle, apply }
}

export function initTheme() {
  const stored = localStorage.getItem(THEME_KEY)
  if (stored === 'dark' || stored === 'light') {
    document.documentElement.setAttribute('data-theme', stored)
    return
  }
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light')
}
