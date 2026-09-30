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
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
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
  ReferenceArea,
  ResponsiveContainer,
} from 'recharts'
import api from '../services/api'

const COLORS = ['#1976d2', '#dc004e', '#ed6c02', '#2e7d32', '#9c27b0']
const formatForecastMetric = (value) => value == null ? '-' : Number(value).toFixed(3)

const getNextMonthValue = () => {
  const today = new Date()
  const month = today.getMonth() + 1
  const year = today.getFullYear() + (month === 12 ? 1 : 0)
  return `${year}-${String(month === 12 ? 1 : month + 1).padStart(2, '0')}`
}

const Analytics = () => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [timeRange] = useState(24)
  const [forecastMonth, setForecastMonth] = useState(getNextMonthValue)
  
  const [waterLevelTrend, setWaterLevelTrend] = useState([])
  const [currentWaterLevel, setCurrentWaterLevel] = useState(null)
  const [alertHistory, setAlertHistory] = useState([])
  const [smsStatistics, setSmsStatistics] = useState([])
  const [decisionSupport, setDecisionSupport] = useState(null)
  const [waterLevelForecast, setWaterLevelForecast] = useState(null)
  const [monthlyForecast, setMonthlyForecast] = useState(null)
  const [monthlyForecastLoading, setMonthlyForecastLoading] = useState(true)
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
        fetchMonthlyForecast(),
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

  const fetchMonthlyForecast = async (selectedMonth = forecastMonth) => {
    if (!selectedMonth) return
    const [year, month] = selectedMonth.split('-')
    setMonthlyForecastLoading(true)
    try {
      const response = await api.get('/api/dashboard/monthly-water-level-forecast/', {
        params: { year, month: Number(month) },
      })
      setMonthlyForecast(response.data)
    } catch (err) {
      console.error('Failed to fetch monthly water-level forecast:', err)
      setMonthlyForecast({ available: false, reason: 'Monthly forecast could not be loaded.' })
    } finally {
      setMonthlyForecastLoading(false)
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
        <TextField
          label="Forecast month"
          type="month"
          size="small"
          value={forecastMonth}
          inputProps={{ min: getNextMonthValue() }}
          onChange={(event) => {
            const selectedMonth = event.target.value
            if (!selectedMonth || selectedMonth >= getNextMonthValue()) {
              setForecastMonth(selectedMonth)
              fetchMonthlyForecast(selectedMonth)
            }
          }}
          InputLabelProps={{ shrink: true }}
          sx={{ minWidth: 180 }}
        />
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
                    <Chip
                      label={currentWaterLevel?.water_level_cm == null
                        ? 'NO DATA'
                        : currentWaterLevel?.is_stale
                          ? 'STALE'
                          : currentWaterLevel?.quality_issue
                            ? 'CHECK SENSOR'
                            : 'LIVE'}
                      color={currentWaterLevel?.water_level_cm == null || currentWaterLevel?.is_stale || currentWaterLevel?.quality_issue ? 'warning' : 'success'}
                      size="small"
                    />
                  </Box>
                  <Typography variant="h2" color="primary">
                    {currentWaterLevel?.water_level_cm == null
                      ? '-- cm'
                      : `${currentWaterLevel?.at_calibrated_limit ? '≥' : ''}${Number(currentWaterLevel.water_level_cm).toFixed(2)} cm`}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {currentWaterLevel?.is_stale ? 'Last valid reading: ' : 'Last reading: '}{currentWaterLevel?.timestamp
                      ? new Date(currentWaterLevel.timestamp).toLocaleString()
                      : 'Waiting for sensor data'}
                  </Typography>
                </Box>
                <Box textAlign={{ xs: 'left', sm: 'right' }}>
                  <Chip
                    label={currentWaterLevel?.is_stale
                      ? 'Stale'
                      : currentWaterLevel?.at_calibrated_limit
                        ? 'At sensor limit'
                        : currentWaterLevel?.quality_issue
                          ? 'Check sensor'
                          : currentWaterLevel?.status || 'No Data'}
                    color={currentWaterLevel?.is_stale || currentWaterLevel?.quality_issue || currentWaterLevel?.status === 'No Data'
                      ? 'warning'
                      : currentWaterLevel?.status === 'Danger'
                        ? 'error'
                        : currentWaterLevel?.status === 'Warning'
                          ? 'warning'
                          : 'success'}
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
              {(currentWaterLevel?.is_stale || currentWaterLevel?.quality_issue) && (
                <Alert severity="warning" sx={{ mt: 2 }}>
                  {currentWaterLevel.quality_issue || 'The latest valid reading is stale.'} Verify the sensor before relying on this value.
                </Alert>
              )}
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
                Monthly Water-Level Forecast
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Daily projection trained on all prior valid readings; method selected using a chronological holdout.
              </Typography>
              {monthlyForecastLoading ? (
                <Box display="flex" alignItems="center" gap={1} minHeight={120}>
                  <CircularProgress size={20} />
                  <Typography variant="body2" color="text.secondary">Loading monthly samples...</Typography>
                </Box>
              ) : (
                <>
                  <ResponsiveContainer width="100%" height={280}>
                    <LineChart data={monthlyForecast?.points || []} margin={{ top: 8, right: 18, left: 4, bottom: 12 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <ReferenceArea y1={0} y2={2} fill="#2e7d32" fillOpacity={0.08} />
                      <ReferenceArea y1={2} y2={3} fill="#ed6c02" fillOpacity={0.1} />
                      <ReferenceArea y1={3} y2={4} fill="#d32f2f" fillOpacity={0.08} />
                      <XAxis dataKey="day" tick={{ fontSize: 11 }} label={{ value: 'Day of month', position: 'insideBottom', offset: -6 }} />
                      <YAxis domain={[0, 4]} ticks={[0, 1, 2, 3, 4]} tick={{ fontSize: 11 }} />
                      <Tooltip
                        labelFormatter={(day) => `${monthlyForecast.month_label} ${day}, ${monthlyForecast.year}`}
                        formatter={(value) => [value == null ? 'No forecast' : `${Number(value).toFixed(2)} cm`, 'Forecast']}
                      />
                      <Legend />
                      <Line type="monotone" dataKey="forecast_cm" name="Forecast water level" stroke="#1565c0" strokeWidth={2.5} dot={{ r: 2 }} connectNulls={false} />
                    </LineChart>
                  </ResponsiveContainer>
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: -0.5, mb: 1 }}>
                    Thresholds: Normal &lt;2 cm · Warning 2–&lt;3 cm · Critical/Danger ≥3 cm
                  </Typography>
                  {monthlyForecast?.horizon_metrics && (
                    <TableContainer sx={{ mb: 1, overflowX: 'auto' }}>
                      <Table size="small" aria-label="Forecast backtest errors by horizon" sx={{ minWidth: 620 }}>
                        <TableHead>
                          <TableRow>
                            <TableCell>Horizon</TableCell>
                            <TableCell align="right">Examples</TableCell>
                            <TableCell align="right">Trend MAE / RMSE (cm)</TableCell>
                            <TableCell align="right">7-reading average MAE / RMSE (cm)</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {Object.values(monthlyForecast.horizon_metrics)
                            .sort((left, right) => left.horizon_days - right.horizon_days)
                            .map((metric) => (
                              <TableRow key={metric.horizon_days}>
                                <TableCell>
                                  {metric.horizon_days} days
                                  {metric.horizon_days === monthlyForecast.forecast_horizon_days ? ' (month)' : ''}
                                </TableCell>
                                <TableCell align="right">{metric.sample_count}</TableCell>
                                <TableCell align="right">
                                  {formatForecastMetric(metric.trend_mae_cm)} / {formatForecastMetric(metric.trend_rmse_cm)}
                                </TableCell>
                                <TableCell align="right">
                                  {formatForecastMetric(metric.persistence_mae_cm)} / {formatForecastMetric(metric.persistence_rmse_cm)}
                                </TableCell>
                              </TableRow>
                            ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  )}
                  {monthlyForecast?.available ? (
                    <>
                      <Grid container spacing={1} sx={{ mt: 0.25, mb: 1 }}>
                        <Grid item xs={12} sm={4}>
                          <Typography variant="caption" color="text.secondary">SELECTED METHOD</Typography>
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>
                            {monthlyForecast.method === 'linear_trend' ? 'Linear trend' : 'Recent 7-day average'}
                          </Typography>
                        </Grid>
                        <Grid item xs={12} sm={4}>
                          <Typography variant="caption" color="text.secondary">BACKTEST MAE / RMSE</Typography>
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>
                            {monthlyForecast.validation_mae_cm} / {monthlyForecast.validation_rmse_cm} cm
                          </Typography>
                        </Grid>
                        <Grid item xs={12} sm={4}>
                          <Typography variant="caption" color="text.secondary">MONTH-LENGTH BACKTEST</Typography>
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>
                            {monthlyForecast.forecast_horizon_days}-day horizon; {monthlyForecast.validation_days} examples
                          </Typography>
                        </Grid>
                      </Grid>
                      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                        At the {monthlyForecast.forecast_horizon_days}-day horizon, linear trend MAE is {monthlyForecast.trend_mae_cm} cm and the recent 7-reading average MAE is {monthlyForecast.persistence_mae_cm} cm.
                      </Typography>
                      <Alert severity="warning">
                        Final projection uses {monthlyForecast.training_days} days of readings. Method selection uses {monthlyForecast.validation_days} historical examples from {monthlyForecast.validation_start} to {monthlyForecast.validation_end} at the full-month horizon. Accuracy is not a guarantee of future conditions. {monthlyForecast.safety_note}
                      </Alert>
                    </>
                  ) : (
                    <Alert severity="info" sx={{ mt: 1 }}>
                      {monthlyForecast?.reason || 'No validated monthly forecast is available for this selection.'}
                    </Alert>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Short-Term Water-Level Regression Forecast
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
