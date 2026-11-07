import { useSyncExternalStore } from 'react'

function subscribeOnline(callback) {
  window.addEventListener('online', callback)
  window.addEventListener('offline', callback)
  return () => {
    window.removeEventListener('online', callback)
    window.removeEventListener('offline', callback)
  }
}

const getOnlineSnapshot = () => navigator.onLine

export default function useOnline() {
  return useSyncExternalStore(subscribeOnline, getOnlineSnapshot)
}
