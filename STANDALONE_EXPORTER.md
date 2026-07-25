# Standalone SigNoz Exporter

This document explains how to use the standalone exporter script to send metrics and traces from Creator-Atlas to an external SigNoz instance.

## Overview

The standalone exporter (`export_to_signoz.py`) is completely independent of the Creator-Atlas application. It can be run separately to send telemetry data to any external SigNoz instance without requiring changes to the application code or configuration.

## Why This Approach?

- **Zero Application Dependencies**: The Creator-Atlas application runs without any OpenTelemetry or SigNoz dependencies
- **Flexible Deployment**: You can run SigNoz anywhere - locally, on a different server, or in the cloud
- **Simple Integration**: Just run the script whenever you want to export data
- **No Infrastructure Complexity**: No need for Docker networking, shared networks, or complex configurations

## Prerequisites

### Install Dependencies

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

### External SigNoz Instance

You need a running SigNoz instance. This can be:
- Local SigNoz running on your machine
- SigNoz running on a remote server
- SigNoz Cloud instance

## Usage

### 1. Test the Exporter

Run the script with test data to verify connectivity:

```bash
python export_to_signoz.py --signoz-endpoint localhost:4317 --test
```

This will send sample traces and metrics to your SigNoz instance.

### 2. Export Custom Data

Create a JSON file with your telemetry data:

```json
[
  {
    "operation": "channel_analyze",
    "attributes": {
      "channel": "google",
      "execution_time_ms": 125.5,
      "cache_hit": false
    },
    "value": 1.0
  },
  {
    "operation": "channel_analyze", 
    "attributes": {
      "channel": "microsoft",
      "execution_time_ms": 89.2,
      "cache_hit": true
    },
    "value": 1.0
  }
]
```

Then export it:

```bash
python export_to_signoz.py --signoz-endpoint localhost:4317 --data-file telemetry_data.json
```

### 3. Interactive Mode

Run the script in interactive mode for manual exports:

```bash
python export_to_signoz.py --signoz-endpoint localhost:4317
```

## Command Line Options

- `--signoz-endpoint`: External SigNoz OTLP endpoint (default: `localhost:4317`)
- `--service-name`: Service name for telemetry (default: `creator-atlas-standalone`)
- `--insecure`: Use insecure connection (default: `True`)
- `--test`: Run with sample test data
- `--data-file`: JSON file containing custom telemetry data to export

## Examples

### Example 1: Local SigNoz

```bash
# Assuming SigNoz is running locally on port 4317
python export_to_signoz.py --signoz-endpoint localhost:4317 --test
```

### Example 2: Remote SigNoz

```bash
# Assuming SigNoz is running on a remote server
python export_to_signoz.py --signoz-endpoint 192.168.1.100:4317 --test
```

### Example 3: Custom Service Name

```bash
python export_to_signoz.py --signoz-endpoint localhost:4317 --service-name my-creator-app --test
```

### Example 4: Export Application Logs

You can create a script to periodically export application data:

```python
import json
import subprocess
import time

# Run this script periodically
while True:
    # Get application metrics (example)
    response = subprocess.run(['curl', 'http://localhost:8081/api/v1/metrics'], 
                           capture_output=True, text=True)
    
    if response.status_code == 200:
        data = json.loads(response.stdout)
        
        # Save to temporary file
        with open('app_metrics.json', 'w') as f:
            json.dump(data, f)
        
        # Export to SigNoz
        subprocess.run(['python', 'export_to_signoz.py', 
                       '--signoz-endpoint', 'localhost:4317',
                       '--data-file', 'app_metrics.json'])
    
    time.sleep(60)  # Export every minute
```

## Integration with Application

### Option 1: Manual Export

Run the exporter manually whenever you want to send data to SigNoz:

```bash
python export_to_signoz.py --signoz-endpoint localhost:4317 --data-file my_telemetry.json
```

### Option 2: Scheduled Export

Use cron (Linux) or Task Scheduler (Windows) to run the exporter periodically:

**Linux (cron):**
```bash
# Export every 5 minutes
*/5 * * * * cd /path/to/Creator-Atlas && python export_to_signoz.py --signoz-endpoint localhost:4317 --data-file telemetry.json
```

**Windows (Task Scheduler):**
Create a scheduled task to run the script periodically.

### Option 3: Application Integration

Modify your application to call the exporter script:

```python
import subprocess
import json

def export_to_signoz(operation_name, attributes, value=1.0):
    """Export telemetry data to SigNoz via standalone script."""
    data = {
        "operation": operation_name,
        "attributes": attributes,
        "value": value
    }
    
    with open('temp_telemetry.json', 'w') as f:
        json.dump([data], f)
    
    subprocess.run([
        'python', 'export_to_signoz.py',
        '--signoz-endpoint', 'localhost:4317',
        '--data-file', 'temp_telemetry.json'
    ])
```

## Data Format

The JSON data file should contain an array of objects, where each object has:

- `operation` (required): Name of the operation for the trace
- `attributes` (required): Key-value pairs for span/metric attributes
- `value` (optional): Numeric value for metrics

Example:
```json
[
  {
    "operation": "api_request",
    "attributes": {
      "endpoint": "/api/v1/analyze",
      "method": "POST",
      "status_code": 200,
      "duration_ms": 125.5
    },
    "value": 1.0
  }
]
```

## Troubleshooting

### Connection Issues

If you see connection errors:

1. Verify SigNoz is running: `curl http://localhost:3301` (or your SigNoz UI port)
2. Check the endpoint is correct: `host:port` format
3. Ensure no firewall is blocking the connection
4. Test connectivity: `telnet localhost 4317`

### No Data in SigNoz UI

If data isn't appearing:

1. Check the exporter logs for errors
2. Verify the service name matches what you're searching for in SigNoz
3. Ensure SigNoz has ClickHouse connectivity
4. Check SigNoz collector logs for incoming data

### Missing Dependencies

If you see import errors:

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

## Architecture

```
┌─────────────────┐
│ Creator-Atlas   │
│   Application   │
│   (No OTel)     │
└────────┬────────┘
         │
         │ (Optional: Generate telemetry data)
         ▼
┌─────────────────┐
│ JSON Data File  │
└────────┬────────┘
         │
         │ (export_to_signoz.py)
         ▼
┌─────────────────┐
│ Standalone      │
│ Exporter Script │
└────────┬────────┘
         │ OTLP (gRPC)
         ▼
┌─────────────────┐
│ External SigNoz │
│   Instance      │
└─────────────────┘
```

## Benefits

- **Clean Application**: No OpenTelemetry dependencies in your application
- **Flexible Deployment**: SigNoz can be anywhere
- **Simple Setup**: Just run the script
- **No Infrastructure Complexity**: No Docker networking issues
- **Easy Testing**: Test with `--test` flag
- **Custom Data**: Export any data you want in any format

## Files

- `export_to_signoz.py` - Standalone exporter script
- `docker-compose.yml` - Application configuration (no OTel dependencies)
- `docker-compose.signoz.yml` - External SigNoz configuration (optional)

## Support

For issues with the standalone exporter:
1. Check the script output for error messages
2. Verify SigNoz is accessible
3. Test with `--test` flag first
4. Check the JSON data format
