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
  alpha,
  useTheme,
  CircularProgress,
} from '@mui/material'
import LocalPharmacyIcon from '@mui/icons-material/LocalPharmacy'
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth'
import AssessmentIcon from '@mui/icons-material/Assessment'
import { authService } from '../../services/authService'

const features = [
  { icon: CalendarMonthIcon, text: 'Planning des tournées et visites' },
  { icon: LocalPharmacyIcon, text: 'Gestion du réseau pharmacies' },
  { icon: AssessmentIcon, text: 'Suivi terrain et facturation' },
]

function Login() {
  const theme = useTheme()
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

      if (response.user) {
        localStorage.setItem('user', JSON.stringify(response.user))
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
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        bgcolor: 'background.default',
      }}
    >
      <Box
        sx={{
          display: { xs: 'none', md: 'flex' },
          flex: 1,
          flexDirection: 'column',
          justifyContent: 'center',
          px: 6,
          py: 4,
          background: `linear-gradient(145deg, ${theme.palette.primary.dark} 0%, ${theme.palette.primary.main} 55%, ${theme.palette.primary.light} 100%)`,
          color: 'primary.contrastText',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <Box
          sx={{
            position: 'absolute',
            width: 400,
            height: 400,
            borderRadius: '50%',
            bgcolor: alpha('#fff', 0.06),
            top: -120,
            right: -80,
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            width: 280,
            height: 280,
            borderRadius: '50%',
            bgcolor: alpha('#fff', 0.04),
            bottom: -60,
            left: -40,
          }}
        />
        <Box sx={{ position: 'relative', zIndex: 1, maxWidth: 420 }}>
          <Typography variant="overline" sx={{ opacity: 0.85, letterSpacing: 2 }}>
            Digestic
          </Typography>
          <Typography variant="h3" fontWeight={700} sx={{ mt: 1, mb: 1.5, letterSpacing: '-0.02em' }}>
            Espaces Pharmacies
          </Typography>
          <Typography variant="body1" sx={{ opacity: 0.92, mb: 4, lineHeight: 1.7 }}>
            Planning et suivi des visites pharmacies — une plateforme pensée pour vos équipes terrain.
          </Typography>
          <Box component="ul" sx={{ listStyle: 'none', p: 0, m: 0 }}>
            {features.map(({ icon: Icon, text }) => (
              <Box
                component="li"
                key={text}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 2,
                  mb: 2,
                }}
              >
                <Box
                  sx={{
                    width: 44,
                    height: 44,
                    borderRadius: 2,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    bgcolor: alpha('#fff', 0.15),
                  }}
                >
                  <Icon />
                </Box>
                <Typography variant="body1" fontWeight={500}>
                  {text}
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>
      </Box>

      <Box
        sx={{
          flex: { xs: 1, md: '0 0 480px' },
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          p: { xs: 2, sm: 4 },
        }}
      >
        <Card
          elevation={0}
          sx={{
            width: '100%',
            maxWidth: 400,
            border: `1px solid ${theme.palette.divider}`,
            boxShadow: '0 12px 40px rgba(26, 35, 50, 0.1)',
          }}
        >
          <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
            <Box sx={{ display: { md: 'none' }, mb: 3, textAlign: 'center' }}>
              <Box
                sx={{
                  width: 48,
                  height: 48,
                  borderRadius: 2,
                  mx: 'auto',
                  mb: 1.5,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  bgcolor: 'primary.main',
                  color: 'primary.contrastText',
                }}
              >
                <LocalPharmacyIcon />
              </Box>
              <Typography variant="h5" fontWeight={700}>
                Espaces Pharmacies
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Digestic
              </Typography>
            </Box>

            <Typography variant="h5" fontWeight={700} gutterBottom sx={{ display: { xs: 'none', md: 'block' } }}>
              Connexion
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3, display: { xs: 'none', md: 'block' } }}>
              Accédez à votre espace commercial ou administrateur.
            </Typography>
            <Typography
              variant="h6"
              align="center"
              color="text.secondary"
              sx={{ mb: 2, display: { xs: 'block', md: 'none' } }}
            >
              Connexion
            </Typography>

            {error && (
              <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>
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
                size="large"
                disabled={loading}
                sx={{ mt: 3, py: 1.4 }}
              >
                {loading ? (
                  <CircularProgress size={24} color="inherit" />
                ) : (
                  'Se connecter'
                )}
              </Button>
            </form>

            <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 3 }}>
              Utilisez les identifiants fournis par votre administrateur.
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Box>
  )
}

export default Login
