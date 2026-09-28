import React, { useState, useEffect } from 'react'
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material'
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'
import api from '../services/api'

const Settings = () => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [thresholds, setThresholds] = useState({
    warning_threshold: 2,
    danger_threshold: 3,
  })
  const [systemSettings, setSystemSettings] = useState({})

  useEffect(() => {
    fetchThresholds()
    fetchSystemSettings()
  }, [])

  const fetchThresholds = async () => {
    try {
      console.log('Fetching flood thresholds...')
      const response = await api.get('/api/settings/flood-thresholds/')
      console.log('Thresholds response:', response.data)
      setThresholds(response.data)
      setError(null)
    } catch (err) {
      console.error('Thresholds fetch error:', err)
      setError('Failed to fetch flood thresholds')
    } finally {
      setLoading(false)
    }
  }

  const fetchSystemSettings = async () => {
    try {
      console.log('Fetching system settings...')
      const response = await api.get('/api/settings/')
      console.log('Settings response:', response.data)
      const settings = {}
      const rows = response.data.results || response.data
      rows.forEach(setting => {
        settings[setting.key] = setting.value
      })
      if (settings.sensor_check_interval && !settings.reading_interval) {
        settings.reading_interval = settings.sensor_check_interval
      }
      settings.reading_interval = settings.reading_interval || '30'
      settings.sync_interval = settings.sync_interval || '60'
      settings.max_sms_per_hour = settings.max_sms_per_hour || '100'
      setSystemSettings(settings)
    } catch (err) {
      console.error('Failed to fetch system settings:', err)
    }
  }

  const handleSystemSettingChange = (key, value) => {
    setSystemSettings({
      ...systemSettings,
      [key]: value
    })
  }

  const handleSaveSystemSettings = async () => {
    try {
      const numericKeys = ['reading_interval', 'sync_interval', 'max_sms_per_hour']
      const valuesToSave = {
        ...systemSettings,
        reading_interval: systemSettings.reading_interval || '30',
        sync_interval: systemSettings.sync_interval || '60',
        max_sms_per_hour: systemSettings.max_sms_per_hour || '100',
      }
      if (numericKeys.some((key) => !Number.isFinite(Number(valuesToSave[key])) || Number(valuesToSave[key]) < 1)) {
        setError('Intervals and SMS limits must be positive numbers')
        return
      }
      const keysToSave = ['sms_enabled', 'ai_prediction_enabled', ...numericKeys]
      await Promise.all(keysToSave.map((key) => (
        api.put(`/api/settings/key/${key}/update/`, { value: String(valuesToSave[key]) })
      )))
      await fetchSystemSettings()
      setSuccess('System settings saved successfully')
      setError(null)
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError('Failed to update system settings')
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
        Settings
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Configure system parameters and flood thresholds
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      <Grid container spacing={3} sx={{ mt: 2 }}>
        {/* Flood Thresholds */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Flood Thresholds (4 cm Sensor)
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Based on the installed sensor calibration: raw ADC 0-600 maps to 0-4 cm.
              </Typography>
              <Box sx={{ mt: 2 }}>
                <TextField
                  fullWidth
                  label="Warning Starts (cm)"
                  type="number"
                  value={thresholds.warning_threshold}
                  InputProps={{ readOnly: true }}
                  sx={{ mb: 2 }}
                  helperText="ADC 300 of 600 = 2.0 cm"
                />
                <TextField
                  fullWidth
                  label="Critical / Danger Starts (cm)"
                  type="number"
                  value={thresholds.danger_threshold}
                  InputProps={{ readOnly: true }}
                  sx={{ mb: 2 }}
                  helperText="ADC 450 of 600 = 3.0 cm"
                />
                <Typography variant="body2">Normal: below 2.0 cm</Typography>
                <Typography variant="body2">Warning: 2.0 cm to below 3.0 cm</Typography>
                <Typography variant="body2">Critical / Danger: 3.0 cm and above</Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* System Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Settings
              </Typography>
              <Box sx={{ mt: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={systemSettings.sms_enabled === 'true'}
                      onChange={(e) => handleSystemSettingChange('sms_enabled', e.target.checked.toString())}
                    />
                  }
                  label="Enable SMS Notifications"
                  sx={{ mb: 2 }}
                />
                <Divider sx={{ mb: 2 }} />
                
                <FormControlLabel
                  control={
                    <Switch
                      checked={systemSettings.ai_prediction_enabled === 'true'}
                      onChange={(e) => handleSystemSettingChange('ai_prediction_enabled', e.target.checked.toString())}
                    />
                  }
                  label="Enable AI Prediction"
                  sx={{ mb: 2 }}
                />
                <Divider sx={{ mb: 2 }} />
                
                <TextField
                  fullWidth
                  label="Reading Interval (seconds)"
                  type="number"
                  value={systemSettings.reading_interval || 30}
                  onChange={(e) => handleSystemSettingChange('reading_interval', e.target.value)}
                  sx={{ mb: 2 }}
                  helperText="Interval between sensor readings"
                />
                <TextField
                  fullWidth
                  label="Sync Interval (seconds)"
                  type="number"
                  value={systemSettings.sync_interval || 60}
                  onChange={(e) => handleSystemSettingChange('sync_interval', e.target.value)}
                  sx={{ mb: 2 }}
                  helperText="Interval between Firebase syncs"
                />
                <TextField
                  fullWidth
                  label="Max SMS Per Hour"
                  type="number"
                  value={systemSettings.max_sms_per_hour || 100}
                  onChange={(e) => handleSystemSettingChange('max_sms_per_hour', e.target.value)}
                  sx={{ mb: 2 }}
                  helperText="Maximum SMS messages per hour to prevent spam"
                />
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={handleSaveSystemSettings}
                  fullWidth
                >
                  Save Settings
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* System Information */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Information
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={4}>
                  <Typography variant="body2" color="textSecondary">
                    System Name
                  </Typography>
                  <Typography variant="body1">
                    {systemSettings.system_name || 'Barangay Tonsuya Flood Detection System'}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  <Typography variant="body2" color="textSecondary">
                    Version
                  </Typography>
                  <Typography variant="body1">
                    1.0.0
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  <Typography variant="body2" color="textSecondary">
                    Location
                  </Typography>
                  <Typography variant="body1">
                    Barangay Tonsuya, Malabon
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

export default Settings
