import React from 'react'
import { Box, CircularProgress, Typography } from '@mui/material'
import LocalPharmacyIcon from '@mui/icons-material/LocalPharmacy'

function AppLoadingScreen({ message = 'Chargement…' }) {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
        bgcolor: 'background.default',
      }}
    >
      <Box
        sx={{
          width: 56,
          height: 56,
          borderRadius: 3,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: 'primary.main',
          color: 'primary.contrastText',
          boxShadow: 4,
        }}
      >
        <LocalPharmacyIcon fontSize="large" />
      </Box>
      <CircularProgress size={32} thickness={4} />
      <Typography variant="body2" color="text.secondary">
        {message}
      </Typography>
    </Box>
  )
}

export default AppLoadingScreen
