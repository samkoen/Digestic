import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  Container,
} from '@mui/material'
import { authService } from '../../services/authService'

function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const response = await authService.login(email, password)
      
      // Stocker les informations utilisateur dans le localStorage
      if (response.user) {
        localStorage.setItem('user', JSON.stringify(response.user))
        // Rediriger vers le dashboard
        navigate('/')
      } else {
        setError('Réponse invalide du serveur')
      }
    } catch (err) {
      console.error('Login error:', err)
      const errorMessage = err.response?.data?.error || err.message || 'Erreur de connexion'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
        }}
      >
        <Card sx={{ width: '100%', maxWidth: 400 }}>
          <CardContent>
            <Box
              display="flex"
              alignItems="baseline"
              justifyContent="center"
              gap={1}
              flexWrap="wrap"
              sx={{ mb: 1 }}
            >
              <Typography variant="h4" component="h1">
                Espaces Pharmacies
              </Typography>
              <Typography variant="subtitle1" component="span" color="text.secondary">
                Planning et suivi des visites pharmacies
              </Typography>
            </Box>
            <Typography variant="h6" component="h2" gutterBottom align="center" color="text.secondary">
              Connexion
            </Typography>

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <form onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                margin="normal"
                autoFocus
                autoComplete="username"
              />
              <TextField
                fullWidth
                label="Mot de passe"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                margin="normal"
                autoComplete="current-password"
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                disabled={loading}
              >
                {loading ? 'Connexion...' : 'Se connecter'}
              </Button>
            </form>

            <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 2 }}>
              Saisissez l’email et le mot de passe de votre compte.
            </Typography>
            <Typography variant="caption" color="text.secondary" align="center" sx={{ mt: 1, display: 'block' }}>
              Exemples: admin@digestic.fr, odelia@digestic.fr, camille@digestic.fr, aaron@digestic.fr
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Container>
  )
}

export default Login

