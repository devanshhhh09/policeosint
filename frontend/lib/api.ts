import axios from 'axios'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${BASE}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    try {
      const raw   = localStorage.getItem('policeosint-auth')
      const token = raw ? JSON.parse(raw)?.state?.token : null
      if (token) config.headers.Authorization = `Bearer ${token}`
    } catch {}
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('policeosint-auth')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const authAPI = {
  login:  (badge_number: string, password: string) =>
            api.post('/auth/login', { badge_number, password }),
  me:     () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
}

export const casesAPI = {
  list:    (params?: any) => api.get('/cases/', { params }),
  get:     (id: string)   => api.get(`/cases/${id}`),
  create:  (data: any)    => api.post('/cases/', data),
  update:  (id: string, data: any) => api.patch(`/cases/${id}`, data),
  delete:  (id: string)   => api.delete(`/cases/${id}`),
  addNote: (id: string, content: string, note_type = 'general') =>
             api.post(`/cases/${id}/notes`, { content, note_type }),
  getNotes:(id: string)   => api.get(`/cases/${id}/notes`),
}

export const dashboardAPI = {
  stats: () => api.get('/dashboard/stats'),
}

export const investigateAPI = {
  start: (data: any)    => api.post('/investigations/', data),
  get:   (id: string)   => api.get(`/investigations/${id}`),
  list:  (params?: any) => api.get('/investigations/', { params }),
}

export const auditAPI = {
  list: (params?: any) => api.get('/audit/', { params }),
}
