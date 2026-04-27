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
  Tabs,
  Tab,
} from '@mui/material'
import ViewColumnIcon from '@mui/icons-material/ViewColumn'
import { format } from 'date-fns'
import { invoiceService } from '../../services/invoiceService'
import { fetchInvoiceTableView, saveInvoiceTableView } from '../../services/tableViewService'
import { ResizableHeaderCell } from '../../components/ResizableTableColumns/ResizableHeaderCell'
import InvoiceColumnPickerDialog from '../../components/InvoiceTable/InvoiceColumnPickerDialog'
import { InvoiceTableBodyCell, InvoiceActionsCell } from '../../components/InvoiceTable/InvoiceDataCells'
import { InvoiceFilterCell } from '../../components/InvoiceTable/InvoiceFilterCells'
import { InvoiceSavedFiltersBar } from '../../components/InvoiceTable/InvoiceSavedFiltersBar'
import {
  EMPTY_INVOICE_FILTERS,
  buildInvoiceListQueryParams,
  getInitialInvoiceFiltersState,
  invoiceFiltersFromPayload,
  parsePharmacyFilterFromSearchParams,
} from '../../utils/invoiceListQueryParams'
import {
  computeResizablePixelWidths,
  defaultEqualFractions,
  loadInvoiceColumnWidths,
  saveInvoiceColumnWidths,
  INVOICE_COLUMN_MIN_PX,
  INVOICE_TABLE_ACTIONS_PX,
} from '../../utils/invoiceTableLayoutUtils'

const headerCellTextSx = { fontSize: '0.75rem', fontWeight: 600 }

const DEFAULT_VISIBLE_COLUMNS = [
  'invoiceNumber',
  'pharmacyName',
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
  if (f.invoiceNumber || f.pharmacyName || f.pharmacyId || f.status) {
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
  const tableWidthRef = useRef(1200)
  const colResizeObserverRef = useRef(null)
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

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
    if (colWidthsPx) {
      const sum = resizableOrder.reduce((a, k) => a + (colWidthsPx[k] || 0), 0)
      const tmin = sum + A
      return {
        fullWidths: { ...colWidthsPx, actions: A },
        tableMinW: Math.max(W, tmin),
      }
    }
    const frac = defaultEqualFractions(resizableOrder)
    const o = computeResizablePixelWidths(frac, w, INVOICE_COLUMN_MIN_PX, resizableOrder, A)
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

  const canDownloadVosFacturesPdf = (inv) =>
    inv.external_provider === 'vosfactures' && Boolean(inv.external_invoice_id)

  const handleDownloadPdf = async (inv) => {
    try {
      setPdfLoadingId(inv.id)
      await invoiceService.downloadVosFacturesPdf(inv.id)
    } catch (e) {
      console.error('PDF facture:', e)
      // eslint-disable-next-line no-alert
      alert(e.message || 'Impossible de télécharger le PDF')
    } finally {
      setPdfLoadingId(null)
    }
  }

  const bodyCtx = useMemo(
    () => ({
      formatDate,
      canDownloadVosFacturesPdf,
      handleDownloadPdf,
      pdfLoadingId,
      navigate,
    }),
    [navigate, pdfLoadingId],
  )

  useEffect(() => {
    const stored = localStorage.getItem('user')
    if (stored) {
      setUser(JSON.parse(stored))
    }
  }, [])

  /** Navigation interne (ex. autre pharmacie) : sync query string → filtres */
  useEffect(() => {
    const extra = parsePharmacyFilterFromSearchParams(searchParams)
    if (!extra) {
      return
    }
    setPage(0)
    setTab(0)
    setActiveSavedFilterId(null)
    setFilters((prev) => ({ ...prev, ...extra }))
    setDebouncedFilters((prev) => ({ ...prev, ...extra }))
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
      setOrderBy(pl.orderBy)
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
      // eslint-disable-next-line no-alert
      alert(e?.response?.data?.error || e.message || 'Erreur de sauvegarde')
    } finally {
      setSavingColumns(false)
    }
  }

  const hasFilterBar = hasDirtyFilters(tab, filters)
  const nDataCols = resizableOrder.length
  const zBase = 20

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
                  PDF
                </ResizableHeaderCell>
              </TableRow>
              <TableRow>
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
                  <TableCell colSpan={nDataCols + 1} align="center">
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
                  onDoubleClick={() => navigate(`/pharmacies/${inv.pharmacy_id}`)}
                  sx={{ cursor: 'pointer' }}
                >
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
    </Box>
  )
}

export default Invoices
