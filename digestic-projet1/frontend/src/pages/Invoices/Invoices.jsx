import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Box,
  Button,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Paper,
  TablePagination,
  LinearProgress,
  TableSortLabel,
  Tabs,
  Tab,
  Checkbox,
} from '@mui/material'
import ViewColumnIcon from '@mui/icons-material/ViewColumn'
import { format } from 'date-fns'
import { pharmacyService } from '../../services/pharmacyService'
import { invoiceService } from '../../services/invoiceService'
import { creditNoteService } from '../../services/creditNoteService'
import { fetchInvoiceTableView, saveInvoiceTableView } from '../../services/tableViewService'
import { ResizableHeaderCell } from '../../components/ResizableTableColumns/ResizableHeaderCell'
import InvoiceColumnPickerDialog from '../../components/InvoiceTable/InvoiceColumnPickerDialog'
import { InvoiceTableBodyCell, InvoiceActionsCell } from '../../components/InvoiceTable/InvoiceDataCells'
import IssueTotalCreditNoteDialog from '../../components/InvoiceTable/IssueTotalCreditNoteDialog'
import MarkInvoicePaidDialog from '../../components/InvoiceTable/MarkInvoicePaidDialog'
import { InvoiceFilterCell } from '../../components/InvoiceTable/InvoiceFilterCells'
import { InvoiceSavedFiltersBar } from '../../components/InvoiceTable/InvoiceSavedFiltersBar'
import {
  EMPTY_INVOICE_FILTERS,
  buildInvoiceListQueryParams,
  getInitialInvoiceFiltersState,
  invoiceFiltersFromPayload,
  parseDepositFilterFromSearchParams,
  parseInvoiceNumberFilterFromSearchParams,
  parsePharmacyFilterFromSearchParams,
} from '../../utils/invoiceListQueryParams'
import {
  computeResizablePixelWidths,
  defaultEqualFractions,
  loadInvoiceColumnWidths,
  saveInvoiceColumnWidths,
  INVOICE_COLUMN_MIN_PX,
  INVOICE_SELECT_COL_PX,
  INVOICE_TABLE_ACTIONS_PX,
} from '../../utils/invoiceTableLayoutUtils'
import { LIST_TABLE_SCROLL_MAX_HEIGHT } from '../../constants/listTableLayout'
import { canIssueTotalCreditNote, canMarkInvoicePaid } from '../../utils/invoiceCreditNoteEligibility'
import SendEmailComposerDialog from '../../components/SendEmailComposerDialog/SendEmailComposerDialog'
import { useNotifier } from '../../hooks/useNotifier'

const headerCellTextSx = { fontSize: '0.75rem', fontWeight: 600 }

const DEFAULT_VISIBLE_COLUMNS = [
  'invoiceNumber',
  'pharmacyName',
  'blNumber',
  'amount',
  'issueDate',
  'dueDate',
  'status',
  'daysOverdue',
]

function hasDirtyFilters(tab, f) {
  if (tab === 1) {
    return true
  }
  if (f.invoiceNumber || f.pharmacyName || f.pharmacyId || f.depositId || f.status) {
    return true
  }
  if (f.overdueOnly) {
    return true
  }
  return false
}

function Invoices() {
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [listLoading, setListLoading] = useState(true)
  const [orderBy, setOrderBy] = useState('issueDate')
  const [order, setOrder] = useState('desc')
  const [user, setUser] = useState(null)
  const [tab, setTab] = useState(0)
  const [filters, setFilters] = useState(getInitialInvoiceFiltersState)
  const [debouncedFilters, setDebouncedFilters] = useState(getInitialInvoiceFiltersState)
  const [colWidthsPx, setColWidthsPx] = useState(null)
  const [tableWidth, setTableWidth] = useState(0)
  const [tableView, setTableView] = useState(null)
  const [columnPickerOpen, setColumnPickerOpen] = useState(false)
  const [savingColumns, setSavingColumns] = useState(false)
  const [activeSavedFilterId, setActiveSavedFilterId] = useState(null)
  const [pdfLoadingId, setPdfLoadingId] = useState(null)
  const [selectedInvoiceIds, setSelectedInvoiceIds] = useState(() => new Set())
  const [creditNoteTargetInvoice, setCreditNoteTargetInvoice] = useState(null)
  const [markPaidTargetInvoice, setMarkPaidTargetInvoice] = useState(null)
  const [pharmacyMap, setPharmacyMap] = useState({})
  const [invEmailOpen, setInvEmailOpen] = useState(false)
  const [invEmailInvoiceId, setInvEmailInvoiceId] = useState(null)
  const [invEmailDraft, setInvEmailDraft] = useState(null)
  const [invEmailDraftLoading, setInvEmailDraftLoading] = useState(false)
  const [invEmailDraftError, setInvEmailDraftError] = useState(null)
  const [invEmailSending, setInvEmailSending] = useState(false)
  const [invEmailSendError, setInvEmailSendError] = useState(null)
  const [invReminderSendingId, setInvReminderSendingId] = useState(null)
  const tableWidthRef = useRef(1200)
  const colResizeObserverRef = useRef(null)
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { notify, NotifierSnackbar } = useNotifier()

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
    const A = INVOICE_TABLE_ACTIONS_PX
    const Sel = INVOICE_SELECT_COL_PX
    if (colWidthsPx) {
      const sum = resizableOrder.reduce((a, k) => a + (colWidthsPx[k] || 0), 0)
      const tmin = sum + A + Sel
      return {
        fullWidths: { ...colWidthsPx, actions: A },
        tableMinW: Math.max(W, tmin),
      }
    }
    const frac = defaultEqualFractions(resizableOrder)
    const o = computeResizablePixelWidths(frac, w, INVOICE_COLUMN_MIN_PX, resizableOrder, A)
    return {
      fullWidths: { ...o.colWidths, actions: o.actions },
      tableMinW: o.tableMinWidth + Sel,
    }
  }, [tableWidth, colWidthsPx, resizableOrder])

  const getPairMaxW = useCallback(
    (key) => {
      const i = resizableOrder.indexOf(key)
      if (i < 0 || i >= resizableOrder.length - 1) {
        return 4000
      }
      const b = resizableOrder[i + 1]
      const minB = INVOICE_COLUMN_MIN_PX[b] ?? 64
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
        const minA = INVOICE_COLUMN_MIN_PX[a] ?? 64
        const minB = INVOICE_COLUMN_MIN_PX[b] ?? 64
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
    const A = INVOICE_TABLE_ACTIONS_PX
    const saved = loadInvoiceColumnWidths(resizableOrder)
    if (saved && resizableOrder.length) {
      const s0 = resizableOrder.reduce((a, k) => a + (saved[k] || 0), 0)
      if (s0 < 1) {
        setColWidthsPx(
          computeResizablePixelWidths(
            defaultEqualFractions(resizableOrder),
            W,
            INVOICE_COLUMN_MIN_PX,
            resizableOrder,
            A,
          ).colWidths,
        )
        return
      }
      const frac = Object.fromEntries(
        resizableOrder.map((k) => [k, (saved[k] || 0) / s0]),
      )
      setColWidthsPx(computeResizablePixelWidths(frac, W, INVOICE_COLUMN_MIN_PX, resizableOrder, A).colWidths)
    } else {
      setColWidthsPx(
        computeResizablePixelWidths(
          defaultEqualFractions(resizableOrder),
          W,
          INVOICE_COLUMN_MIN_PX,
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
    saveInvoiceColumnWidths(resizableOrder, colWidthsPx)
  }, [colWidthsPx, resizableKeyStr, resizableOrder])

  const formatDate = (dateString) => {
    if (!dateString) {
      return '-'
    }
    try {
      return format(new Date(dateString), 'dd/MM/yyyy')
    } catch {
      return dateString
    }
  }

  const canDownloadVosFacturesPdf = useCallback((inv) => {
    if (inv.row_kind === 'credit_note') {
      return inv.external_provider === 'vosfactures' && Boolean(inv.external_credit_note_id)
    }
    return inv.external_provider === 'vosfactures' && Boolean(inv.external_invoice_id)
  }, [])

  const handleDownloadPdf = useCallback(async (inv) => {
    try {
      setPdfLoadingId(inv.id)
      if (inv.row_kind === 'credit_note') {
        await creditNoteService.downloadVosFacturesPdf(inv.id)
      } else {
        await invoiceService.downloadVosFacturesPdf(inv.id)
      }
    } catch (e) {
      console.error('PDF facture/avoir:', e)
      notify(e.message || 'Impossible de télécharger le PDF', 'error')
    } finally {
      setPdfLoadingId(null)
    }
  }, [notify])

  const navigateToPharmacy = useCallback(
    (pharmacyId) => {
      const qs = searchParams.toString()
      navigate(`/pharmacies/${pharmacyId}`, {
        state: {
          from: '/invoices',
          ...(qs ? { returnSearch: `?${qs}` } : {}),
        },
      })
    },
    [navigate, searchParams],
  )

  useEffect(() => {
    const stored = localStorage.getItem('user')
    if (stored) {
      setUser(JSON.parse(stored))
    }
  }, [])

  /** Navigation interne (ex. fiche pharmacie, lien depuis un BL ou une facture) : sync query → filtres */
  useEffect(() => {
    const extraP = parsePharmacyFilterFromSearchParams(searchParams)
    const extraD = parseDepositFilterFromSearchParams(searchParams)
    const extraN = parseInvoiceNumberFilterFromSearchParams(searchParams)
    if (!extraP && !extraD && !extraN) {
      return
    }
    const merged = { ...(extraP || {}), ...(extraD || {}), ...(extraN || {}) }
    setPage(0)
    setTab(0)
    setActiveSavedFilterId(null)
    setFilters((prev) => ({ ...prev, ...merged }))
    setDebouncedFilters((prev) => ({ ...prev, ...merged }))
  }, [searchParams])

  useEffect(() => {
    let c = true
    ;(async () => {
      try {
        const d = await fetchInvoiceTableView()
        if (c) {
          setTableView(d)
        }
      } catch (e) {
        console.error(e)
        if (c) {
          setTableView({
            viewKey: 'invoices',
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
      const data = await invoiceService.getList(
        buildInvoiceListQueryParams({
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

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const list = await pharmacyService.getAll()
        if (cancelled) return
        const map = {}
        for (const p of list || []) {
          map[p.id] = {
            email: p.email,
            pharmacist_email: p.pharmacist_email,
          }
        }
        setPharmacyMap(map)
      } catch (e) {
        console.error(e)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const resetInvEmailComposer = useCallback(() => {
    setInvEmailOpen(false)
    setInvEmailInvoiceId(null)
    setInvEmailDraft(null)
    setInvEmailDraftError(null)
    setInvEmailSendError(null)
    setInvEmailDraftLoading(false)
    setInvEmailSending(false)
  }, [])

  const handleCloseInvEmailComposer = useCallback(() => {
    if (invEmailSending) {
      return
    }
    resetInvEmailComposer()
  }, [invEmailSending, resetInvEmailComposer])

  const handleOpenInvoiceEmailComposer = useCallback(async (inv) => {
    if (inv.row_kind === 'credit_note') {
      return
    }
    setInvEmailInvoiceId(inv.id)
    setInvEmailOpen(true)
    setInvEmailDraft(null)
    setInvEmailDraftError(null)
    setInvEmailSendError(null)
    setInvEmailDraftLoading(true)
    try {
      const d = await invoiceService.getEmailDraft(inv.id)
      setInvEmailDraft(d)
    } catch (e) {
      console.error(e)
      setInvEmailDraftError(
        e?.response?.data?.error || e.message || 'Impossible de charger le brouillon d’e-mail',
      )
    } finally {
      setInvEmailDraftLoading(false)
    }
  }, [])

  const handleConfirmInvoiceTableEmailSend = useCallback(
    async ({ subject, body_html }) => {
      if (!invEmailInvoiceId) {
        return
      }
      setInvEmailSendError(null)
      setInvEmailSending(true)
      try {
        const res = await invoiceService.sendEmail(invEmailInvoiceId, {
          subject,
          body_html,
        })
        void loadData()
        notify(
          res.message || (res.email ? `E-mail envoyé à ${res.email}` : 'Envoi effectué.'),
          'success',
        )
        resetInvEmailComposer()
      } catch (e) {
        console.error(e)
        setInvEmailSendError(e?.response?.data?.error || e.message || 'Envoi impossible')
      } finally {
        setInvEmailSending(false)
      }
    },
    [invEmailInvoiceId, loadData, notify, resetInvEmailComposer],
  )

  const handleSendInvoiceUnpaidReminder = useCallback(
    async (inv) => {
      if (!inv?.id || inv.row_kind === 'credit_note') {
        return
      }
      setInvReminderSendingId(inv.id)
      try {
        const res = await invoiceService.sendUnpaidReminderEmail(inv.id)
        void loadData()
        notify(res.message || (res.email ? `Relance envoyée à ${res.email}` : 'Relance envoyée.'), 'success')
      } catch (e) {
        console.error(e)
        notify(
          e?.response?.data?.error || e.message || 'Impossible d’envoyer la relance.',
          'error',
        )
      } finally {
        setInvReminderSendingId(null)
      }
    },
    [loadData, notify],
  )

  const invEmailBusyRowId =
    invEmailDraftLoading || invEmailSending ? invEmailInvoiceId : null

  const bodyCtx = useMemo(
    () => ({
      formatDate,
      canDownloadVosFacturesPdf,
      canIssueTotalCreditNote,
      canMarkInvoicePaid,
      requestIssueCreditNote: (inv) => setCreditNoteTargetInvoice(inv),
      requestMarkPaid: (inv) => setMarkPaidTargetInvoice(inv),
      handleDownloadPdf,
      pdfLoadingId,
      navigateToPharmacy,
      pharmacyMap,
      handleOpenInvoiceEmailComposer,
      invEmailBusyRowId,
      invEmailOpen,
      invReminderSendingId,
      handleSendInvoiceUnpaidReminder,
    }),
    [
      navigateToPharmacy,
      pdfLoadingId,
      canDownloadVosFacturesPdf,
      handleDownloadPdf,
      pharmacyMap,
      handleOpenInvoiceEmailComposer,
      invEmailBusyRowId,
      invEmailOpen,
      canIssueTotalCreditNote,
      canMarkInvoicePaid,
      invReminderSendingId,
      handleSendInvoiceUnpaidReminder,
    ],
  )

  const handleTabChange = (_, newTab) => {
    setTab(newTab)
    setActiveSavedFilterId(null)
    setPage(0)
    if (newTab === 1) {
      setFilters((prev) => ({ ...prev, overdueOnly: true, overdueMinDays: 30 }))
    } else {
      setFilters((prev) => ({ ...prev, overdueOnly: false }))
    }
  }

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
    const next = invoiceFiltersFromPayload(pl.filters)
    setFilters(next)
    setDebouncedFilters(next)
    if (pl.orderBy) {
      setOrderBy(pl.orderBy === 'blDeposit' ? 'blNumber' : pl.orderBy)
    }
    if (pl.order) {
      setOrder(pl.order)
    }
    setActiveSavedFilterId(item.id)
    if (next.overdueOnly) {
      setTab(1)
    } else {
      setTab(0)
    }
  }, [])

  const clearFilters = () => {
    setActiveSavedFilterId(null)
    setPage(0)
    setTab(0)
    const z = { ...EMPTY_INVOICE_FILTERS, overdueOnly: false }
    setFilters(z)
    setDebouncedFilters(z)
    setSearchParams({}, { replace: true })
  }

  const onSaveColumnPicker = async (keys) => {
    setSavingColumns(true)
    try {
      const res = await saveInvoiceTableView(keys)
      setTableView((prev) => ({ ...prev, visibleColumnKeys: res.visibleColumnKeys }))
      setColWidthsPx(null)
      setColumnPickerOpen(false)
    } catch (e) {
      console.error(e)
      notify(e?.response?.data?.error || e.message || 'Erreur de sauvegarde', 'error')
    } finally {
      setSavingColumns(false)
    }
  }

  const selectableRowIds = useMemo(
    () => rows.filter((r) => r.row_kind !== 'credit_note').map((r) => r.id),
    [rows],
  )

  const headerBulkCheckboxProps = useMemo(() => {
    const ids = selectableRowIds
    if (ids.length === 0) {
      return { checked: false, indeterminate: false }
    }
    const sel = ids.filter((id) => selectedInvoiceIds.has(id)).length
    return {
      checked: sel === ids.length,
      indeterminate: sel > 0 && sel < ids.length,
    }
  }, [selectableRowIds, selectedInvoiceIds])

  const toggleSelectRow = useCallback((id) => {
    setSelectedInvoiceIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const toggleSelectAllOnPage = useCallback(() => {
    const ids = rows.filter((r) => r.row_kind !== 'credit_note').map((r) => r.id)
    if (ids.length === 0) return
    setSelectedInvoiceIds((prev) => {
      const allOn = ids.every((id) => prev.has(id))
      const next = new Set(prev)
      if (allOn) {
        for (const id of ids) next.delete(id)
      } else {
        for (const id of ids) next.add(id)
      }
      return next
    })
  }, [rows])

  const hasFilterBar = hasDirtyFilters(tab, filters)
  const nDataCols = resizableOrder.length
  const zBase = 20
  const selectColSx = {
    width: INVOICE_SELECT_COL_PX,
    minWidth: INVOICE_SELECT_COL_PX,
    maxWidth: INVOICE_SELECT_COL_PX,
    boxSizing: 'border-box',
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1} flexWrap="wrap" gap={2}>
        <Typography variant="h4">Factures</Typography>
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

      <Tabs value={tab} onChange={handleTabChange} sx={{ mb: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Tab label="Toutes les factures" />
        <Tab label="Factures en retard (30 j+)" />
      </Tabs>

      {user && (
        <InvoiceSavedFiltersBar
          filters={filters}
          orderBy={orderBy}
          order={order}
          activeSavedFilterId={activeSavedFilterId}
          onSelectSaved={handleSelectSavedFilter}
          onActiveFilterRemoved={() => setActiveSavedFilterId(null)}
        />
      )}

      {user?.role === 'admin' && tableView && (
        <InvoiceColumnPickerDialog
          open={columnPickerOpen}
          onClose={() => setColumnPickerOpen(false)}
          definition={tableView.definition}
          initialKeys={tableView.visibleColumnKeys}
          onSave={onSaveColumnPicker}
          saving={savingColumns}
        />
      )}

      <Box ref={setTableContainerRef} sx={{ width: '100%', minWidth: 0 }}>
        <Paper
          elevation={2}
          sx={{
            display: 'flex',
            flexDirection: 'column',
            width: '100%',
            maxHeight: LIST_TABLE_SCROLL_MAX_HEIGHT,
            overflow: 'hidden',
          }}
        >
          <Box sx={{ position: 'relative', flex: '1 1 auto', minHeight: 0, overflow: 'auto' }}>
            {listLoading && <LinearProgress sx={{ position: 'absolute', top: 0, left: 0, right: 0, zIndex: 2 }} />}
            <Table
              stickyHeader
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
                <TableCell
                  padding="checkbox"
                  sx={{
                    ...selectColSx,
                    ...headerCellTextSx,
                    verticalAlign: 'bottom',
                    borderBottom: (t) => `1px solid ${t.palette.divider}`,
                  }}
                >
                  <Checkbox
                    size="small"
                    disabled={selectableRowIds.length === 0}
                    checked={headerBulkCheckboxProps.checked}
                    indeterminate={headerBulkCheckboxProps.indeterminate}
                    onChange={toggleSelectAllOnPage}
                    inputProps={{ 'aria-label': 'Sélectionner toutes les factures de la page' }}
                  />
                </TableCell>
                {resizableOrder.map((colKey, idx) => {
                  const last = idx === nDataCols - 1
                  const d = tableView?.definition?.find((c) => c.key === colKey)
                  const sortable = d ? d.sortable !== false : true
                  return (
                    <ResizableHeaderCell
                      key={colKey}
                      width={fullWidths[colKey]}
                      onWidthChange={setColWidth(colKey)}
                      minWidth={INVOICE_COLUMN_MIN_PX[colKey] ?? 64}
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
                <TableCell
                  padding="checkbox"
                  sx={{
                    ...selectColSx,
                    verticalAlign: 'top',
                    py: 0.75,
                    borderBottom: (t) => `1px solid ${t.palette.divider}`,
                  }}
                />
                {resizableOrder.map((colKey) => (
                  <InvoiceFilterCell
                    key={`f-${colKey}`}
                    columnKey={colKey}
                    fullWidths={fullWidths}
                    filters={filters}
                    onChange={handleFilterChange}
                    definition={tableView?.definition}
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
                    whiteSpace: 'nowrap',
                  }}
                />
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.length === 0 && !listLoading && (
                <TableRow>
                  <TableCell colSpan={nDataCols + 2} align="center">
                    <Typography color="textSecondary" py={2}>
                      Aucune facture
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
              {rows.map((inv) => (
                <TableRow
                  key={inv.id}
                  hover
                  selected={selectedInvoiceIds.has(inv.id)}
                  onDoubleClick={() => navigateToPharmacy(inv.pharmacy_id)}
                  sx={{ cursor: 'pointer' }}
                >
                  <TableCell
                    padding="checkbox"
                    sx={selectColSx}
                    onClick={(e) => e.stopPropagation()}
                    onDoubleClick={(e) => e.stopPropagation()}
                  >
                    <Checkbox
                      size="small"
                      disabled={inv.row_kind === 'credit_note'}
                      checked={selectedInvoiceIds.has(inv.id)}
                      onChange={() => toggleSelectRow(inv.id)}
                      inputProps={{
                        'aria-label': `Sélectionner la facture ${inv.invoice_number || inv.id}`,
                      }}
                    />
                  </TableCell>
                  {resizableOrder.map((colKey) => (
                    <InvoiceTableBodyCell
                      key={`${inv.id}-${colKey}`}
                      columnKey={colKey}
                      invoice={inv}
                      fullWidths={fullWidths}
                      ctx={bodyCtx}
                    />
                  ))}
                  <InvoiceActionsCell invoice={inv} fullWidths={fullWidths} ctx={bodyCtx} />
                </TableRow>
              ))}
            </TableBody>
          </Table>
          </Box>
          <TablePagination
            sx={{ flexShrink: 0, borderTop: 1, borderColor: 'divider' }}
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
        </Paper>
      </Box>

      <IssueTotalCreditNoteDialog
        open={creditNoteTargetInvoice != null}
        invoice={creditNoteTargetInvoice ?? undefined}
        onClose={() => setCreditNoteTargetInvoice(null)}
        onSuccess={() => void loadData()}
      />

      <MarkInvoicePaidDialog
        open={markPaidTargetInvoice != null}
        invoice={markPaidTargetInvoice ?? undefined}
        onClose={() => setMarkPaidTargetInvoice(null)}
        onSuccess={() => void loadData()}
      />

      <SendEmailComposerDialog
        open={invEmailOpen}
        title="Envoyer la facture par e-mail"
        onClose={handleCloseInvEmailComposer}
        draftLoading={invEmailDraftLoading}
        draftError={invEmailDraftError}
        draft={invEmailDraft}
        onSend={handleConfirmInvoiceTableEmailSend}
        sending={invEmailSending}
        sendError={invEmailSendError}
      />

      {NotifierSnackbar}
    </Box>
  )
}

export default Invoices
