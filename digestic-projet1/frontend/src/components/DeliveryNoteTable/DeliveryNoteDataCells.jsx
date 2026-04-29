import React from 'react'
import { Avatar, Box, Button, Chip, Link, Typography, TableCell, IconButton, Tooltip, CircularProgress } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import DownloadIcon from '@mui/icons-material/Download'
import { AlignedTableCell } from '../ResizableTableColumns/ResizableHeaderCell'

function blStatusColor(status) {
  const colors = {
    sent: 'success',
    pending: 'warning',
    confirmed: 'primary',
    fully_invoiced: 'default',
    draft: 'default',
    validated: 'warning',
  }
  const key = status === 'valide' ? 'pending' : status
  return colors[key] || 'default'
}

const BL_STATUS_I18N = {
  pending: 'En attente',
  sent: 'Envoyé',
  confirmed: 'Confirmé',
  fully_invoiced: 'Facturé',
  draft: 'Brouillon',
  validated: 'Validé (visite)',
}

function blStatusLabel(status) {
  if (!status) {
    return '—'
  }
  const key = status === 'valide' ? 'pending' : status
  return BL_STATUS_I18N[key] || status
}

/**
 * @param {object} p
 * @param {object} p.row — item API (to_dict + pharmacy_name, commercial_name, linked_invoices)
 * @param {object} p.ctx — formatDate, navigate, getPhotoUrl, onFacturer, handleDownloadPdf, pdfLoadingId
 */
export function DeliveryNoteTableBodyCell(p) {
  const { columnKey, row, fullWidths, ctx } = p
  const w = fullWidths[columnKey] ?? 80
  if (columnKey === 'pharmacyName') {
    const name = row.pharmacy_name || row.pharmacy_id
    return (
      <AlignedTableCell width={w}>
        <Box display="flex" gap={1} alignItems="center" minWidth={0}>
          <Avatar src={ctx.getPhotoUrl?.(row.pharmacy_id)} alt={name} sx={{ width: 32, height: 32 }}>
            {name?.[0]}
          </Avatar>
          <Typography
            variant="body2"
            noWrap
            title={name}
            sx={{ color: 'primary.main', cursor: 'pointer' }}
            onClick={() => ctx?.navigate?.(`/pharmacies/${row.pharmacy_id}`)}
          >
            {name || '—'}
          </Typography>
        </Box>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'deliveryDate') {
    return (
      <AlignedTableCell width={w}>
        <Typography variant="body2" noWrap>
          {ctx.formatDate(row.delivery_date)}
        </Typography>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'blNumber') {
    return (
      <AlignedTableCell width={w}>
        <Typography variant="body2" noWrap title={row.bl_number || ''} sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
          {row.bl_number || '—'}
        </Typography>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'bottlesCount') {
    return (
      <AlignedTableCell width={w}>
        <Typography variant="body2" noWrap align="right" sx={{ display: 'block' }}>
          {row.bottles_count}
        </Typography>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'freeUnits') {
    return (
      <AlignedTableCell width={w}>
        <Typography variant="body2" noWrap align="right" sx={{ display: 'block' }}>
          {row.free_units_quantity ?? 0}
        </Typography>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'commercial') {
    return (
      <AlignedTableCell width={w}>
        <Typography variant="body2" noWrap title={row.commercial_name}>
          {row.commercial_name || row.commercial_id || '—'}
        </Typography>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'status') {
    return (
      <AlignedTableCell width={w}>
        <Chip
          label={blStatusLabel(row.status)}
          color={blStatusColor(row.status)}
          size="small"
        />
      </AlignedTableCell>
    )
  }
  if (columnKey === 'linkedInvoices') {
    return (
      <AlignedTableCell width={w}>
        {row.linked_invoices?.length ? (
          <Link
            component={RouterLink}
            to={`/invoices?deposit_id=${encodeURIComponent(row.id)}`}
            underline="hover"
            variant="body2"
            title="Liste des factures pour ce dépôt"
          >
            {row.linked_invoices.map((inv) => inv.invoice_number).join(', ')}
          </Link>
        ) : (
          <Typography variant="body2" color="text.secondary">
            —
          </Typography>
        )}
      </AlignedTableCell>
    )
  }
  if (columnKey === 'isDepositSale') {
    return (
      <AlignedTableCell width={w}>
        <Chip
          label={row.is_deposit_sale ? 'Oui' : 'Non'}
          color={row.is_deposit_sale ? 'warning' : 'default'}
          size="small"
        />
      </AlignedTableCell>
    )
  }
  if (columnKey === 'sageReference') {
    return (
      <AlignedTableCell width={w}>
        <Typography variant="body2" noWrap title={row.sage_reference}>
          {row.sage_reference || '—'}
        </Typography>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'depositId') {
    const did = row.id
    const short = did && did.length > 14 ? `${did.slice(0, 8)}…${did.slice(-4)}` : did
    return (
      <AlignedTableCell width={w}>
        <Link
          component={RouterLink}
          to={`/delivery-notes?deposit_id=${encodeURIComponent(did)}`}
          variant="body2"
          underline="hover"
          sx={{
            fontFamily: 'monospace',
            fontSize: '0.75rem',
            display: 'block',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
          title={did}
        >
          {short || '—'}
        </Link>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'emailSent') {
    return (
      <AlignedTableCell width={w}>
        <Chip label={row.email_sent ? 'Oui' : 'Non'} color={row.email_sent ? 'success' : 'default'} size="small" />
      </AlignedTableCell>
    )
  }
  return <AlignedTableCell width={w}>—</AlignedTableCell>
}

export function DeliveryNoteActionsCell({ row, fullWidths, ctx }) {
  const w = fullWidths.actions
  const disabled = (row.bottles_count || 0) < 1 || row.status === 'fully_invoiced'
  return (
    <TableCell
      align="right"
      padding="none"
      sx={{
        width: w,
        minWidth: w,
        maxWidth: w,
        boxSizing: 'border-box',
        py: 0.5,
        px: 1,
      }}
    >
      <Box display="flex" alignItems="center" justifyContent="flex-end" gap={0.5} flexWrap="nowrap">
        <Tooltip title="Télécharger le PDF du bon de livraison">
          <span>
            <IconButton
              size="small"
              disabled={ctx.pdfLoadingId === row.id}
              onClick={() => void ctx.handleDownloadPdf(row)}
              aria-label="Télécharger le PDF"
            >
              {ctx.pdfLoadingId === row.id ? (
                <CircularProgress color="inherit" size={22} />
              ) : (
                <DownloadIcon fontSize="small" />
              )}
            </IconButton>
          </span>
        </Tooltip>
        <Button size="small" variant="outlined" disabled={disabled} onClick={() => ctx.onFacturer(row)}>
          Facturer
        </Button>
      </Box>
    </TableCell>
  )
}
