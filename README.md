# AssetFlow

Multi-Tenant Asset Management System built with Django REST Framework.

## Dashboard Visualization

Chart.js is used for dashboard visualization. The vendored library is excluded from git — regenerate it locally:

```bash
curl -sL -o apps/analytics/dashboard/static/js/chart.min.js \
  "https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"
```

To upgrade to a newer version, change the version number in the URL above.
