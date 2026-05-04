import React, { useCallback, useMemo, useState } from 'react'
import { Alert, Snackbar } from '@mui/material'

/** Snackbar + Alert (même UX que la page BL : multiligne, durées par sévérité). */
export function useNotifier() {
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success',
  })

  const closeSnackbar = useCallback((_e, reason) => {
    if (reason === 'clickaway') {
      return
    }
    setSnackbar((s) => ({ ...s, open: false }))
  }, [])

  const notify = useCallback((message, severity = 'success') => {
    setSnackbar({ open: true, message, severity })
  }, [])

  const NotifierSnackbar = useMemo(
    () => (
      <Snackbar
        open={snackbar.open}
        autoHideDuration={snackbar.severity === 'error' ? 9000 : 6000}
        onClose={closeSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          elevation={6}
          onClose={closeSnackbar}
          severity={snackbar.severity}
          variant="filled"
          sx={{
            width: '100%',
            maxWidth: 560,
            whiteSpace: String(snackbar.message).includes('\n') ? 'pre-wrap' : 'normal',
          }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    ),
    [snackbar.open, snackbar.message, snackbar.severity, closeSnackbar],
  )

  return { notify, NotifierSnackbar }
}
