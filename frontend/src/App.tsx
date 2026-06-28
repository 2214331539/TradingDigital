import { RouterProvider } from 'react-router-dom'
import { AuthProvider } from './app/providers/AuthProvider'
import { router } from './app/router'
import './App.css'

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  )
}
