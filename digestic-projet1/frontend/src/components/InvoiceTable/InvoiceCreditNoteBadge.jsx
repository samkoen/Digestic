import React from 'react'
import Tooltip from '@mui/material/Tooltip'
import RemoveCircleIcon from '@mui/icons-material/RemoveCircle'

/** Indicateur façon VosFactures : facture assortie d’au moins un avoir. */
export default function InvoiceCreditNoteBadge({ show }) {
  if (!show) return null
  return (
    <Tooltip title="Au moins un avoir est lié à cette facture." enterDelay={300}>
      <RemoveCircleIcon
        aria-label="Au moins un avoir est lié à cette facture"
        sx={{
          fontSize: 17,
          ml: '3px',
          color: '#546e7a',
          flexShrink: 0,
          display: 'block',
          verticalAlign: 'middle',
        }}
      />
    </Tooltip>
  )
}
