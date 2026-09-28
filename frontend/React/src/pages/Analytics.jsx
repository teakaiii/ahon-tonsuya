import React, { useState, useEffect } from 'react'
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material'
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import api from '../services/api'

const COLORS = ['#1976d2', '#dc004e', '#ed6c02', '#2e7d32', '#9c27b0']

const Analytics = () => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [timeRange, setTimeRange] = useState(24)
  
  const [waterLevelTrend, setWaterLevelTrend] = useState([])
  const [currentWaterLevel, setCurrentWaterLevel] = useState(null)
  const [alertHistory, setAlertHistory] = useState([])
  const [smsStatistics, setSmsStatistics] = useState([])
  const [decisionSupport, setDecisionSupport] = useState(null)
  const [waterLevelForecast, setWaterLevelForecast] = useState(null)
  const [residentDistribution, setResidentDistribution] = useState([])

  useEffect(() => {
    fetchAllAnalytics()

    const currentInterval = setInterval(() => {
      fetchCurrentWaterLevel()
      fetchDecisionSupport()
    }, 10000)
    const forecastInterval = setInterval(fetchWaterLevelForecast, 60000)
    return () => {
      clearInterval(currentInterval)
      clearInterval(forecastInterval)
    }
  }, [timeRange])

  const fetchAllAnalytics = async () => {
    try {
      console.log('Fetching all analytics data...')
      await Promise.all([
        fetchCurrentWaterLevel(),
        fetchWaterLevelTrend(),
        fetchAlertHistory(),
        fetchSMSStatistics(),
        fetchDecisionSupport(),
        fetchWaterLevelForecast(),
        fetchResidentDistribution()
      ])
      setError(null)
      console.log('Analytics data fetched successfully')
    } catch (err) {
      console.error('Analytics fetch error:', err)
      setError('Failed to fetch analytics data')
    } finally {
      setLoading(false)
    }
  }

  const fetchCurrentWaterLevel = async () => {
    try {
      const response = await api.get('/api/water-level/current/')
      setCurrentWaterLevel(response.data)
    } catch (err) {
      console.error('Failed to fetch current water level:', err)
    }
  }

  const fetchWaterLevelTrend = async () => {
    try {
      const response = await api.get(`/api/dashboard/water-level-trend/?hours=${timeRange}`)
      const formattedData = response.data.map(item => ({
        time: new Date(item.timestamp).toLocaleTimeString(),
        level: item.water_level_cm
      }))
      setWaterLevelTrend(formattedData)
    } catch (err) {
      console.error('Failed to fetch water level trend:', err)
    }
  }

  const fetchAlertHistory = async () => {
    try {
      const response = await api.get(`/api/dashboard/alert-history/?hours=${timeRange}`)
      const formattedData = response.data.map(item => ({
        time: new Date(item.timestamp).toLocaleTimeString(),
        level: item.alert_level,
        active: item.is_active ? 1 : 0
      }))
      setAlertHistory(formattedData)
    } catch (err) {
      console.error('Failed to fetch alert history:', err)
    }
  }

  const fetchSMSStatistics = async () => {
    try {
      const response = await api.get(`/api/dashboard/sms-statistics/?hours=${timeRange}`)
      setSmsStatistics(response.data)
    } catch (err) {
      console.error('Failed to fetch SMS statistics:', err)
    }
  }

  const fetchDecisionSupport = async () => {
    try {
      const response = await api.get('/api/dashboard/decision-support/')
      setDecisionSupport(response.data)
    } catch (err) {
      console.error('Failed to fetch decision support:', err)
    }
  }

  const fetchWaterLevelForecast = async () => {
    try {
      const response = await api.get('/api/dashboard/water-level-forecast/')
      setWaterLevelForecast(response.data)
    } catch (err) {
      console.error('Failed to fetch regression forecast:', err)
      setWaterLevelForecast(null)
    }
  }

  const fetchResidentDistribution = async () => {
    try {
      const response = await api.get('/api/dashboard/resident-distribution/')
      setResidentDistribution(response.data)
    } catch (err) {
      console.error('Failed to fetch resident distribution:', err)
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
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Analytics
          </Typography>
          <Typography variant="body1" color="text.secondary">
            System performance and data analysis
          </Typography>
        </Box>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Time Range</InputLabel>
          <Select
            value={timeRange}
            label="Time Range"
            onChange={(e) => setTimeRange(e.target.value)}
          >
            <MenuItem value={1}>1 Hour</MenuItem>
            <MenuItem value={6}>6 Hours</MenuItem>
            <MenuItem value={24}>24 Hours</MenuItem>
            <MenuItem value={168}>1 Week</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Grid container spacing={3}>
        {/* Live Water Level Monitor */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={2}>
                <Box>
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <Typography variant="h6">Live Water Level</Typography>
                    <Chip label="LIVE" color="success" size="small" />
                  </Box>
                  <Typography variant="h2" color="primary">
                    {currentWaterLevel?.water_level_cm ?? '--'} cm
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Last reading: {currentWaterLevel?.timestamp
                      ? new Date(currentWaterLevel.timestamp).toLocaleString()
                      : 'Waiting for sensor data'}
                  </Typography>
                </Box>
                <Box textAlign={{ xs: 'left', sm: 'right' }}>
                  <Chip
                    label={currentWaterLevel?.status || 'Unknown'}
                    color={currentWaterLevel?.status === 'Danger' ? 'error' : currentWaterLevel?.status === 'Warning' ? 'warning' : 'success'}
                    sx={{ mb: 1 }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    Sensor: {currentWaterLevel?.sensor_status || 'Unknown'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    GSM: {currentWaterLevel?.gsm_status || 'Unknown'}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Water Level Trend Chart */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Water Level Trend
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={waterLevelTrend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="level" 
                    stroke="#1976d2" 
                    strokeWidth={2}
                    name="Water Level (cm)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* SMS Statistics Chart */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                SMS Delivery Status
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={smsStatistics}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={(entry) => `${entry.delivery_status}: ${entry.count}`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {smsStatistics.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Alert History Chart */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Alert History
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={alertHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="active" fill="#dc004e" name="Active Alerts" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Resident Distribution Chart */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Resident Distribution by Purok
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={residentDistribution} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis dataKey="purok_zone" type="category" width={100} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count" fill="#1976d2" name="Residents" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Decision Support Metrics */}
        {decisionSupport && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Decision Support Metrics
                </Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6} md={3}>
                    <Box textAlign="center">
                      <Typography variant="h3" color="primary">
                        {decisionSupport.risk_percentage ?? '--'}%
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Operational Risk Score
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Box textAlign="center">
                      <Typography variant="h3" color="success.main">
                        {decisionSupport.data_confidence ?? '--'}%
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Data Confidence
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={12} md={6}>
                    <Box>
                      <Typography variant="body2" gutterBottom>
                        Current Assessment: {decisionSupport.status || 'Unavailable'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {decisionSupport.status_summary || 'No decision support summary available.'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Risk score is an operational indicator, not measured model accuracy.
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Water-Level Regression Forecast
              </Typography>
              {waterLevelForecast?.available ? (
                <>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6} md={3}>
                      <Typography variant="h4" color="primary">
                        {waterLevelForecast.selected_forecast_cm} cm
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Selected estimate in {waterLevelForecast.horizon_minutes} minutes
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {waterLevelForecast.selected_method === 'random_forest'
                          ? 'Random Forest performed better on the time-ordered holdout.'
                          : 'Persistence baseline selected because its holdout MAE was lower.'}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                      <Typography variant="h5">{waterLevelForecast.model_forecast_cm} cm</Typography>
                      <Typography variant="body2" color="text.secondary">Random Forest estimate</Typography>
                      <Typography variant="body2" color="text.secondary">
                        Baseline: {waterLevelForecast.baseline_forecast_cm} cm
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                      <Typography variant="subtitle2">Random Forest holdout</Typography>
                      <Typography variant="body2">MAE: {waterLevelForecast.model_metrics.mae_cm} cm</Typography>
                      <Typography variant="body2">RMSE: {waterLevelForecast.model_metrics.rmse_cm} cm</Typography>
                      <Typography variant="body2">R²: {waterLevelForecast.model_metrics.r_squared}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                      <Typography variant="subtitle2">Data quality</Typography>
                      <Typography variant="body2">{waterLevelForecast.valid_readings} valid readings</Typography>
                      <Typography variant="body2">{waterLevelForecast.excluded_readings} excluded outside 0-4 cm</Typography>
                      <Typography variant="body2">{waterLevelForecast.supervised_rows} forecast rows</Typography>
                    </Grid>
                  </Grid>
                  <Alert severity="warning" sx={{ mt: 2 }}>
                    Exploratory forecast only. It is not validated for evacuation decisions. {waterLevelForecast.safety_note}
                  </Alert>
                </>
              ) : (
                <Alert severity="info">
                  {waterLevelForecast?.reason || 'Forecast unavailable. Waiting for sufficient valid, continuous sensor readings.'}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

export default Analytics
