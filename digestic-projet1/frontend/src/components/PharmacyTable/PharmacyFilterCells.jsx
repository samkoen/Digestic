import React from 'react'
import {
  Autocomplete,
  Checkbox,
  FormControl,
  ListItemText,
  MenuItem,
  OutlinedInput,
  Select,
  TextField,
} from '@mui/material'
import { AlignedTableCell } from '../ResizableTableColumns/ResizableHeaderCell'
import { PAYMENT_MODES } from '../../constants/paymentModes'

/** Pas de padding horizontal sur la TableCell : l’alignement est géré par AlignedTableCell (comme ResizableHeaderCell). */
const filterSx = { verticalAlign: 'top' }

/**
 * @param {object} p
 * @param {string} p.columnKey
 * @param {Record<string, number>} p.fullWidths
 * @param {object} p.filters
 * @param {function} p.onChange
 * @param {Array<{id: string, first_name: string, last_name: string}>} [p.commercials]
 * @param {Array<{id: string, name: string, city?: string}>} [p.depots]
 * @param {string[]} [p.cityOptions] — villes distinctes (API) pour multi-sélection
 */
export function PharmacyFilterCell(p) {
  const {
    columnKey,
    fullWidths,
    filters,
    onChange,
    commercials = [],
    depots = [],
    cityOptions = [],
  } = p
  const w = fullWidths[columnKey] ?? 80

  if (columnKey === 'commercial') {
    const commercialSel = Array.isArray(filters.commercial) ? filters.commercial : []
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <FormControl size="small" fullWidth>
          <Select
            multiple
            displayEmpty
            value={commercialSel}
            onChange={(e) => onChange('commercial', e.target.value)}
            input={<OutlinedInput notched={false} />}
            renderValue={(sel) =>
              !sel || sel.length === 0 ? 'Tous' : `${sel.length} commercial(aux)`
            }
            MenuProps={{ PaperProps: { sx: { maxHeight: 320 } } }}
          >
            {commercials.map((c) => (
              <MenuItem key={c.id} value={c.id}>
                <Checkbox checked={commercialSel.includes(c.id)} size="small" sx={{ mr: 0.5, py: 0 }} />
                <ListItemText primary={`${c.first_name} ${c.last_name}`} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'depot') {
    const depotSel = Array.isArray(filters.depot) ? filters.depot : []
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <FormControl size="small" fullWidth>
          <Select
            multiple
            displayEmpty
            value={depotSel}
            onChange={(e) => onChange('depot', e.target.value)}
            input={<OutlinedInput notched={false} />}
            renderValue={(sel) =>
              !sel || sel.length === 0 ? 'Tous' : `${sel.length} dépôt(s)`
            }
            MenuProps={{ PaperProps: { sx: { maxHeight: 320 } } }}
          >
            {depots.map((d) => (
              <MenuItem key={d.id} value={d.id}>
                <Checkbox checked={depotSel.includes(d.id)} size="small" sx={{ mr: 0.5, py: 0 }} />
                <ListItemText
                  primary={
                    <>
                      {d.name}
                      {d.city ? ` — ${d.city}` : ''}
                    </>
                  }
                />
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'status') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <TextField
          select
          value={filters.status}
          onChange={(e) => onChange('status', e.target.value)}
          size="small"
          fullWidth
          variant="outlined"
        >
          <MenuItem value="">Tous</MenuItem>
          <MenuItem value="actif">Actif</MenuItem>
          <MenuItem value="desactive">Désactivé</MenuItem>
          <MenuItem value="standby">Standby</MenuItem>
          <MenuItem value="autre">Autre / libre</MenuItem>
        </TextField>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'paymentMode') {
    const modeSel = Array.isArray(filters.paymentMode) ? filters.paymentMode : []
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <FormControl size="small" fullWidth>
          <Select
            multiple
            displayEmpty
            value={modeSel}
            onChange={(e) => onChange('paymentMode', e.target.value)}
            input={<OutlinedInput notched={false} />}
            renderValue={(sel) =>
              !sel || sel.length === 0 ? 'Tous' : `${sel.length} mode(s)`
            }
            MenuProps={{ PaperProps: { sx: { maxHeight: 320 } } }}
          >
            {PAYMENT_MODES.map((mode) => (
              <MenuItem key={mode} value={mode}>
                <Checkbox checked={modeSel.includes(mode)} size="small" sx={{ mr: 0.5, py: 0 }} />
                <ListItemText primary={mode} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'nextVisit') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <TextField
          type="date"
          value={filters.nextVisit}
          onChange={(e) => onChange('nextVisit', e.target.value)}
          size="small"
          fullWidth
          variant="outlined"
          InputLabelProps={{ shrink: true }}
        />
      </AlignedTableCell>
    )
  }
  if (columnKey === 'rib') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <TextField
          select
          value={filters.rib ?? ''}
          onChange={(e) => onChange('rib', e.target.value)}
          size="small"
          fullWidth
          variant="outlined"
        >
          <MenuItem value="">Tous</MenuItem>
          <MenuItem value="yes">Oui</MenuItem>
          <MenuItem value="no">Non</MenuItem>
        </TextField>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'createdAt') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <TextField
          value={filters.created}
          onChange={(e) => onChange('created', e.target.value)}
          size="small"
          placeholder="Filtrer (date)..."
          fullWidth
          variant="outlined"
        />
      </AlignedTableCell>
    )
  }
  if (columnKey === 'city') {
    const citySel = Array.isArray(filters.city) ? filters.city : []
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <FormControl size="small" fullWidth>
          <Select
            multiple
            displayEmpty
            value={citySel}
            onChange={(e) => onChange('city', e.target.value)}
            input={<OutlinedInput notched={false} />}
            renderValue={(sel) =>
              !sel || sel.length === 0 ? 'Tous' : `${sel.length} ville(s)`
            }
            MenuProps={{ PaperProps: { sx: { maxHeight: 320 } } }}
          >
            {cityOptions.length === 0 ? (
              <MenuItem disabled value="_">
                <ListItemText primary="Aucune ville en base pour l’instant" />
              </MenuItem>
            ) : (
              cityOptions.map((cityName) => (
                <MenuItem key={cityName} value={cityName}>
                  <Checkbox checked={citySel.includes(cityName)} size="small" sx={{ mr: 0.5, py: 0 }} />
                  <ListItemText primary={cityName} />
                </MenuItem>
              ))
            )}
          </Select>
        </FormControl>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'postalCode') {
    const value = Array.isArray(filters.postalCodes) ? filters.postalCodes : []
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <Autocomplete
          multiple
          freeSolo
          size="small"
          options={[]}
          value={value}
          onChange={(_, newValue) =>
            onChange(
              'postalCodes',
              newValue.map((x) => String(x).trim()).filter(Boolean),
            )
          }
          renderInput={(ip) => (
            <TextField {...ip} variant="outlined" placeholder="CP (plusieurs)…" />
          )}
          sx={{ width: '100%' }}
        />
      </AlignedTableCell>
    )
  }

  const textKey = {
    name: 'name',
    address: 'address',
    country: 'country',
    email: 'email',
    phone: 'phone',
    pharmacistName: 'pharmacistName',
    lastVisit: 'lastVisit',
    created: 'created',
  }[columnKey]

  if (!textKey) {
    return <AlignedTableCell width={w} dense sx={filterSx} />
  }

  return (
    <AlignedTableCell width={w} dense sx={filterSx}>
      <TextField
        value={filters[textKey] || ''}
        onChange={(e) => onChange(textKey, e.target.value)}
        size="small"
        placeholder="Filtrer..."
        fullWidth
        variant="outlined"
      />
    </AlignedTableCell>
  )
}
