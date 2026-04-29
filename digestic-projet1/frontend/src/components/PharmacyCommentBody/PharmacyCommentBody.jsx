import React, { useMemo } from 'react'
import { Box, Typography } from '@mui/material'

const RE_AUDIO = /^Note audio\s*:\s*(.+)$/i
const RE_PHOTO = /^Note photo\s*:\s*(.+)$/i
const RE_VIDEO = /^Note vidéo\s*:\s*(.+)$/i

/**
 * Affiche le texte d'un commentaire ; les lignes issues d'un rapport de visite
 * (note audio / photo / vidéo) sont rendues comme sur le détail du rapport.
 */
function commentToSegments(text) {
  const raw = (text || '').split('\n')
  const out = []
  let textBuf = []
  const flushText = () => {
    if (textBuf.length) {
      out.push({ type: 'text', value: textBuf.join('\n') })
      textBuf = []
    }
  }
  for (const line of raw) {
    const am = line.match(RE_AUDIO)
    const pm = line.match(RE_PHOTO)
    const vm = line.match(RE_VIDEO)
    if (am) {
      flushText()
      out.push({ type: 'audio', url: am[1].trim() })
    } else if (pm) {
      flushText()
      out.push({ type: 'photo', url: pm[1].trim() })
    } else if (vm) {
      flushText()
      out.push({ type: 'video', url: vm[1].trim() })
    } else {
      textBuf.push(line)
    }
  }
  flushText()
  return out
}

export default function PharmacyCommentBody({ text }) {
  const segments = useMemo(() => commentToSegments(text), [text])

  return (
    <Box component="span" sx={{ display: 'block' }}>
      {segments.map((seg, i) => {
        if (seg.type === 'text') {
          return (
            <Typography
              key={i}
              component="span"
              variant="body2"
              color="text.primary"
              sx={{ whiteSpace: 'pre-wrap', display: 'block' }}
            >
              {seg.value}
            </Typography>
          )
        }
        if (seg.type === 'audio') {
          return (
            <Box key={i} sx={{ my: 1 }}>
              <Typography variant="caption" color="text.secondary" display="block">
                Audio
              </Typography>
              <audio controls src={seg.url} style={{ display: 'block', maxWidth: '100%' }} />
            </Box>
          )
        }
        if (seg.type === 'photo') {
          return (
            <Box key={i} sx={{ my: 1 }}>
              <Typography variant="caption" color="text.secondary" display="block">
                Photo
              </Typography>
              <Box
                component="img"
                src={seg.url}
                alt="Note photo"
                sx={{ maxHeight: 160, display: 'block', maxWidth: '100%' }}
              />
            </Box>
          )
        }
        if (seg.type === 'video') {
          return (
            <Box key={i} sx={{ my: 1 }}>
              <Typography variant="caption" color="text.secondary" display="block">
                Vidéo
              </Typography>
              <video
                src={seg.url}
                controls
                style={{ display: 'block', maxWidth: '100%', maxHeight: 220 }}
              />
            </Box>
          )
        }
        return null
      })}
    </Box>
  )
}
