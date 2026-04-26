import React, { useLayoutEffect, useRef } from 'react'
import { Box, TableCell } from '@mui/material'
import { alpha } from '@mui/material/styles'

const clamp = (v, a, b) => Math.max(a, Math.min(b, v))

const num = (x, fallback) => {
  const n = Number(x)
  return Number.isFinite(n) ? n : fallback
}

/** Espace réservé à droite (ligne + alignement) — identique pour toutes les colonnes. */
const RIGHT_GUTTER_PX = 6
/** Zone réelle de capture du drag (souris) — plus fine que toute la zone visuelle. */
const RESIZE_HIT_PX = 4
const LINE_INSET_FROM_RIGHT = 3

/**
 * En-tête : poignée à droite pour redimensionner.
 * Drag = mousedown (window mousemove / mouseup) : évite pointerId / passive / capture incompatibles.
 * `resizable={false}` : même aspect de séparateur, sans redimensionnement (ex. RIB, Actions).
 */
export function ResizableHeaderCell({
  width,
  onWidthChange = () => {},
  minWidth: minW = 64,
  maxWidth: maxW = 800,
  /** @deprecated utiliser resizable + showRightSeparator */
  showResizeHandle,
  resizable: resizableProp,
  showRightSeparator = true,
  stackZIndex = 1,
  children,
  sx: sxProps,
  ...tableCellProps
}) {
  const resizable =
    resizableProp !== undefined
      ? resizableProp
      : showResizeHandle === false
        ? false
        : true
  const rightGutter = showRightSeparator ? RIGHT_GUTTER_PX : 0
  const w = num(width, minW)
  const maxWNum = num(maxW, 8000)
  const maxSafe = Math.max(maxWNum, minW)
  const onWidthChangeRef = useRef(onWidthChange)
  const widthRef = useRef(w)
  const minRef = useRef(minW)
  const maxRef = useRef(maxSafe)

  useLayoutEffect(() => {
    onWidthChangeRef.current = onWidthChange
  }, [onWidthChange])
  useLayoutEffect(() => {
    widthRef.current = w
    minRef.current = minW
    maxRef.current = maxSafe
  }, [w, minW, maxSafe])

  const handleRef = useRef(null)
  const dragRef = useRef({ move: null, up: null })
  const onMouseDownRef = useRef((e) => {})

  onMouseDownRef.current = (e) => {
    if (e.button !== 0) {
      return
    }
    e.preventDefault()
    e.stopPropagation()
    if (e.stopImmediatePropagation) {
      e.stopImmediatePropagation()
    }

    const startX = e.clientX
    const startW0 = widthRef.current
    const startMin = minRef.current
    const startMax = maxRef.current

    const onMove = (ev) => {
      const next = Math.round(
        clamp(
          startW0 + (ev.clientX - startX),
          startMin,
          startMax,
        ),
      )
      onWidthChangeRef.current(next)
    }

    const onUp = () => {
      const d = dragRef.current
      if (d.move) {
        window.removeEventListener('mousemove', d.move, true)
      }
      if (d.up) {
        window.removeEventListener('mouseup', d.up, true)
      }
      dragRef.current = { move: null, up: null }
      document.body.style.removeProperty('cursor')
      document.body.style.removeProperty('user-select')
    }

    dragRef.current = { move: onMove, up: onUp }
    window.addEventListener('mousemove', onMove, true)
    window.addEventListener('mouseup', onUp, true)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  useLayoutEffect(() => {
    const el = handleRef.current
    if (!el || !resizable) {
      return
    }
    const nativeDown = (e) => {
      onMouseDownRef.current(e)
    }
    el.addEventListener('mousedown', nativeDown, true)
    return () => el.removeEventListener('mousedown', nativeDown, true)
  }, [resizable])

  return (
    <TableCell
      padding="none"
      {...tableCellProps}
      sx={{
        position: 'relative',
        width: w,
        minWidth: w,
        maxWidth: w,
        boxSizing: 'border-box',
        verticalAlign: 'center',
        overflow: 'visible',
        ...sxProps,
        zIndex: stackZIndex,
        isolation: 'isolate',
      }}
    >
      <Box
        sx={{
          pl: 2,
          pr: showRightSeparator ? `${rightGutter}px` : 2,
          py: 1.5,
          overflow: 'hidden',
          maxWidth: '100%',
          whiteSpace: 'nowrap',
          pointerEvents: 'none',
        }}
      >
        <Box
          component="div"
          sx={{
            display: 'inline-block',
            maxWidth: '100%',
            minWidth: 0,
            pointerEvents: 'auto',
            verticalAlign: 'top',
            '& .MuiTableSortLabel-root': {
              maxWidth: '100%',
              minWidth: 0,
            },
          }}
        >
          {children}
        </Box>
      </Box>
      {showRightSeparator && (
        <Box
          aria-hidden
          className="column-sep-wrap"
          sx={(theme) => ({
            position: 'absolute',
            right: 0,
            top: 0,
            bottom: 0,
            width: rightGutter,
            zIndex: 2,
            pointerEvents: 'none',
            // Ligne : fine, légèrement raccourcie, même rendu partout
            '&::before': {
              content: '""',
              position: 'absolute',
              right: LINE_INSET_FROM_RIGHT,
              top: 10,
              bottom: 10,
              width: 1,
              borderRadius: 0.5,
              backgroundColor: alpha(theme.palette.text.primary, 0.1),
              boxShadow: `1px 0 0 0 ${alpha(theme.palette.text.primary, 0.04)}`,
              transition: theme.transitions.create(
                ['background-color', 'box-shadow', 'top', 'bottom'],
                { duration: theme.transitions.duration.shorter },
              ),
            },
            ...(resizable && {
              '&:has(> *:hover)::before': {
                backgroundColor: alpha(theme.palette.primary.main, 0.65),
                boxShadow: `0 0 0 1px ${alpha(theme.palette.primary.main, 0.2)}, 0 0 8px ${alpha(theme.palette.primary.main, 0.2)}`,
                top: 6,
                bottom: 6,
              },
            }),
          })}
        >
          {resizable && (
            <Box
              ref={handleRef}
              component="div"
              role="separator"
              aria-orientation="vertical"
              aria-label="Redimensionner la colonne"
              title="Redimensionner (glisser)"
              sx={{
                position: 'absolute',
                right: 0,
                top: 0,
                bottom: 0,
                width: RESIZE_HIT_PX,
                cursor: 'col-resize',
                touchAction: 'none',
                userSelect: 'none',
                pointerEvents: 'auto',
                boxSizing: 'border-box',
                background: 'none',
                border: 'none',
                padding: 0,
              }}
            />
          )}
        </Box>
      )}
    </TableCell>
  )
}

export function AlignedTableCell({ width, children, dense = false, contentSx, sx: sxProps, ...rest }) {
  const w = num(width, 100)
  return (
    <TableCell
      padding="none"
      {...rest}
      sx={{
        width: w,
        minWidth: w,
        maxWidth: w,
        boxSizing: 'border-box',
        ...sxProps,
      }}
    >
      <Box
        sx={{
          // pl: 2 aligné sur l’en-tête. pr: 2 (16px) : la ligne filtres ne doit pas coller le champ
          // au filet (le gutter 6px seul était trop juste à droite du rectangle).
          pl: 2,
          pr: 2,
          py: dense ? 0.75 : 1.5,
          overflow: 'hidden',
          ...contentSx,
        }}
      >
        {children}
      </Box>
    </TableCell>
  )
}
