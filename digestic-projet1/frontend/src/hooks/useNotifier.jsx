import React, { useCallback, useMemo, useState } from 'react'
import { Alert, Snackbar } from '@mui/material'

/** Snackbar + Alert (même UX que la page BL : multiligne, durées par sévérité). */
export function useNotifier() {
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success',
    action: null,
  })

  const closeSnackbar = useCallback((_e, reason) => {
    if (reason === 'clickaway') {
      return
    }
    setSnackbar((s) => ({ ...s, open: false, action: null }))
  }, [])

  const notify = useCallback((message, severity = 'success', options = {}) => {
    setSnackbar({
      open: true,
      message,
      severity,
      action: options.action ?? null,
    })
  }, [])

  const NotifierSnackbar = useMemo(
    () => (
      <Snackbar
        open={snackbar.open}
        autoHideDuration={
          snackbar.action ? null : snackbar.severity === 'error' ? 9000 : 6000
        }
        onClose={closeSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          elevation={6}
          onClose={closeSnackbar}
          severity={snackbar.severity}
          variant="filled"
          action={snackbar.action ?? undefined}
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
    [
      snackbar.open,
      snackbar.message,
      snackbar.severity,
      snackbar.action,
      closeSnackbar,
    ],
  )

  return { notify, dismiss: closeSnackbar, NotifierSnackbar }
}
