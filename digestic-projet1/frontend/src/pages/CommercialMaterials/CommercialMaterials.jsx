import React, { useEffect, useState } from 'react'
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  CircularProgress,
  Chip,
} from '@mui/material'
import DescriptionIcon from '@mui/icons-material/Description'
import { commercialMaterialService } from '../../services/commercialMaterialService'

function CommercialMaterials() {
  const [materials, setMaterials] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMaterials()
  }, [])

  const fetchMaterials = async () => {
    try {
      setLoading(true)
      const data = await commercialMaterialService.getAll(true)
      setMaterials(data)
    } catch (error) {
      console.error('Error fetching materials:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Supports Commerciaux
      </Typography>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        {materials.map((material) => (
          <Grid item xs={12} sm={6} md={4} key={material.id}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: 4,
                },
              }}
            >
              <CardContent sx={{ flexGrow: 1 }}>
                <Box display="flex" alignItems="center" gap={2} mb={2}>
                  <DescriptionIcon sx={{ fontSize: 40, color: '#1976d2' }} />
                  <Box>
                    <Typography variant="h6">{material.name}</Typography>
                    <Chip
                      label={material.type}
                      size="small"
                      sx={{ mt: 1 }}
                    />
                  </Box>
                </Box>
                {material.description && (
                  <Typography variant="body2" color="text.secondary">
                    {material.description}
                  </Typography>
                )}
                <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
                  Version: {material.version}
                </Typography>
              </CardContent>
              <CardActions>
                {material.file_url && (
                  <Button size="small" href={material.file_url} target="_blank">
                    Télécharger
                  </Button>
                )}
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}

export default CommercialMaterials


