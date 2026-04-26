import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  TableSortLabel,
  TablePagination,
  LinearProgress,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import VisibilityIcon from '@mui/icons-material/Visibility'
import DeleteIcon from '@mui/icons-material/Delete'
import ViewColumnIcon from '@mui/icons-material/ViewColumn'
import { format } from 'date-fns'
import { pharmacyService, fetchPharmacyDistinctCities } from '../../services/pharmacyService'
import { userService } from '../../services/userService'
import { depotService } from '../../services/depotService'
import { fetchPharmacyTableView, savePharmacyTableView } from '../../services/tableViewService'
import PharmacyForm from '../../components/PharmacyForm/PharmacyForm'
import { ResizableHeaderCell } from '../../components/ResizableTableColumns/ResizableHeaderCell'
import PharmacyColumnPickerDialog from '../../components/PharmacyTable/PharmacyColumnPickerDialog'
import { PharmacyTableBodyCell } from '../../components/PharmacyTable/PharmacyDataCells'
import { PharmacyFilterCell } from '../../components/PharmacyTable/PharmacyFilterCells'
import { PharmacySavedFiltersBar } from '../../components/PharmacyTable/PharmacySavedFiltersBar'
import { PHARMACY_COLUMN_MIN_PX, PHARM_TABLE_ACTIONS_PX } from '../../constants/pharmacyTableMinWidths'
import {
  EMPTY_PHARMACY_FILTERS,
  buildPharmacyListQueryParams,
  pharmacyFiltersFromPayload,
} from '../../utils/pharmacyListQueryParams'
import {
  computeResizablePixelWidths,
  defaultEqualFractions,
  loadColumnWidthsPx,
  saveColumnWidthsPx,
} from '../../utils/pharmacyTableLayoutUtils'

const headerCellTextSx = { fontSize: '0.75rem', fontWeight: 600 }

const DEFAULT_VISIBLE_COLUMNS = [
  'name',
  'address',
  'city',
  'commercial',
  'lastVisit',
  'nextVisit',
  'status',
  'rib',
]

function Pharmacies() {
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [listLoading, setListLoading] = useState(true)
  const [openForm, setOpenForm] = useState(false)
  const [editingPharmacy, setEditingPharmacy] = useState(null)
  const [orderBy, setOrderBy] = useState('name')
  const [order, setOrder] = useState('asc')
  const [commercials, setCommercials] = useState([])
  const [depots, setDepots] = useState([])
  const [cityOptions, setCityOptions] = useState([])
  const [user, setUser] = useState(null)
  const [filters, setFilters] = useState(() => ({ ...EMPTY_PHARMACY_FILTERS }))
  const [debouncedFilters, setDebouncedFilters] = useState(() => ({
    ...EMPTY_PHARMACY_FILTERS,
  }))
  const [editingNextVisitId, setEditingNextVisitId] = useState(null)
  const [editingNextVisitValue, setEditingNextVisitValue] = useState('')
  const [shouldSaveOnBlur, setShouldSaveOnBlur] = useState(true)
  const [colWidthsPx, setColWidthsPx] = useState(null)
  const [tableWidth, setTableWidth] = useState(0)
  const [tableView, setTableView] = useState(null)
  const [columnPickerOpen, setColumnPickerOpen] = useState(false)
  const [savingColumns, setSavingColumns] = useState(false)
  const [activeSavedFilterId, setActiveSavedFilterId] = useState(null)
  const tableWidthRef = useRef(1200)
  const colResizeObserverRef = useRef(null)
  const navigate = useNavigate()

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
    if (colWidthsPx) {
      const sum = resizableOrder.reduce((a, k) => a + (colWidthsPx[k] || 0), 0)
      const tmin = sum + PHARM_TABLE_ACTIONS_PX
      return {
        fullWidths: { ...colWidthsPx, actions: PHARM_TABLE_ACTIONS_PX },
        tableMinW: Math.max(W, tmin),
      }
    }
    const frac = defaultEqualFractions(resizableOrder)
    const o = computeResizablePixelWidths(frac, w, PHARMACY_COLUMN_MIN_PX, resizableOrder)
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
      const minB = PHARMACY_COLUMN_MIN_PX[b] ?? 64
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
        const minA = PHARMACY_COLUMN_MIN_PX[a] ?? 64
        const minB = PHARMACY_COLUMN_MIN_PX[b] ?? 64
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
    const saved = loadColumnWidthsPx(resizableOrder)
    if (saved && resizableOrder.length) {
      const s0 = resizableOrder.reduce((a, k) => a + (saved[k] || 0), 0)
      if (s0 < 1) {
        setColWidthsPx(
          computeResizablePixelWidths(
            defaultEqualFractions(resizableOrder),
            W,
            PHARMACY_COLUMN_MIN_PX,
            resizableOrder,
          ).colWidths,
        )
        return
      }
      const frac = Object.fromEntries(
        resizableOrder.map((k) => [k, (saved[k] || 0) / s0]),
      )
      setColWidthsPx(computeResizablePixelWidths(frac, W, PHARMACY_COLUMN_MIN_PX, resizableOrder).colWidths)
    } else {
      setColWidthsPx(
        computeResizablePixelWidths(
          defaultEqualFractions(resizableOrder),
          W,
          PHARMACY_COLUMN_MIN_PX,
          resizableOrder,
        ).colWidths,
      )
    }
  }, [tableWidth, colWidthsPx, resizableKeyStr, resizableOrder])

  useEffect(() => {
    if (!colWidthsPx || !resizableOrder.length) {
      return
    }
    saveColumnWidthsPx(resizableOrder, colWidthsPx)
  }, [colWidthsPx, resizableKeyStr, resizableOrder])

  const getPhotoPreviewUrl = (pharmacy, size = 120) => {
    const seed = encodeURIComponent(pharmacy.id ?? pharmacy.name ?? 'pharmacy-photo')
    return pharmacy.photo_url || `https://picsum.photos/seed/${seed}/${size}/${size}`
  }

  useEffect(() => {
    const storedUser = localStorage.getItem('user')
    if (storedUser) {
      setUser(JSON.parse(storedUser))
    }
  }, [])

  useEffect(() => {
    let c = true
    ;(async () => {
      try {
        const d = await fetchPharmacyTableView()
        if (c) {
          setTableView(d)
        }
      } catch (e) {
        console.error(e)
        if (c) {
          setTableView({
            viewKey: 'pharmacies',
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
      const data = await pharmacyService.getList(
        buildPharmacyListQueryParams({
          page,
          rowsPerPage,
          orderBy,
          order,
          debouncedFilters,
        }),
      )
      setRows(
        (data.items || []).map((p) => ({
          ...p,
          lastVisitDate: p.last_visit_at,
          nextVisitDate: p.next_visit_date,
        })),
      )
      setTotal(data.total ?? 0)
    } catch (error) {
      console.error('Error fetching pharmacies:', error)
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
    const loadCommercials = async () => {
      try {
        const data = await userService.getAll('commercial')
        setCommercials(data || [])
      } catch (error) {
        console.error('Erreur lors du chargement des commerciaux:', error)
      }
    }
    const loadDepots = async () => {
      try {
        const data = await depotService.list()
        const list = Array.isArray(data) ? data : []
        list.sort((a, b) => (a.name || '').localeCompare(b.name || '', 'fr'))
        setDepots(list)
      } catch (error) {
        console.error('Erreur lors du chargement des dépôts:', error)
        setDepots([])
      }
    }
    void loadCommercials()
    void loadDepots()
  }, [])

  useEffect(() => {
    let c = true
    ;(async () => {
      try {
        const list = await fetchPharmacyDistinctCities()
        if (c) {
          setCityOptions(Array.isArray(list) ? list : [])
        }
      } catch (e) {
        console.error(e)
        if (c) {
          setCityOptions([])
        }
      }
    })()
    return () => {
      c = false
    }
  }, [])

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

  const handleNextVisitClick = useCallback((ph) => {
    setEditingNextVisitId(ph.id)
    const dateValue = ph.nextVisitDate
      ? format(new Date(ph.nextVisitDate), 'yyyy-MM-dd')
      : ''
    setEditingNextVisitValue(dateValue)
    setShouldSaveOnBlur(true)
  }, [])

  const handleNextVisitChange = useCallback((e) => {
    setEditingNextVisitValue(e.target.value)
  }, [])

  const handleNextVisitSave = useCallback(
    async (pharmacyId) => {
      if (!shouldSaveOnBlur) {
        setShouldSaveOnBlur(true)
        return
      }
      try {
        let isoDate = null
        if (editingNextVisitValue) {
          const d = new Date(editingNextVisitValue)
          d.setHours(0, 0, 0, 0)
          isoDate = d.toISOString()
        }
        await pharmacyService.update(pharmacyId, { next_visit_date: isoDate })
        setEditingNextVisitId(null)
        setEditingNextVisitValue('')
        setShouldSaveOnBlur(true)
        void loadData()
      } catch (error) {
        console.error('Erreur lors de la mise à jour de la date:', error)
        alert('Erreur lors de la mise à jour de la date de prochaine visite')
        setEditingNextVisitId(null)
        setEditingNextVisitValue('')
      }
    },
    [shouldSaveOnBlur, editingNextVisitValue, loadData],
  )

  const handleNextVisitKeyDown = useCallback(
    (e, pharmacyId) => {
      if (e.key === 'Enter') {
        void handleNextVisitSave(pharmacyId)
      } else if (e.key === 'Escape') {
        setEditingNextVisitId(null)
        setEditingNextVisitValue('')
      }
    },
    [handleNextVisitSave],
  )

  const bodyCtx = useMemo(
    () => ({
      getPhotoPreviewUrl,
      formatDate,
      editingNextVisitId,
      editingNextVisitValue,
      handleNextVisitClick,
      handleNextVisitChange,
      handleNextVisitSave,
      handleNextVisitKeyDown,
      setShouldSaveOnBlur,
      setEditingNextVisitValue,
    }),
    [
      editingNextVisitId,
      editingNextVisitValue,
      handleNextVisitClick,
      handleNextVisitChange,
      handleNextVisitSave,
      handleNextVisitKeyDown,
    ],
  )

  const handleCreate = () => {
    setEditingPharmacy(null)
    setOpenForm(true)
  }

  const handleEdit = (pharmacy) => {
    setEditingPharmacy(pharmacy)
    setOpenForm(true)
  }

  const handleFormClose = () => {
    setOpenForm(false)
    setEditingPharmacy(null)
    void loadData()
  }

  const handleDelete = async (pharmacy) => {
    if (window.confirm(`Êtes-vous sûr de vouloir supprimer la pharmacie "${pharmacy.name}" ?`)) {
      try {
        await pharmacyService.delete(pharmacy.id)
        void loadData()
      } catch (error) {
        console.error('Error deleting pharmacy:', error)
        alert('Erreur lors de la suppression de la pharmacie')
      }
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
    setFilters((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const handleSelectSavedFilter = useCallback((item) => {
    setPage(0)
    const pl = item.payload || {}
    const next = pharmacyFiltersFromPayload(pl.filters)
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
    setFilters({ ...EMPTY_PHARMACY_FILTERS })
    setDebouncedFilters({ ...EMPTY_PHARMACY_FILTERS })
  }

  const hasActiveFilters = Object.values(filters).some((v) =>
    Array.isArray(v) ? v.length > 0 : v !== '',
  )

  const onSaveColumnPicker = async (keys) => {
    setSavingColumns(true)
    try {
      const res = await savePharmacyTableView(keys)
      setTableView((prev) => ({
        ...prev,
        visibleColumnKeys: res.visibleColumnKeys,
      }))
      setColWidthsPx(null)
      setColumnPickerOpen(false)
    } catch (e) {
      console.error(e)
      alert(e?.response?.data?.error || e.message || 'Erreur de sauvegarde')
    } finally {
      setSavingColumns(false)
    }
  }

  const nDataCols = resizableOrder.length
  const zBase = 20

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Pharmacies</Typography>
        <Box display="flex" gap={2} flexWrap="wrap" justifyContent="flex-end">
          {hasActiveFilters && (
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
          {user?.role === 'admin' && (
            <Button variant="contained" startIcon={<AddIcon />} onClick={handleCreate}>
              Nouvelle Pharmacie
            </Button>
          )}
        </Box>
      </Box>

      {user && (
        <PharmacySavedFiltersBar
          filters={filters}
          orderBy={orderBy}
          order={order}
          activeSavedFilterId={activeSavedFilterId}
          onSelectSaved={handleSelectSavedFilter}
          onActiveFilterRemoved={() => setActiveSavedFilterId(null)}
        />
      )}

      {user?.role === 'admin' && tableView && (
        <PharmacyColumnPickerDialog
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
                  return (
                    <ResizableHeaderCell
                      key={colKey}
                      width={fullWidths[colKey]}
                      onWidthChange={setColWidth(colKey)}
                      minWidth={PHARMACY_COLUMN_MIN_PX[colKey] ?? 64}
                      maxWidth={getPairMaxW(colKey)}
                      resizable={!last}
                      stackZIndex={zBase - idx}
                      sx={headerCellTextSx}
                    >
                      <TableSortLabel
                        active={orderBy === colKey}
                        direction={orderBy === colKey ? order : 'asc'}
                        onClick={() => handleSort(colKey)}
                      >
                        {getColumnLabel(colKey)}
                      </TableSortLabel>
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
                  <PharmacyFilterCell
                    key={`f-${colKey}`}
                    columnKey={colKey}
                    fullWidths={fullWidths}
                    filters={filters}
                    onChange={handleFilterChange}
                    commercials={commercials}
                    depots={depots}
                    cityOptions={cityOptions}
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
                      Aucune pharmacie
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
              {rows.map((pharmacy) => (
                <TableRow
                  key={pharmacy.id}
                  hover
                  onDoubleClick={() => navigate(`/pharmacies/${pharmacy.id}`)}
                  sx={{ cursor: 'pointer' }}
                >
                  {resizableOrder.map((colKey) => (
                    <PharmacyTableBodyCell
                      key={`${pharmacy.id}-${colKey}`}
                      columnKey={colKey}
                      pharmacy={pharmacy}
                      fullWidths={fullWidths}
                      ctx={bodyCtx}
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
                      whiteSpace: 'nowrap',
                    }}
                  >
                    <Box
                      sx={{
                        display: 'flex',
                        justifyContent: 'flex-end',
                        flexWrap: 'nowrap',
                        gap: 0,
                        px: 1,
                        py: 0.5,
                      }}
                    >
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation()
                          navigate(`/pharmacies/${pharmacy.id}`)
                        }}
                      >
                        <VisibilityIcon />
                      </IconButton>
                      {user?.role === 'admin' && (
                        <>
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleEdit(pharmacy)
                            }}
                          >
                            <EditIcon />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDelete(pharmacy)
                            }}
                            color="error"
                          >
                            <DeleteIcon />
                          </IconButton>
                        </>
                      )}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <TablePagination
            component="div"
            count={total}
            page={page}
            onPageChange={(_, newPage) => setPage(newPage)}
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

      <PharmacyForm open={openForm} onClose={handleFormClose} pharmacy={editingPharmacy} />
    </Box>
  )
}

export default Pharmacies
