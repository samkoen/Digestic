import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Box,
  Button,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TablePagination,
  LinearProgress,
  TableSortLabel,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  TextField,
} from '@mui/material'
import ViewColumnIcon from '@mui/icons-material/ViewColumn'
import CloseIcon from '@mui/icons-material/Close'
import { format } from 'date-fns'
import { deliveryNoteService } from '../../services/deliveryNoteService'
import { pharmacyService } from '../../services/pharmacyService'
import { userService } from '../../services/userService'
import { productService } from '../../services/productService'
import { fetchDeliveryNotesTableView, saveDeliveryNotesTableView } from '../../services/tableViewService'
import { ResizableHeaderCell } from '../../components/ResizableTableColumns/ResizableHeaderCell'
import DeliveryNoteColumnPickerDialog from '../../components/DeliveryNoteTable/DeliveryNoteColumnPickerDialog'
import {
  DeliveryNoteTableBodyCell,
  DeliveryNoteActionsCell,
} from '../../components/DeliveryNoteTable/DeliveryNoteDataCells'
import { DeliveryNoteFilterCell } from '../../components/DeliveryNoteTable/DeliveryNoteFilterCells'
import { DeliveryNoteSavedFiltersBar } from '../../components/DeliveryNoteTable/DeliveryNoteSavedFiltersBar'
import {
  EMPTY_DELIVERY_NOTE_FILTERS,
  buildDeliveryNoteListQueryParams,
  deliveryNoteFiltersFromPayload,
  getInitialDeliveryNoteFiltersState,
  hasDirtyDeliveryNoteFilters,
} from '../../utils/deliveryNoteListQueryParams'
import { parseDepositFilterFromSearchParams } from '../../utils/invoiceListQueryParams'
import {
  computeResizablePixelWidths,
  defaultEqualFractions,
  loadDeliveryNoteColumnWidths,
  saveDeliveryNoteColumnWidths,
  DELIVERY_NOTE_COLUMN_MIN_PX,
  DELIVERY_NOTE_TABLE_ACTIONS_PX,
} from '../../utils/deliveryNoteTableLayoutUtils'

const headerCellTextSx = { fontSize: '0.75rem', fontWeight: 600 }

const DEFAULT_VISIBLE_COLUMNS = [
  'pharmacyName',
  'deliveryDate',
  'blNumber',
  'bottlesCount',
  'commercial',
  'status',
  'linkedInvoices',
]

/** Aligné sur `delivery_note_service.issue_invoice_from_delivery_note`. */
function indicativeInvoiceTotals(bottles, product) {
  const n = Math.max(0, Number(bottles) || 0)
  if (!product || n <= 0) {
    return { ht: 0, vat: 0, ttc: 0, vatRatePercent: 0 }
  }
  const unitHt = Number(product.wholesale_unit_price) || 0
  const vatRate = Number(product.vat_rate) || 0
  const lht = Math.round(n * unitHt * 10000) / 10000
  const lvat = Math.round(lht * (vatRate / 100) * 10000) / 10000
  const totalHt = Math.round(lht * 100) / 100
  const totalVat = Math.round(lvat * 100) / 100
  const ttc = Math.round((totalHt + totalVat) * 100) / 100
  return { ht: totalHt, vat: totalVat, ttc, vatRatePercent: vatRate }
}

function DeliveryNotes() {
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [listLoading, setListLoading] = useState(true)
  const [orderBy, setOrderBy] = useState('deliveryDate')
  const [order, setOrder] = useState('desc')
  const [user, setUser] = useState(null)
  const [filters, setFilters] = useState(getInitialDeliveryNoteFiltersState)
  const [debouncedFilters, setDebouncedFilters] = useState(getInitialDeliveryNoteFiltersState)
  const [pharmacyMap, setPharmacyMap] = useState({})
  const [commercials, setCommercials] = useState([])
  const [colWidthsPx, setColWidthsPx] = useState(null)
  const [tableWidth, setTableWidth] = useState(0)
  const [tableView, setTableView] = useState(null)
  const [columnPickerOpen, setColumnPickerOpen] = useState(false)
  const [savingColumns, setSavingColumns] = useState(false)
  const [activeSavedFilterId, setActiveSavedFilterId] = useState(null)
  const tableWidthRef = useRef(1200)
  const colResizeObserverRef = useRef(null)
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const [invoiceDialogOpen, setInvoiceDialogOpen] = useState(false)
  const [invoiceTarget, setInvoiceTarget] = useState(null)
  const [invoiceForm, setInvoiceForm] = useState({ bottles: 0 })
  const [billingProduct, setBillingProduct] = useState(null)
  const [pdfLoadingId, setPdfLoadingId] = useState(null)

  const resizableOrder = useMemo(() => {
    if (tableView?.visibleColumnKeys?.length) {
      return tableView.visibleColumnKeys
    }
    return DEFAULT_VISIBLE_COLUMNS
  }, [tableView])

  const getColumnLabel = useCallback(
    (key) => {
      const d = tableView?.definition?.find((c) => c.key === key)
      return d?.label || key
    },
    [tableView],
  )

  const setTableContainerRef = useCallback((el) => {
    if (colResizeObserverRef.current) {
      colResizeObserverRef.current.disconnect()
      colResizeObserverRef.current = null
    }
    if (!el) {
      return
    }
    const w0 = Math.floor(el.getBoundingClientRect().width)
    if (w0 > 0) {
      setTableWidth(w0)
      tableWidthRef.current = w0
    }
    const ro = new ResizeObserver((entries) => {
      const w = Math.floor(entries[0].contentRect.width)
      if (w > 0) {
        setTableWidth(w)
        tableWidthRef.current = w
      }
    })
    ro.observe(el)
    colResizeObserverRef.current = ro
  }, [])

  const { fullWidths, tableMinW } = useMemo(() => {
    const w = tableWidth > 0 ? tableWidth : tableWidthRef.current
    const W = Math.max(200, w)
    const A = DELIVERY_NOTE_TABLE_ACTIONS_PX
    if (colWidthsPx) {
      const sum = resizableOrder.reduce((a, k) => a + (colWidthsPx[k] || 0), 0)
      const tmin = sum + A
      return {
        fullWidths: { ...colWidthsPx, actions: A },
        tableMinW: Math.max(W, tmin),
      }
    }
    const frac = defaultEqualFractions(resizableOrder)
    const o = computeResizablePixelWidths(frac, w, DELIVERY_NOTE_COLUMN_MIN_PX, resizableOrder, A)
    return {
      fullWidths: { ...o.colWidths, actions: o.actions },
      tableMinW: o.tableMinWidth,
    }
  }, [tableWidth, colWidthsPx, resizableOrder])

  const getPairMaxW = useCallback(
    (key) => {
      const i = resizableOrder.indexOf(key)
      if (i < 0 || i >= resizableOrder.length - 1) {
        return 4000
      }
      const b = resizableOrder[i + 1]
      const minB = DELIVERY_NOTE_COLUMN_MIN_PX[b] ?? 64
      return fullWidths[key] + fullWidths[b] - minB
    },
    [fullWidths, resizableOrder],
  )

  const setColWidth = useCallback(
    (key) => (newAPx) => {
      setColWidthsPx((prev) => {
        if (!prev) {
          return prev
        }
        const i = resizableOrder.indexOf(key)
        if (i < 0 || i >= resizableOrder.length - 1) {
          return prev
        }
        const a = key
        const b = resizableOrder[i + 1]
        const minA = DELIVERY_NOTE_COLUMN_MIN_PX[a] ?? 64
        const minB = DELIVERY_NOTE_COLUMN_MIN_PX[b] ?? 64
        const pair = (prev[a] || 0) + (prev[b] || 0)
        const newA = Math.max(minA, Math.min(newAPx, pair - minB))
        const newB = pair - newA
        if (newA === prev[a] && newB === prev[b]) {
          return prev
        }
        return { ...prev, [a]: newA, [b]: newB }
      })
    },
    [resizableOrder],
  )

  const resizableKeyStr = resizableOrder.join(',')
  const resizableKeyStrPrev = useRef(null)

  useEffect(() => {
    if (resizableKeyStrPrev.current === null) {
      resizableKeyStrPrev.current = resizableKeyStr
      return
    }
    if (resizableKeyStrPrev.current !== resizableKeyStr) {
      resizableKeyStrPrev.current = resizableKeyStr
      setColWidthsPx(null)
    }
  }, [resizableKeyStr])

  useEffect(() => {
    if (tableWidth < 1 || colWidthsPx !== null) {
      return
    }
    const W = Math.max(200, tableWidth)
    const A = DELIVERY_NOTE_TABLE_ACTIONS_PX
    const saved = loadDeliveryNoteColumnWidths(resizableOrder)
    if (saved && resizableOrder.length) {
      const s0 = resizableOrder.reduce((a, k) => a + (saved[k] || 0), 0)
      if (s0 < 1) {
        setColWidthsPx(
          computeResizablePixelWidths(
            defaultEqualFractions(resizableOrder),
            W,
            DELIVERY_NOTE_COLUMN_MIN_PX,
            resizableOrder,
            A,
          ).colWidths,
        )
        return
      }
      const frac = Object.fromEntries(
        resizableOrder.map((k) => [k, (saved[k] || 0) / s0]),
      )
      setColWidthsPx(
        computeResizablePixelWidths(frac, W, DELIVERY_NOTE_COLUMN_MIN_PX, resizableOrder, A).colWidths,
      )
    } else {
      setColWidthsPx(
        computeResizablePixelWidths(
          defaultEqualFractions(resizableOrder),
          W,
          DELIVERY_NOTE_COLUMN_MIN_PX,
          resizableOrder,
          A,
        ).colWidths,
      )
    }
  }, [tableWidth, colWidthsPx, resizableKeyStr, resizableOrder])

  useEffect(() => {
    if (!colWidthsPx || !resizableOrder.length) {
      return
    }
    saveDeliveryNoteColumnWidths(resizableOrder, colWidthsPx)
  }, [colWidthsPx, resizableKeyStr, resizableOrder])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const list = await productService.list({ active_only: true })
        if (cancelled) return
        const def =
          list.find((p) => p.is_default_for_billing) || list[0] || null
        setBillingProduct(def)
      } catch (e) {
        console.error(e)
        if (!cancelled) setBillingProduct(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const stored = localStorage.getItem('user')
    if (stored) {
      setUser(JSON.parse(stored))
    }
  }, [])

  useEffect(() => {
    const extra = parseDepositFilterFromSearchParams(searchParams)
    if (!extra) {
      return
    }
    setPage(0)
    setActiveSavedFilterId(null)
    setFilters((prev) => ({ ...prev, ...extra, includeArchived: true }))
    setDebouncedFilters((prev) => ({ ...prev, ...extra, includeArchived: true }))
  }, [searchParams])

  useEffect(() => {
    let c = true
    ;(async () => {
      try {
        const d = await fetchDeliveryNotesTableView()
        if (c) setTableView(d)
      } catch (e) {
        console.error(e)
        if (c) {
          setTableView({
            viewKey: 'delivery_notes',
            definition: [],
            visibleColumnKeys: DEFAULT_VISIBLE_COLUMNS,
          })
        }
      }
    })()
    return () => {
      c = false
    }
  }, [])

  const loadMetaMaps = useCallback(async () => {
    try {
      const [pharmacies, comms] = await Promise.all([
        pharmacyService.getAll(),
        userService.getAll('commercial'),
      ])
      const pmap = {}
      for (const p of pharmacies || []) {
        pmap[p.id] = { name: p.name, photo_url: p.photo_url }
      }
      setPharmacyMap(pmap)
      setCommercials(comms || [])
    } catch (e) {
      console.error(e)
    }
  }, [])

  useEffect(() => {
    void loadMetaMaps()
  }, [loadMetaMaps])

  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedFilters((prev) => {
        const next = { ...filters }
        if (JSON.stringify(prev) === JSON.stringify(next)) {
          return prev
        }
        return next
      })
    }, 400)
    return () => clearTimeout(t)
  }, [filters])

  const loadData = useCallback(async () => {
    setListLoading(true)
    try {
      const data = await deliveryNoteService.getList(
        buildDeliveryNoteListQueryParams({
          page,
          rowsPerPage,
          orderBy,
          order,
          debouncedFilters,
        }),
      )
      setRows(data.items || [])
      setTotal(data.total ?? 0)
    } catch (e) {
      console.error(e)
      setRows([])
      setTotal(0)
    } finally {
      setListLoading(false)
    }
  }, [page, rowsPerPage, orderBy, order, debouncedFilters])

  useEffect(() => {
    void loadData()
  }, [loadData])

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    try {
      return format(new Date(dateString), 'dd/MM/yyyy')
    } catch {
      return dateString
    }
  }

  const getPhotoUrl = useCallback(
    (pharmacyId) => {
      const stored = pharmacyMap[pharmacyId]
      if (stored?.photo_url) {
        return stored.photo_url
      }
      const seed = encodeURIComponent(pharmacyId || 'pharmacy')
      return `https://picsum.photos/seed/${seed}/200/200`
    },
    [pharmacyMap],
  )

  const invoiceIndicative = useMemo(
    () => indicativeInvoiceTotals(invoiceForm.bottles, billingProduct),
    [invoiceForm.bottles, billingProduct],
  )

  const handleDownloadPdf = useCallback(async (row) => {
    try {
      setPdfLoadingId(row.id)
      await deliveryNoteService.downloadPdf(row.id)
    } catch (e) {
      console.error('PDF bon de livraison:', e)
      // eslint-disable-next-line no-alert
      alert(e.message || 'Impossible de télécharger le PDF')
    } finally {
      setPdfLoadingId(null)
    }
  }, [])

  const bodyCtx = useMemo(
    () => ({
      formatDate,
      navigate,
      getPhotoUrl,
      onFacturer: (note) => {
        setInvoiceTarget(note)
        setInvoiceForm({ bottles: note.bottles_count })
        setInvoiceDialogOpen(true)
      },
      handleDownloadPdf,
      pdfLoadingId,
    }),
    [navigate, getPhotoUrl, handleDownloadPdf, pdfLoadingId],
  )

  const handleSort = (property) => {
    setActiveSavedFilterId(null)
    if (property !== orderBy) {
      setPage(0)
    }
    const isAsc = orderBy === property && order === 'asc'
    setOrder(isAsc ? 'desc' : 'asc')
    setOrderBy(property)
  }

  const handleFilterChange = (field, value) => {
    setActiveSavedFilterId(null)
    setPage(0)
    setFilters((prev) => ({ ...prev, [field]: value }))
  }

  const handleSelectSavedFilter = useCallback((item) => {
    setPage(0)
    const pl = item.payload || {}
    const next = deliveryNoteFiltersFromPayload(pl.filters)
    setFilters(next)
    setDebouncedFilters(next)
    if (pl.orderBy) {
      setOrderBy(pl.orderBy)
    }
    if (pl.order) {
      setOrder(pl.order)
    }
    setActiveSavedFilterId(item.id)
  }, [])

  const clearFilters = () => {
    setActiveSavedFilterId(null)
    setPage(0)
    const z = { ...EMPTY_DELIVERY_NOTE_FILTERS }
    setFilters(z)
    setDebouncedFilters(z)
    setSearchParams({}, { replace: true })
  }

  const onSaveColumnPicker = async (keys) => {
    setSavingColumns(true)
    try {
      const res = await saveDeliveryNotesTableView(keys)
      setTableView((prev) => ({ ...prev, visibleColumnKeys: res.visibleColumnKeys }))
      setColWidthsPx(null)
      setColumnPickerOpen(false)
    } catch (e) {
      console.error(e)
      // eslint-disable-next-line no-alert
      alert(e?.response?.data?.error || e.message || 'Erreur de sauvegarde')
    } finally {
      setSavingColumns(false)
    }
  }

  const closeInvoiceDialog = () => {
    setInvoiceDialogOpen(false)
    setInvoiceTarget(null)
  }

  const handleIssueInvoiceSubmit = async () => {
    if (!invoiceTarget) return
    try {
      await deliveryNoteService.issueInvoice(invoiceTarget.id, {
        bottles_to_invoice: invoiceForm.bottles,
        amount: invoiceIndicative.ttc,
      })
      closeInvoiceDialog()
      void loadData()
      void loadMetaMaps()
    } catch (error) {
      console.error(error)
      const data = error.response?.data
      const msg = [data?.error, data?.detail].filter(Boolean).join('\n') || error.message
      // eslint-disable-next-line no-alert
      alert(msg || 'Erreur lors de la facturation')
    }
  }

  const hasFilterBar = hasDirtyDeliveryNoteFilters(filters)
  const nDataCols = resizableOrder.length
  const zBase = 20

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1} flexWrap="wrap" gap={2}>
        <Typography variant="h4">Bons de livraison</Typography>
        <Box display="flex" gap={2} flexWrap="wrap" justifyContent="flex-end" alignItems="center">
          {hasFilterBar && (
            <Button variant="outlined" onClick={clearFilters} size="small">
              Réinitialiser filtres
            </Button>
          )}
          {user?.role === 'admin' && (
            <Button
              variant="outlined"
              startIcon={<ViewColumnIcon />}
              size="small"
              onClick={() => setColumnPickerOpen(true)}
            >
              Colonnes
            </Button>
          )}
        </Box>
      </Box>

      {user && (
        <DeliveryNoteSavedFiltersBar
          filters={filters}
          orderBy={orderBy}
          order={order}
          activeSavedFilterId={activeSavedFilterId}
          onSelectSaved={handleSelectSavedFilter}
          onActiveFilterRemoved={() => setActiveSavedFilterId(null)}
        />
      )}

      {user?.role === 'admin' && tableView && (
        <DeliveryNoteColumnPickerDialog
          open={columnPickerOpen}
          onClose={() => setColumnPickerOpen(false)}
          definition={tableView.definition}
          initialKeys={tableView.visibleColumnKeys}
          onSave={onSaveColumnPicker}
          saving={savingColumns}
        />
      )}

      <Box ref={setTableContainerRef} sx={{ width: '100%', minWidth: 0 }}>
        <TableContainer
          component={Paper}
          sx={{ position: 'relative', overflowX: 'auto', width: '100%' }}
        >
          {listLoading && <LinearProgress sx={{ position: 'absolute', top: 0, left: 0, right: 0, zIndex: 1 }} />}
          <Table
            size="small"
            sx={{
              tableLayout: 'fixed',
              width: '100%',
              minWidth: tableMinW,
            }}
          >
            <TableHead
              sx={{
                overflow: 'visible',
                '& .MuiTableRow-root': { overflow: 'visible' },
              }}
            >
              <TableRow sx={{ position: 'relative' }}>
                {resizableOrder.map((colKey, idx) => {
                  const last = idx === nDataCols - 1
                  const d = tableView?.definition?.find((c) => c.key === colKey)
                  const sortable = d ? d.sortable !== false : true
                  return (
                    <ResizableHeaderCell
                      key={colKey}
                      width={fullWidths[colKey]}
                      onWidthChange={setColWidth(colKey)}
                      minWidth={DELIVERY_NOTE_COLUMN_MIN_PX[colKey] ?? 64}
                      maxWidth={getPairMaxW(colKey)}
                      resizable={!last}
                      stackZIndex={zBase - idx}
                      sx={headerCellTextSx}
                    >
                      {sortable ? (
                        <TableSortLabel
                          active={orderBy === colKey}
                          direction={orderBy === colKey ? order : 'asc'}
                          onClick={() => handleSort(colKey)}
                        >
                          {getColumnLabel(colKey)}
                        </TableSortLabel>
                      ) : (
                        getColumnLabel(colKey)
                      )}
                    </ResizableHeaderCell>
                  )
                })}
                <ResizableHeaderCell
                  width={fullWidths.actions}
                  resizable={false}
                  align="right"
                  stackZIndex={0}
                  sx={headerCellTextSx}
                >
                  Actions
                </ResizableHeaderCell>
              </TableRow>
              <TableRow>
                {resizableOrder.map((colKey) => (
                  <DeliveryNoteFilterCell
                    key={`f-${colKey}`}
                    columnKey={colKey}
                    fullWidths={fullWidths}
                    filters={filters}
                    onChange={handleFilterChange}
                    definition={tableView?.definition}
                    commercials={commercials}
                  />
                ))}
                <TableCell
                  align="right"
                  padding="none"
                  sx={{
                    width: fullWidths.actions,
                    minWidth: fullWidths.actions,
                    maxWidth: fullWidths.actions,
                    boxSizing: 'border-box',
                    py: 0.75,
                    pl: 2,
                    pr: 2,
                    ...headerCellTextSx,
                  }}
                />
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.length === 0 && !listLoading && (
                <TableRow>
                  <TableCell colSpan={nDataCols + 1} align="center">
                    <Typography color="textSecondary" py={2}>
                      {debouncedFilters.depositId
                        ? 'Aucun bon pour ces critères (identifiant inconnu ou déjà clôturé si « inclure clôturés » est décoché).'
                        : 'Aucun bon de livraison'}
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
              {rows.map((row) => (
                <TableRow key={row.id} hover>
                  {resizableOrder.map((colKey) => (
                    <DeliveryNoteTableBodyCell
                      key={`${row.id}-${colKey}`}
                      columnKey={colKey}
                      row={row}
                      fullWidths={fullWidths}
                      ctx={bodyCtx}
                    />
                  ))}
                  <DeliveryNoteActionsCell row={row} fullWidths={fullWidths} ctx={bodyCtx} />
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <TablePagination
            component="div"
            count={total}
            page={page}
            onPageChange={(_, p) => setPage(p)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(e) => {
              setRowsPerPage(parseInt(e.target.value, 10))
              setPage(0)
            }}
            rowsPerPageOptions={[10, 25, 50, 100]}
            labelRowsPerPage="Lignes par page"
          />
        </TableContainer>
      </Box>

      <Dialog open={invoiceDialogOpen} onClose={closeInvoiceDialog} maxWidth="xs" fullWidth>
        <DialogTitle>
          Émettre la facture
          <IconButton
            aria-label="fermer"
            onClick={closeInvoiceDialog}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Création de la facture à partir de ce bon de livraison (VosFactures si configuré). Les montants
            sont calculés côté serveur à partir du <strong>produit par défaut de facturation</strong>
            {billingProduct?.name ? (
              <>
                {' '}
                (« {billingProduct.name} », {Number(billingProduct.wholesale_unit_price).toFixed(2)} € HT / unité,
                TVA {Number(billingProduct.vat_rate).toFixed(1)} %)
              </>
            ) : null}
            . Estimation ci-dessous (même logique que la facture émise).
          </Typography>
          <TextField
            fullWidth
            label="Bouteilles à facturer"
            type="number"
            value={invoiceForm.bottles}
            inputProps={{ min: 1, max: invoiceTarget?.bottles_count || 0 }}
            onChange={(e) =>
              setInvoiceForm((prev) => ({
                ...prev,
                bottles: Math.min(
                  Math.max(Number(e.target.value), 1),
                  invoiceTarget?.bottles_count || 1,
                ),
              }))
            }
            sx={{ mb: 2 }}
          />
          {!billingProduct ? (
            <Typography variant="body2" color="warning.main">
              Aucun produit actif en base : impossible d’estimer le montant ici.
            </Typography>
          ) : (
            <Box
              sx={{
                p: 1.5,
                borderRadius: 1,
                bgcolor: 'action.hover',
                border: 1,
                borderColor: 'divider',
              }}
            >
              <Typography variant="subtitle2" gutterBottom>
                Montants indicatifs (ligne payante)
              </Typography>
              <Typography variant="body2">
                Total HT : <strong>{invoiceIndicative.ht.toFixed(2)} €</strong>
              </Typography>
              <Typography variant="body2">
                TVA ({invoiceIndicative.vatRatePercent.toFixed(1)} %) :{' '}
                <strong>{invoiceIndicative.vat.toFixed(2)} €</strong>
              </Typography>
              <Typography variant="body2">
                Total TTC : <strong>{invoiceIndicative.ttc.toFixed(2)} €</strong>
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeInvoiceDialog}>Annuler</Button>
          <Button
            variant="contained"
            onClick={() => void handleIssueInvoiceSubmit()}
            disabled={
              !invoiceForm.bottles || invoiceForm.bottles > (invoiceTarget?.bottles_count || 0)
            }
          >
            Facturer
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default DeliveryNotes
