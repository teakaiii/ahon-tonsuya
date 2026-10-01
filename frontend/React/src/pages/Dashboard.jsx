import React, { useEffect, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  Grid,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import { CheckCircle, Download, ErrorOutline, MonitorHeart, People, Sms, TrendingDown, TrendingFlat, TrendingUp, WarningAmber } from '@mui/icons-material'
import { CartesianGrid, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import api from '../services/api'

const bandStyles = {
  normal: { label: 'Normal', color: 'success', accent: '#2e7d32', background: '#edf7ed' },
  warning: { label: 'Warning', color: 'warning', accent: '#ed6c02', background: '#fff8e6' },
  critical: { label: 'Critical', color: 'error', accent: '#d32f2f', background: '#fff0f0' },
  unknown: { label: 'No fresh data', color: 'default', accent: '#687782', background: '#f2f4f5' },
}

const formatTimestamp = (value) => {
  if (!value) return 'No reading'
  const date = new Date(value)
  const pad = (part) => String(part).padStart(2, '0')
  const hour = date.getHours()
  const period = hour >= 12 ? 'PM' : 'AM'
  const clockHour = hour % 12 || 12
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${clockHour}:${pad(date.getMinutes())}:${pad(date.getSeconds())} ${period}`
}

const statusIcon = (band) => {
  if (band === 'critical') return <ErrorOutline fontSize="small" />
  if (band === 'warning') return <WarningAmber fontSize="small" />
  if (band === 'unknown') return <ErrorOutline fontSize="small" />
  return <CheckCircle fontSize="small" />
}

const Dashboard = () => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [overview, setOverview] = useState(null)
  const [telemetry, setTelemetry] = useState([])
  const [decision, setDecision] = useState(null)
  const [exportFormat, setExportFormat] = useState('pdf')
  const [exporting, setExporting] = useState(false)

  const fetchDashboard = async () => {
    try {
      const [overviewResponse, telemetryResponse, decisionResponse] = await Promise.all([
        api.get('/api/dashboard/overview/'),
        api.get('/api/dashboard/telemetry/?limit=25'),
        api.get('/api/dashboard/decision-support/'),
      ])
      setOverview(overviewResponse.data)
      setTelemetry(telemetryResponse.data)
      setDecision({
        ...decisionResponse.data,
        status_summary: (decisionResponse.data.status_summary || '').replace('Latest valid sensor reading is stale. ', ''),
      })
      setError(null)
    } catch (requestError) {
      console.error('Dashboard fetch error:', requestError)
      setError('Unable to load live monitoring data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboard()
    const interval = setInterval(fetchDashboard, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleExport = async () => {
    setExporting(true)
    try {
      const response = await api.get(`/api/reports/export/?file_format=${exportFormat}`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = `ahon-floodwatch-telemetry-${new Date().toISOString().replace(/[:.]/g, '-')}.${exportFormat}`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (exportError) {
      console.error('Export failed:', exportError)
      setError('Export failed. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  if (loading) {
    return <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 320, gap: 1 }}><CircularProgress size={24} /><Typography color="text.secondary">Loading monitoring data...</Typography></Box>
  }

  if (error && !overview) return <Alert severity="error">{error}</Alert>

  const current = overview?.current_water_level || {}
  const currentBand = current.quality_issue || current.status === 'No Data'
    ? 'unknown'
    : current.status === 'Danger'
      ? 'critical'
      : current.status === 'Warning' || current.status === 'Alert'
        ? 'warning'
        : telemetry[0]?.band || 'normal'
  const currentStyle = bandStyles[currentBand]
  const chartData = [...telemetry].reverse().map((item) => ({ time: formatTimestamp(item.timestamp).slice(11), level: item.water_level_cm }))
  const chartMax = Math.max(4, Math.ceil(Math.max(...chartData.map(({ level }) => Number(level) || 0))))
  const chartTicks = Array.from({ length: chartMax + 1 }, (_, index) => index)

  return (
    <Box sx={{ p: { xs: 1.5, md: 2.5 }, backgroundColor: '#f7f9fb', minHeight: '100%' }}>
      {error && <Alert severity="warning" sx={{ mb: 1.5 }}>{error}</Alert>}

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: { xs: 'flex-start', md: 'center' }, gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: 1.2 }}>Barangay Tonsuya / Admin Monitoring</Typography>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>FloodWatch dashboard</Typography>
          <Typography variant="body2" color="text.secondary">Live telemetry, threshold history, and operational guidance</Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 105 }}>
            <Select value={exportFormat} onChange={(event) => setExportFormat(event.target.value)} aria-label="Export format">
              <MenuItem value="pdf">PDF</MenuItem>
              <MenuItem value="csv">CSV</MenuItem>
              <MenuItem value="xlsx">Excel</MenuItem>
            </Select>
          </FormControl>
          <Button variant="contained" startIcon={exporting ? <CircularProgress size={17} color="inherit" /> : <Download />} onClick={handleExport} disabled={exporting} sx={{ textTransform: 'none' }}>
            {exporting ? 'Exporting' : 'Export report'}
          </Button>
        </Stack>
      </Box>

      <Card sx={{ mb: 2, borderLeft: `5px solid ${currentStyle.accent}`, backgroundColor: currentStyle.background, boxShadow: 'none' }}>
        <CardContent sx={{ py: 1.75, '&:last-child': { pb: 1.75 } }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} gap={1}>
            <Box><Typography variant="caption" color="text.secondary">LATEST VALID WATER LEVEL</Typography><Typography variant="h3" sx={{ fontWeight: 750, lineHeight: 1.1 }}>{current.water_level_cm == null ? 'No reading' : `${current.at_calibrated_limit ? '≥' : ''}${Number(current.water_level_cm).toFixed(2)}`} {current.water_level_cm == null ? null : <Typography component="span" variant="h6" color="text.secondary">cm</Typography>}</Typography></Box>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap"><Chip icon={statusIcon(currentBand)} color={currentStyle.color} label={current.at_calibrated_limit ? 'At sensor limit' : current.quality_issue ? 'Check sensor' : currentStyle.label} /><Typography variant="caption" color="text.secondary">Updated {formatTimestamp(current.timestamp)}</Typography></Stack>
          </Stack>
        </CardContent>
      </Card>
      {current.quality_issue && (
        <Alert severity="warning" sx={{ mb: 1.5 }}>
          {current.quality_issue} Verify the sensor before relying on this value.
        </Alert>
      )}

      <Grid container spacing={1.5} sx={{ mb: 2 }}>
        <Metric title="Active alerts" value={overview?.alerts?.active_count || 0} detail={`${overview?.alerts?.recent_count || 0} in last 24h`} icon={<WarningAmber />} color="#ed6c02" />
        <Metric title="Residents" value={overview?.residents?.total || 0} detail={`${overview?.residents?.active || 0} active`} icon={<People />} color="#1565c0" />
        <Metric title="SMS delivery" value={overview?.sms?.sent_last_24h || 0} detail={`${overview?.sms?.failed_last_24h || 0} failed in 24h`} icon={<Sms />} color="#2e7d32" />
        <Metric title="Sensor / GSM" value={!current.quality_issue && current.sensor_status === 'online' ? 'Online' : current.water_level_cm == null ? 'Offline' : 'Check'} detail={`${current.gsm_status || 'unknown'} | 10s refresh`} icon={<MonitorHeart />} color="#6a1b9a" />
      </Grid>

      <Grid container spacing={1.5}>
        <Grid item xs={12} md={7}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ p: 2 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>Telemetry trend</Typography>
                  <Typography variant="caption" color="text.secondary">Latest {telemetry.length} readings</Typography>
                </Box>
                <Chip size="small" label="10-second refresh" variant="outlined" />
              </Stack>
              <ResponsiveContainer width="100%" height={235}>
                <LineChart data={chartData} margin={{ top: 8, right: 12, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e7ebef" />
                  <ReferenceArea y1={0} y2={2} fill="#2e7d32" fillOpacity={0.08} />
                  <ReferenceArea y1={2} y2={3} fill="#ed6c02" fillOpacity={0.1} />
                  <ReferenceArea y1={3} y2={chartMax} fill="#d32f2f" fillOpacity={0.08} />
                  <XAxis dataKey="time" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                  <YAxis domain={[0, chartMax]} ticks={chartTicks} tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(value) => [`${Number(value).toFixed(2)} cm`, 'Level']} />
                  <Line type="monotone" dataKey="level" stroke="#1565c0" strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
              <Box component="section" aria-label="Water level guide" sx={{ mt: 1, pt: 1.25, borderTop: '1px solid #e7ebef' }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>Water level guide</Typography>
                <Grid container spacing={1.5}>
                  <Grid item xs={12} sm={4}>
                    <Box sx={{ pl: 1, borderLeft: '3px solid #2e7d32' }}>
                      <Typography variant="body2" sx={{ fontWeight: 700, color: '#2e7d32' }}>0–&lt;2 cm · Normal</Typography>
                      <Typography variant="caption" color="text.secondary">Routine monitoring; continue regular checks.</Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Box sx={{ pl: 1, borderLeft: '3px solid #ed6c02' }}>
                      <Typography variant="body2" sx={{ fontWeight: 700, color: '#ed6c02' }}>2–&lt;3 cm · Warning</Typography>
                      <Typography variant="caption" color="text.secondary">Water is rising; stay alert and prepare.</Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Box sx={{ pl: 1, borderLeft: '3px solid #d32f2f' }}>
                      <Typography variant="body2" sx={{ fontWeight: 700, color: '#d32f2f' }}>≥3 cm · Critical / Danger</Typography>
                      <Typography variant="caption" color="text.secondary">Activate response; verify the reading and prepare evacuation.</Typography>
                    </Box>
                  </Grid>
                </Grid>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={5}><Card sx={{ height: '100%' }}><CardContent sx={{ p: 2 }}><Typography variant="h6" sx={{ fontWeight: 700 }}>Decision support</Typography><Typography variant="caption" color="text.secondary">Evidence-based guidance from stored telemetry</Typography><Stack direction="row" spacing={2} sx={{ mt: 1.5, mb: 1.25 }}><Box sx={{ flex: 1 }}><Typography variant="caption" color="text.secondary">OPERATIONAL RISK SCORE</Typography><Typography variant="h3" sx={{ fontWeight: 750, lineHeight: 1.1 }}>{decision?.risk_percentage ?? 0}%</Typography><RiskScale value={decision?.risk_percentage ?? 0} /></Box><Box><Typography variant="caption" color="text.secondary">DATA CONFIDENCE</Typography><Typography variant="h5" sx={{ fontWeight: 700, mt: 0.5 }}>{decision?.data_confidence ?? 0}%</Typography><Typography variant="caption" color="text.secondary">Sensor/GSM health</Typography></Box></Stack><Stack direction="row" spacing={0.75} alignItems="center" sx={{ mb: 1 }}><TrendIcon value={decision?.trend_change_percentage} /><Typography variant="caption" color="text.secondary">{decision?.trend_change_percentage == null ? 'Trend unavailable' : `${Math.abs(decision.trend_change_percentage).toFixed(1)}% ${decision.trend_change_percentage > 0 ? 'increase' : decision.trend_change_percentage < 0 ? 'decrease' : 'no change'} from previous reading`}</Typography></Stack><Typography sx={{ fontWeight: 700 }}>{decision?.status_summary || 'No telemetry available.'}</Typography><Typography variant="caption" color="text.secondary">Basis: {decision?.basis || 'Recorded data only.'}</Typography><Typography variant="subtitle2" sx={{ mt: 1.5 }}>Key findings</Typography><Box component="ul" sx={{ pl: 2.2, mt: 0.5, mb: 1 }}>{(decision?.key_findings || []).map((finding) => <Typography component="li" variant="body2" key={finding}>{finding}</Typography>)}</Box><Typography variant="subtitle2">Recommended admin action</Typography><Box component="ol" sx={{ pl: 2.2, mt: 0.5, mb: 0 }}>{(decision?.recommended_actions || []).map((action) => <Typography component="li" variant="body2" key={action}>{action}</Typography>)}</Box></CardContent></Card></Grid>
        <Grid item xs={12}><Card><CardContent sx={{ p: 2, '&:last-child': { pb: 1 } }}><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} gap={1} mb={1}><Box><Typography variant="h6" sx={{ fontWeight: 700 }}>Telemetry log</Typography><Typography variant="caption" color="text.secondary">Local date/time: YYYY-MM-DD h:mm:ss AM/PM</Typography></Box><Stack direction="row" spacing={0.75}><Chip size="small" label="Normal" color="success" variant="outlined" /><Chip size="small" label="Warning" color="warning" variant="outlined" /><Chip size="small" label="Critical" color="error" variant="outlined" /></Stack></Stack><Box sx={{ overflowX: 'auto' }}><Table size="small" aria-label="Telemetry history table"><TableHead><TableRow><TableCell>Timestamp</TableCell><TableCell align="right">Level</TableCell><TableCell>Status</TableCell><TableCell>Sensor</TableCell><TableCell>GSM</TableCell></TableRow></TableHead><TableBody>{telemetry.map((item) => { const style = bandStyles[item.band] || bandStyles.normal; return <TableRow key={item.reading_id} sx={{ '&:last-child td': { border: 0 } }}><TableCell sx={{ whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 12 }}>{formatTimestamp(item.timestamp)}</TableCell><TableCell align="right" sx={{ fontWeight: 700 }}>{Number(item.water_level_cm).toFixed(2)} cm</TableCell><TableCell><Chip size="small" icon={statusIcon(item.band)} color={style.color} label={style.label} /></TableCell><TableCell>{item.sensor_status}</TableCell><TableCell>{item.gsm_status}</TableCell></TableRow> })}{!telemetry.length && <TableRow><TableCell colSpan={5}><Typography color="text.secondary">No telemetry has been recorded.</Typography></TableCell></TableRow>}</TableBody></Table></Box></CardContent></Card></Grid>
      </Grid>
    </Box>
  )
}

const Metric = ({ title, value, detail, icon, color }) => (
  <Grid item xs={12} sm={6} md={3}><Card sx={{ height: '100%' }}><CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}><Stack direction="row" justifyContent="space-between" alignItems="flex-start"><Box><Typography variant="caption" color="text.secondary">{title.toUpperCase()}</Typography><Typography variant="h5" sx={{ fontWeight: 750, mt: 0.35 }}>{value}</Typography><Typography variant="caption" color="text.secondary">{detail}</Typography></Box><Box sx={{ color, display: 'flex' }}>{icon}</Box></Stack></CardContent></Card></Grid>
)

const RiskScale = ({ value }) => {
  const filled = Math.ceil(value / 10)
  return <Box sx={{ mt: 1, maxWidth: 250 }}><Stack direction="row" spacing={0.35}>{Array.from({ length: 10 }, (_, index) => <Box key={index} sx={{ flex: 1, height: 8, borderRadius: 0.5, backgroundColor: index < filled ? (index < 4 ? '#2e7d32' : index < 7 ? '#ed6c02' : '#d32f2f') : '#e1e6eb' }} />)}</Stack><Stack direction="row" justifyContent="space-between"><Typography variant="caption" color="text.secondary">Normal</Typography><Typography variant="caption" color="text.secondary">Warning</Typography><Typography variant="caption" color="text.secondary">Critical</Typography></Stack></Box>
}

const TrendIcon = ({ value }) => {
  if (value > 0) return <TrendingUp fontSize="small" color="error" />
  if (value < 0) return <TrendingDown fontSize="small" color="success" />
  return <TrendingFlat fontSize="small" color="disabled" />
}

export default Dashboard
