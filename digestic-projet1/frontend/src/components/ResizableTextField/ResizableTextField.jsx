import { Box, TextField } from '@mui/material'

const TIP_LIGNE =
  'Redimensionner : tirez le bord droit du cadre. Texte long : glissez le coin inférieur droit du champ.'

/**
 * TextField MUI que l’utilisateur peut élargir ou rétrécir (ou agrandir en hauteur si multiline).
 */
export function ResizableTextField({
  multiline = false,
  minRows = 3,
  boxSx,
  sx,
  size,
  inputProps,
  title = TIP_LIGNE,
  ...rest
}) {
  const { sx: restSx, ...fieldRest } = rest
  if (multiline) {
    const { label: ml, InputLabelProps: mlp, ...mRest } = fieldRest
    const mLabel = ml
      ? { shrink: true, ...mlp }
      : mlp
    return (
      <TextField
        fullWidth
        multiline
        size={size}
        title={title}
        label={ml}
        InputLabelProps={mLabel}
        inputProps={{ ...inputProps, title }}
        minRows={minRows}
        sx={{
          maxWidth: '100%',
          marginTop: '2px',
          '& .MuiInputLabel-root': { lineHeight: 1.25, paddingTop: '1px' },
          '& .MuiInputBase-root': { alignItems: 'flex-start' },
          '& .MuiInputBase-inputMultiline': {
            resize: 'vertical',
            minHeight: 72,
            maxHeight: 400,
            boxSizing: 'border-box',
          },
          ...sx,
          ...restSx,
        }}
        {...mRest}
      />
    )
  }
  // overflow: auto sur le wrapper recadrait les libellés (position absolue) — on garde le resize horizontal
  // avec marge haute + libellé « shrink » pour qu’il reste dans l’emprise du champ.
  const { label, InputLabelProps: inProps, ...otherField } = fieldRest
  const mergedInputLabel = label
    ? { shrink: true, ...inProps }
    : inProps
  return (
    <Box
      title={title}
      sx={{
        display: 'inline-block',
        width: '100%',
        minWidth: 100,
        maxWidth: '100%',
        resize: 'horizontal',
        overflow: 'auto',
        boxSizing: 'border-box',
        verticalAlign: 'top',
        // Réserve l’espace au-dessus du TextField (évite la coupe du haut des libellés)
        paddingTop: '8px',
        paddingBottom: 0.5,
        ...boxSx,
      }}
    >
      <TextField
        fullWidth
        size={size}
        label={label}
        InputLabelProps={mergedInputLabel}
        inputProps={{ ...inputProps, title }}
        sx={{
          minWidth: 0,
          '& .MuiInputLabel-root': { lineHeight: 1.25, paddingTop: '1px' },
          ...sx,
          ...restSx,
        }}
        {...otherField}
      />
    </Box>
  )
}

export default ResizableTextField
