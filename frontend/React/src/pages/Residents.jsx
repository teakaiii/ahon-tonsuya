import React, { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  Grid,
  IconButton,
  InputAdornment,
  InputLabel,
  Menu,
  MenuItem,
  Select,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material'
import {
  Add as AddIcon,
  CheckCircleOutline,
  DeleteOutline,
  Download as DownloadIcon,
  EditOutlined,
  GroupOutlined,
  MoreVert,
  NotificationsActiveOutlined,
  Search as SearchIcon,
  SmsOutlined,
  UploadFile as UploadFileIcon,
} from '@mui/icons-material'
import api from '../services/api'

const REQUIRED_COLUMNS = ['full_name', 'mobile_number', 'address', 'purok_zone', 'status', 'sms_enabled']

const emptyForm = {
  full_name: '',
  mobile_number: '',
  address: '',
  purok_zone: '',
  status: 'active',
  sms_enabled: true,
}

const statusColor = (status) => ({ active: 'success', inactive: 'default', evacuated: 'warning' }[status] || 'default')
const formatStreetLabel = (value) => String(value ?? '').replace(/^purok\b/i, 'Street')

const Residents = () => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [residents, setResidents] = useState([])
  const [statistics, setStatistics] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterPurok, setFilterPurok] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterSms, setFilterSms] = useState('')
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [selected, setSelected] = useState([])
  const [openDialog, setOpenDialog] = useState(false)
  const [editingResident, setEditingResident] = useState(null)
  const [formData, setFormData] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [fileInput, setFileInput] = useState(null)
  const [importing, setImporting] = useState(false)
  const [importErrors, setImportErrors] = useState([])
  const [showImportHelp, setShowImportHelp] = useState(true)
  const [menuAnchor, setMenuAnchor] = useState(null)

  const fetchResidents = async () => {
    try {
      const response = await api.get('/api/residents/')
      setResidents(response.data.results || response.data)
      setError(null)
    } catch (requestError) {
      console.error('Residents fetch error:', requestError)
      setError('Unable to load resident records.')
    } finally {
      setLoading(false)
    }
  }

  const fetchStatistics = async () => {
    try {
      const response = await api.get('/api/residents/statistics/')
      setStatistics(response.data)
    } catch (requestError) {
      console.error('Residents statistics error:', requestError)
    }
  }

  useEffect(() => {
    fetchResidents()
    fetchStatistics()
  }, [])

  const filteredResidents = useMemo(() => residents.filter((resident) => {
    const query = searchTerm.trim().toLowerCase()
    const matchesSearch = !query || [resident.full_name, resident.mobile_number, resident.address].some((value) => value?.toLowerCase().includes(query))
    const matchesPurok = !filterPurok || resident.purok_zone === filterPurok
    const matchesStatus = !filterStatus || resident.status === filterStatus
    const matchesSms = filterSms === '' || String(resident.sms_enabled) === filterSms
    return matchesSearch && matchesPurok && matchesStatus && matchesSms
  }), [residents, searchTerm, filterPurok, filterStatus, filterSms])

  const visibleResidents = filteredResidents.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
  const visibleIds = visibleResidents.map((resident) => resident.resident_id)
  const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((id) => selected.includes(id))

  const updateForm = (field, value) => setFormData((current) => ({ ...current, [field]: value }))

  const openResidentDialog = (resident = null) => {
    setEditingResident(resident)
    setFormError('')
    setFormData(resident ? {
      full_name: resident.full_name,
      mobile_number: resident.mobile_number.replace(/^\+63/, ''),
      address: resident.address,
      purok_zone: resident.purok_zone,
      status: resident.status,
      sms_enabled: resident.sms_enabled,
    } : emptyForm)
    setOpenDialog(true)
  }

  const closeResidentDialog = () => {
    setOpenDialog(false)
    setEditingResident(null)
    setFormError('')
  }

  const validateForm = () => {
    if (!formData.full_name.trim() || !formData.address.trim() || !formData.purok_zone.trim()) return 'Name, address, and Street are required.'
    if (!/^9\d{9}$/.test(formData.mobile_number)) return 'Enter a valid Philippine mobile number: 9XXXXXXXXX.'
    return ''
  }

  const handleSubmit = async () => {
    const validationError = validateForm()
    if (validationError) {
      setFormError(validationError)
      return
    }
    try {
      if (editingResident) await api.patch(`/api/residents/${editingResident.resident_id}/`, formData)
      else await api.post('/api/residents/', formData)
      closeResidentDialog()
      await Promise.all([fetchResidents(), fetchStatistics()])
    } catch (requestError) {
      setFormError(requestError.response?.data?.mobile_number?.[0] || 'Unable to save resident record.')
    }
  }

  const handleFileSelected = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError('Please select a CSV file.')
      return
    }
    const header = (await file.text()).split(/\r?\n/, 1)[0].split(',').map((column) => column.trim())
    const missing = REQUIRED_COLUMNS.filter((column) => !header.includes(column))
    if (missing.length) {
      setError(`CSV is missing required columns: ${missing.join(', ')}`)
      setFileInput(null)
      return
    }
    setError(null)
    setImportErrors([])
    setFileInput(file)
  }

  const handleImport = async () => {
    if (!fileInput) return
    setImporting(true)
    const upload = new FormData()
    upload.append('file', fileInput)
    try {
      const response = await api.post('/api/residents/import/', upload, { headers: { 'Content-Type': 'multipart/form-data' } })
      setImportErrors(response.data.errors || [])
      setFileInput(null)
      await Promise.all([fetchResidents(), fetchStatistics()])
      if (response.data.errors?.length) setError('Some CSV rows need attention.')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'CSV import failed.')
    } finally {
      setImporting(false)
    }
  }

  const toggleSelected = (id) => setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])
  const toggleVisible = () => setSelected((current) => allVisibleSelected ? current.filter((id) => !visibleIds.includes(id)) : [...new Set([...current, ...visibleIds])])

  const bulkSmsUpdate = async (enabled) => {
    await Promise.all(selected.map((id) => api.patch(`/api/residents/${id}/`, { sms_enabled: enabled })))
    setSelected([])
    await fetchResidents()
  }

  const bulkDelete = async () => {
    if (!selected.length || !window.confirm(`Delete ${selected.length} selected resident(s)?`)) return
    await Promise.all(selected.map((id) => api.delete(`/api/residents/${id}/`)))
    setSelected([])
    await Promise.all([fetchResidents(), fetchStatistics()])
  }

  const exportSelected = () => {
    const rows = residents.filter((resident) => selected.includes(resident.resident_id))
    const csv = [REQUIRED_COLUMNS.join(','), ...rows.map((resident) => [resident.full_name, resident.mobile_number, resident.address, resident.purok_zone, resident.status, resident.sms_enabled ? 'true' : 'false'].map((value) => `"${String(value).replace(/"/g, '""')}"`).join(','))].join('\n')
    const link = document.createElement('a')
    link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    link.download = `residents-selected-${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(link.href)
  }

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 12 }}><CircularProgress /></Box>

  const puroks = Object.keys(statistics?.purok_counts || {})

  return (
    <Box sx={{ pb: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: { xs: 'flex-start', md: 'center' }, gap: 1.5, mb: 1.5, flexWrap: 'wrap' }}>
        <Box><Typography variant="h4" sx={{ fontWeight: 700, mb: 0.25 }}>Residents Management</Typography><Typography variant="body2" color="text.secondary">Resident registry and SMS alert recipients</Typography></Box>
<DeleteOutline fontSize="small" />
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <ButtonGroup variant="contained"><Button startIcon={<AddIcon />} onClick={() => openResidentDialog()}>Add Resident</Button><Button aria-label="More resident actions" onClick={(event) => setMenuAnchor(event.currentTarget)}><MoreVert /></Button></ButtonGroup>
          <Menu anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={() => setMenuAnchor(null)}><MenuItem onClick={() => { setMenuAnchor(null); document.getElementById('resident-import-input')?.click() }}><UploadFileIcon fontSize="small" sx={{ mr: 1 }} />Import CSV</MenuItem><MenuItem component="a" href="/residents_template.csv" download="residents_template.csv" onClick={() => setMenuAnchor(null)}><DownloadIcon fontSize="small" sx={{ mr: 1 }} />Download template</MenuItem></Menu>
          <input id="resident-import-input" type="file" accept=".csv" hidden onChange={handleFileSelected} />
        </Stack>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 1.5 }}>{error}</Alert>}
      {showImportHelp && <Alert severity="info" onClose={() => setShowImportHelp(false)} sx={{ mb: 1.5, py: 0.25 }}>CSV import requires: <strong>{REQUIRED_COLUMNS.join(', ')}</strong></Alert>}
      {fileInput && <Alert severity="info" action={<Button color="inherit" size="small" onClick={handleImport} disabled={importing}>{importing ? 'Importing...' : 'Process CSV'}</Button>} sx={{ mb: 1.5 }}>Ready to import <strong>{fileInput.name}</strong></Alert>}
      {importErrors.length > 0 && <Alert severity="warning" sx={{ mb: 1.5 }}>Imported with {importErrors.length} invalid row(s). Review rows: {importErrors.map((item) => item.row).join(', ')}.</Alert>}

      <Grid container spacing={1.5} sx={{ mb: 1.5 }}>
        <StatCard label="Total residents" value={statistics?.total_residents || 0} icon={<GroupOutlined />} color="#1565c0" />
        <StatCard label="Active residents" value={statistics?.active_residents || 0} icon={<CheckCircleOutline />} color="#2e7d32" />
        <StatCard label="SMS enabled" value={statistics?.sms_enabled_count || 0} icon={<SmsOutlined />} color="#6a1b9a" />
        <StatCard label="Streets" value={puroks.length} icon={<NotificationsActiveOutlined />} color="#ed6c02" />
      </Grid>

      <Card sx={{ mb: 1.5, boxShadow: '0 1px 4px rgba(18, 38, 63, 0.10)' }}><CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}><Grid container spacing={1.25} alignItems="center"><Grid item xs={12} md={4}><TextField fullWidth size="small" label="Search name, phone, or address" value={searchTerm} onChange={(event) => { setSearchTerm(event.target.value); setPage(0) }} InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> }} /></Grid><Grid item xs={12} sm={4} md={2.5}><FilterSelect label="Street" value={filterPurok} onChange={(value) => { setFilterPurok(value); setPage(0) }} options={puroks.map((value) => ({ value, label: formatStreetLabel(value) }))} /></Grid><Grid item xs={12} sm={4} md={2.5}><FilterSelect label="Status" value={filterStatus} onChange={(value) => { setFilterStatus(value); setPage(0) }} options={['active', 'inactive', 'evacuated']} /></Grid><Grid item xs={12} sm={4} md={2.5}><FilterSelect label="SMS status" value={filterSms} onChange={(value) => { setFilterSms(value); setPage(0) }} options={[{ value: 'true', label: 'Enabled' }, { value: 'false', label: 'Disabled' }]} /></Grid><Grid item xs={12} md={12}><Typography variant="caption" color="text.secondary">Showing {filteredResidents.length} of {residents.length} resident records</Typography></Grid></Grid></CardContent></Card>

      {selected.length > 0 && <Toolbar disableGutters sx={{ minHeight: 44, px: 1.5, mb: 1, borderRadius: 1, backgroundColor: '#eaf2fa' }}><Typography variant="body2" sx={{ flex: 1, fontWeight: 600 }}>{selected.length} selected</Typography><Stack direction="row" spacing={0.75}><Button size="small" onClick={() => bulkSmsUpdate(true)}>Enable SMS</Button><Button size="small" onClick={() => bulkSmsUpdate(false)}>Disable SMS</Button><Button size="small" onClick={exportSelected} startIcon={<DownloadIcon />}>Export</Button><Button size="small" color="error" onClick={bulkDelete} startIcon={<DeleteOutline />}>Delete</Button></Stack></Toolbar>}

      <Card sx={{ boxShadow: '0 1px 4px rgba(18, 38, 63, 0.10)' }}><TableContainer><Table size="small"><TableHead sx={{ backgroundColor: '#f4f7fa' }}><TableRow><TableCell padding="checkbox"><Checkbox checked={allVisibleSelected} indeterminate={selected.length > 0 && !allVisibleSelected} onChange={toggleVisible} /></TableCell><TableCell sx={{ fontWeight: 700 }}>Name</TableCell><TableCell sx={{ fontWeight: 700 }}>Mobile Number</TableCell><TableCell sx={{ fontWeight: 700 }}>Address</TableCell><TableCell sx={{ fontWeight: 700 }}>Street</TableCell><TableCell sx={{ fontWeight: 700 }}>Status</TableCell><TableCell sx={{ fontWeight: 700 }}>SMS</TableCell><TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell></TableRow></TableHead><TableBody>{visibleResidents.map((resident) => <TableRow key={resident.resident_id} hover><TableCell padding="checkbox"><Checkbox checked={selected.includes(resident.resident_id)} onChange={() => toggleSelected(resident.resident_id)} /></TableCell><TableCell sx={{ fontWeight: 600 }}>{resident.full_name}</TableCell><TableCell>{resident.mobile_number}</TableCell><TableCell>{resident.address}</TableCell><TableCell>{formatStreetLabel(resident.purok_zone)}</TableCell><TableCell><Chip label={resident.status} color={statusColor(resident.status)} size="small" sx={{ fontWeight: 600, textTransform: 'capitalize' }} /></TableCell><TableCell><Chip label={resident.sms_enabled ? 'Enabled' : 'Disabled'} color={resident.sms_enabled ? 'success' : 'default'} size="small" variant="outlined" /></TableCell><TableCell align="right"><Tooltip title="Edit resident"><IconButton size="small" onClick={() => openResidentDialog(resident)}><EditOutlined fontSize="small" /></IconButton></Tooltip><Tooltip title="Delete resident"><IconButton size="small" color="error" onClick={() => { if (window.confirm(`Delete ${resident.full_name}?`)) api.delete(`/api/residents/${resident.resident_id}/`).then(() => Promise.all([fetchResidents(), fetchStatistics()])).catch(() => setError('Unable to delete resident.')) }}><DeleteOutline /></IconButton></Tooltip></TableCell></TableRow>)}{!visibleResidents.length && <TableRow><TableCell colSpan={8} align="center" sx={{ py: 5 }}><Typography color="text.secondary">No residents match the current filters.</Typography></TableCell></TableRow>}</TableBody></Table></TableContainer><Divider /><TablePagination component="div" count={filteredResidents.length} page={page} onPageChange={(_, nextPage) => setPage(nextPage)} rowsPerPage={rowsPerPage} onRowsPerPageChange={(event) => { setRowsPerPage(Number(event.target.value)); setPage(0) }} rowsPerPageOptions={[5, 10, 25, 50]} labelRowsPerPage="Rows" /></Card>

      <Dialog open={openDialog} onClose={closeResidentDialog} maxWidth="sm" fullWidth><DialogTitle>{editingResident ? 'Edit resident record' : 'Add resident'}</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}><TextField label="Full name" value={formData.full_name} onChange={(event) => updateForm('full_name', event.target.value)} fullWidth required /><TextField label="Mobile number" value={formData.mobile_number} onChange={(event) => updateForm('mobile_number', event.target.value.replace(/\D/g, '').slice(0, 10))} InputProps={{ startAdornment: <InputAdornment position="start">+63</InputAdornment> }} helperText="Enter 10 digits after +63: 9XXXXXXXXX" fullWidth required /><TextField label="Address" value={formData.address} onChange={(event) => updateForm('address', event.target.value)} fullWidth required /><TextField label="Street" value={formData.purok_zone} onChange={(event) => updateForm('purok_zone', event.target.value)} fullWidth required /><FormControl fullWidth><InputLabel>Status</InputLabel><Select label="Status" value={formData.status} onChange={(event) => updateForm('status', event.target.value)}><MenuItem value="active">Active</MenuItem><MenuItem value="inactive">Inactive</MenuItem><MenuItem value="evacuated">Evacuated</MenuItem></Select></FormControl><FormControlLabel control={<Switch checked={formData.sms_enabled} onChange={(event) => updateForm('sms_enabled', event.target.checked)} />} label="Enable SMS alerts" />{formError && <Alert severity="error">{formError}</Alert>}</Stack></DialogContent><DialogActions><Button onClick={closeResidentDialog}>Cancel</Button><Button variant="contained" onClick={handleSubmit}>{editingResident ? 'Save changes' : 'Add resident'}</Button></DialogActions></Dialog>
    </Box>
  )
}

const FilterSelect = ({ label, value, onChange, options }) => <FormControl fullWidth size="small"><InputLabel>{label}</InputLabel><Select label={label} value={value} onChange={(event) => onChange(event.target.value)}><MenuItem value="">All</MenuItem>{options.map((option) => { const item = typeof option === 'string' ? { value: option, label: option } : option; return <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem> })}</Select></FormControl>

const StatCard = ({ label, value, icon, color }) => <Grid item xs={12} sm={6} md={3}><Card sx={{ height: '100%', boxShadow: '0 1px 4px rgba(18, 38, 63, 0.10)' }}><CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}><Stack direction="row" justifyContent="space-between" alignItems="center"><Box><Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</Typography><Typography variant="h5" sx={{ fontWeight: 700, mt: 0.25 }}>{value}</Typography></Box><Box sx={{ color, display: 'flex' }}>{icon}</Box></Stack></CardContent></Card></Grid>

export default Residents
