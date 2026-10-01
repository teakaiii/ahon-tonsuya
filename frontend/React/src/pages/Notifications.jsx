import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Button,
  Badge,
  IconButton,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Tooltip,
} from '@mui/material'
import {
  Notifications as NotificationsIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  MarkEmailRead as MarkReadIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'
import api from '../services/api'

const Notifications = () => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [viewFilter, setViewFilter] = useState('all')
  const [expandedNotifications, setExpandedNotifications] = useState(new Set())

  useEffect(() => {
    fetchNotifications()
    const interval = setInterval(() => {
      fetchNotifications()
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchNotifications = async () => {
    try {
      const response = await api.get('/api/notifications/')
      const records = response.data.results || response.data
      setNotifications(records)
      setUnreadCount(records.filter((notification) => !notification.is_read).length)
      setError(null)
    } catch (err) {
      setError('Failed to fetch notifications')
    } finally {
      setLoading(false)
    }
  }

  const handleMarkAsRead = async (notifId) => {
    try {
      await api.patch(`/api/notifications/${notifId}/`, { is_read: true })
      fetchNotifications()
    } catch (err) {
      setError('Failed to mark notification as read')
    }
  }

  const handleNotificationClick = (notification) => {
    setExpandedNotifications((current) => {
      const next = new Set(current)
      if (next.has(notification.notif_id)) next.delete(notification.notif_id)
      else next.add(notification.notif_id)
      return next
    })
    if (!notification.is_read) handleMarkAsRead(notification.notif_id)
  }

  const handleMarkAllAsRead = async () => {
    try {
      await api.post('/api/notifications/mark-all-read/')
      fetchNotifications()
    } catch (err) {
      setError('Failed to mark all notifications as read')
    }
  }

  const handleDelete = async (notifId) => {
    try {
      await api.delete(`/api/notifications/${notifId}/`)
      fetchNotifications()
    } catch (err) {
      setError('Failed to delete notification')
    }
  }

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'success':
        return <CheckCircleIcon color="success" />
      case 'warning':
        return <WarningIcon color="warning" />
      case 'danger':
      case 'alert':
        return <ErrorIcon color="error" />
      case 'info':
      default:
        return <InfoIcon color="info" />
    }
  }

  const getNotificationColor = (type) => {
    switch (type) {
      case 'success':
        return 'success'
      case 'warning':
        return 'warning'
      case 'danger':
      case 'alert':
        return 'error'
      case 'info':
      default:
        return 'info'
    }
  }

  const getDisplayType = (notification) => {
    if (notification.type === 'alert') return 'danger'
    return notification.type
  }

  const formatTimestamp = (value) => {
    if (!value) return 'Unknown time'
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric', month: 'numeric', day: 'numeric',
      hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true,
    }).format(new Date(value))
  }

  const visibleNotifications = notifications.filter((notification) => (
    viewFilter === 'all' || (viewFilter === 'unread' && !notification.is_read) || (viewFilter === 'read' && notification.is_read)
  ))

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} mb={1.5} gap={2} flexWrap="wrap">
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.25 }}>
            Notifications
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <Badge badgeContent={unreadCount} color="error"><NotificationsIcon color="action" /></Badge>
          <FormControl size="small" sx={{ minWidth: 125 }}>
            <InputLabel>View</InputLabel>
            <Select value={viewFilter} label="View" onChange={(event) => setViewFilter(event.target.value)}>
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="unread">Unread</MenuItem>
              <MenuItem value="read">Read</MenuItem>
            </Select>
          </FormControl>
          <Tooltip title="Refresh notifications"><IconButton onClick={fetchNotifications}><RefreshIcon /></IconButton></Tooltip>
          {unreadCount > 0 && (
            <Button variant="outlined" size="small" startIcon={<MarkReadIcon />} onClick={handleMarkAllAsRead}>Mark all read</Button>
          )}
        </Stack>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Card sx={{ boxShadow: '0 1px 4px rgba(18, 38, 63, 0.10)' }}>
        <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
          {visibleNotifications.length === 0 ? (
            <Box textAlign="center" py={4}>
              <NotificationsIcon sx={{ fontSize: 48, color: 'text.secondary' }} />
              <Typography variant="h6" color="textSecondary" sx={{ mt: 2 }}>
                {notifications.length === 0 ? 'No notifications yet' : 'No matching notifications'}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {notifications.length === 0 ? 'New system activity and alerts will appear here.' : 'Try changing the view filter.'}
              </Typography>
            </Box>
          ) : (
            <List>
              {visibleNotifications.map((notification) => (
                <React.Fragment key={notification.notif_id}>
                  {(() => {
                    const displayType = getDisplayType(notification)
                    return (
                  <ListItem
                    button
                    tabIndex={0}
                    aria-label={`Open notification: ${notification.title}`}
                    aria-expanded={expandedNotifications.has(notification.notif_id)}
                    onClick={() => handleNotificationClick(notification)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        handleNotificationClick(notification)
                      }
                    }}
                    sx={{
                      bgcolor: notification.is_read ? 'transparent' : '#f1f7fd',
                      borderLeft: notification.is_read ? '3px solid transparent' : '3px solid #1976d2',
                      px: 1.5,
                      py: 1.25,
                      cursor: 'pointer',
                      '&:hover': { bgcolor: '#eaf2fa' },
                      '&:focus-visible': { outline: '2px solid #1976d2', outlineOffset: '-2px' },
                    }}
                    secondaryAction={
                      <Box>
                        {!notification.is_read && (
                          <Tooltip title="Mark as read"><IconButton
                            edge="end"
                            onClick={(event) => {
                              event.stopPropagation()
                              handleMarkAsRead(notification.notif_id)
                            }}
                            sx={{ mr: 1 }}
                          >
                            <MarkReadIcon />
                          </IconButton></Tooltip>
                        )}
                        <Tooltip title="Delete notification"><IconButton
                          edge="end"
                          onClick={(event) => {
                            event.stopPropagation()
                            handleDelete(notification.notif_id)
                          }}
                        >
                          <DeleteIcon />
                        </IconButton></Tooltip>
                      </Box>
                    }
                  >
                    <ListItemIcon>
                      {getNotificationIcon(displayType)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="subtitle1" fontWeight={notification.is_read ? 'normal' : 'bold'}>
                            {notification.title}
                          </Typography>
                          <Chip
                            label={displayType}
                            color={displayType === 'demo' ? 'default' : getNotificationColor(displayType)}
                            size="small"
                            sx={{ textTransform: 'capitalize' }}
                          />
                        </Box>
                      }
                      secondaryTypographyProps={{ component: 'div' }}
                      secondary={expandedNotifications.has(notification.notif_id) ? (
                        <Box sx={{ mt: 0.75 }}>
                          <Typography variant="body2" color="textSecondary">
                            {notification.message}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            {formatTimestamp(notification.created_at)}
                          </Typography>
                        </Box>
                      ) : null}
                    />
                  </ListItem>
                    )
                  })()}
                  <Divider />
                </React.Fragment>
              ))}
            </List>
          )}
        </CardContent>
      </Card>
    </Box>
  )
}

export default Notifications
