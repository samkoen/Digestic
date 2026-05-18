import React, { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import Login from './pages/Login/Login'
import Dashboard from './pages/Dashboard/Dashboard'
import Pharmacies from './pages/Pharmacies/Pharmacies'
import PharmacyAdvancedFiltersPage from './pages/Pharmacies/PharmacyAdvancedFiltersPage'
import PharmacyDetail from './pages/Pharmacies/PharmacyDetail'
import Planning from './pages/Planning/Planning'
import PlanningLayout from './pages/Planning/PlanningLayout'
import PlanningEvaluation from './pages/Planning/PlanningEvaluation'
import PlanningSettings from './pages/Planning/PlanningSettings'
import Invoices from './pages/Invoices/Invoices'
import Users from './pages/Users/Users'
import DeliveryNotes from './pages/DeliveryNotes/DeliveryNotes'
import Depots from './pages/Depots/Depots'
import Products from './pages/Products/Products'
import EmailTemplates from './pages/EmailTemplates/EmailTemplates'
import { authService } from './services/authService'

function PrivateRoute({ children, adminOnly = false }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const storedUser = localStorage.getItem('user')
        if (storedUser) {
          const userData = JSON.parse(storedUser)
          setUser(userData)
          
          // Vérifier avec le serveur
          const response = await authService.getCurrentUser()
          setUser(response.user)
          localStorage.setItem('user', JSON.stringify(response.user))
        }
      } catch (error) {
        localStorage.removeItem('user')
        setUser(null)
      } finally {
        setLoading(false)
      }
    }
    checkAuth()
  }, [])

  if (loading) {
    return <div>Chargement...</div>
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (adminOnly && user.role !== 'admin') {
    return <Navigate to="/" replace />
  }

  return children
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <PrivateRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/pharmacies" element={<Pharmacies />} />
                <Route
                  path="/pharmacies/advanced-filters"
                  element={
                    <PrivateRoute adminOnly>
                      <PharmacyAdvancedFiltersPage />
                    </PrivateRoute>
                  }
                />
                <Route path="/pharmacies/:id" element={<PharmacyDetail />} />
                <Route path="/planning" element={<PlanningLayout />}>
                  <Route index element={<Planning />} />
                  <Route path="evaluation" element={<PlanningEvaluation />} />
                  <Route
                    path="parametres"
                    element={
                      <PrivateRoute adminOnly>
                        <PlanningSettings />
                      </PrivateRoute>
                    }
                  />
                </Route>
                <Route path="/invoices" element={<Invoices />} />
                <Route path="/delivery-notes" element={<DeliveryNotes />} />
                <Route
                  path="/depots"
                  element={
                    <PrivateRoute adminOnly>
                      <Depots />
                    </PrivateRoute>
                  }
                />
                <Route
                  path="/products"
                  element={
                    <PrivateRoute adminOnly>
                      <Products />
                    </PrivateRoute>
                  }
                />
                <Route
                  path="/users"
                  element={
                    <PrivateRoute adminOnly>
                      <Users />
                    </PrivateRoute>
                  }
                />
                <Route
                  path="/email-templates"
                  element={
                    <PrivateRoute adminOnly>
                      <EmailTemplates />
                    </PrivateRoute>
                  }
                />
              </Routes>
            </Layout>
          </PrivateRoute>
        }
      />
    </Routes>
  )
}

export default App

