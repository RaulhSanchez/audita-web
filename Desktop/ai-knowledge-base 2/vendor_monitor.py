#!/usr/bin/env python3
"""
Vendor Client Monitoring System
Monitors the status of all vendor clients in parallel.
"""

import json
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def load_clients(filepath='clients.json'):
    """Load clients configuration from JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"{Colors.RED}Error: {filepath} not found{Colors.RESET}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"{Colors.RED}Error: Invalid JSON in {filepath}{Colors.RESET}")
        sys.exit(1)


def get_client_status(client, timeout=10):
    """Fetch status for a single client."""
    result = {
        'name': client['name'],
        'status': None,
        'error': None,
        'data': None
    }

    try:
        # POST-AUDITORÍA · Forzar HTTPS y verificar certificado.
        # El vendor_key es un secreto compartido — si viaja sobre HTTP se
        # filtra a cualquiera en la red.
        url = f"{client['url']}/api/v1/plan/status"
        if not url.lower().startswith("https://"):
            result['status'] = 'error'
            result['error'] = (
                f"URL insegura: '{client['url']}'. Solo se admite https:// "
                "para proteger el X-Vendor-Key."
            )
            return result

        import ssl as _ssl
        ctx = _ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = _ssl.CERT_REQUIRED

        req = urllib.request.Request(
            url,
            headers={'X-Vendor-Key': client['vendor_key']}
        )

        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            result['status'] = 'ok'
            result['data'] = data
    except urllib.error.URLError as e:
        result['status'] = 'error'
        result['error'] = str(e)
    except urllib.error.HTTPError as e:
        result['status'] = 'error'
        result['error'] = f"HTTP {e.code}"
    except json.JSONDecodeError:
        result['status'] = 'error'
        result['error'] = "Invalid JSON response"
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)

    return result


def get_alert_level(data):
    """Determine alert level based on usage percentages."""
    if not data:
        return 'error'

    try:
        pct_docs  = float(data.get('pct_documents', 0))
        pct_users = float(data.get('pct_users', 0))
        max_pct   = max(pct_docs, pct_users)

        if max_pct > 95:
            return 'critical'
        elif max_pct > 80:
            return 'warning'
        else:
            return 'ok'
    except Exception:
        return 'error'


def color_cell(text, level):
    """Apply color based on alert level."""
    if level == 'critical':
        return f"{Colors.RED}{text}{Colors.RESET}"
    elif level == 'warning':
        return f"{Colors.YELLOW}{text}{Colors.RESET}"
    else:
        return f"{Colors.GREEN}{text}{Colors.RESET}"


def format_usage(used, limit):
    """Format usage as 'used/limit (percent%)'."""
    if limit == 0:
        return "0/0 (0%)"
    percent = (used / limit) * 100
    return f"{used}/{limit} ({percent:.0f}%)"


def print_table(results):
    """Print results as a formatted table."""
    print(f"\n{Colors.BOLD}{'Company':<25} {'Plan':<15} {'Docs':<20} {'Users':<20} {'Queries/day':<15} {'Alerts':<15}{Colors.RESET}")
    print("-" * 110)

    total_clients = 0
    plan_counts = {'starter': 0, 'business': 0, 'enterprise': 0, 'unknown': 0}
    alert_count = 0

    for result in results:
        total_clients += 1
        name = result['name'][:24]

        if result['status'] == 'error':
            alert_count += 1
            plan_counts['unknown'] += 1
            print(color_cell(f"{name:<25} {'N/A':<15} {'N/A':<20} {'N/A':<20} {'N/A':<15} {'❌ Sin conexión':<15}", 'critical'))
            continue

        data = result['data']
        plan = data.get('plan_label', data.get('plan', 'N/A'))[:14]
        docs  = format_usage(
            data.get('usage', {}).get('documents', 0),
            data.get('limits', {}).get('max_documents', 0)
        )
        users = format_usage(
            data.get('usage', {}).get('users', 0),
            data.get('limits', {}).get('max_users', 0)
        )
        queries_val = data.get('limits', {}).get('max_queries_day', 0)
        queries = ('∞' if queries_val == -1 else str(queries_val))[:14]

        # Count by plan
        plan_lower = plan.lower()
        if plan_lower in plan_counts:
            plan_counts[plan_lower] += 1
        else:
            plan_counts['unknown'] += 1

        # Determine alert level
        alert_level = get_alert_level(data)
        if alert_level != 'ok':
            alert_count += 1

        alerts_text = ''
        if alert_level == 'critical':
            alerts_text = '🔴 Crítica'
        elif alert_level == 'warning':
            alerts_text = '🟡 Alerta'
        else:
            alerts_text = '✓ OK'

        # Format row with colors
        row = f"{name:<25} {plan:<15} {docs:<20} {users:<20} {queries:<15} {alerts_text:<15}"
        print(color_cell(row, alert_level))

    # Summary
    print("-" * 110)
    print(f"\n{Colors.BOLD}RESUMEN:{Colors.RESET}")
    print(f"  Total clientes: {total_clients}")
    print(f"  Starter: {plan_counts['starter']}, Business: {plan_counts['business']}, Enterprise: {plan_counts['enterprise']}")
    print(f"  Clientes con alertas: {color_cell(str(alert_count), 'critical' if alert_count > 0 else 'ok')}")


def print_json(results):
    """Print results as JSON."""
    output = {
        'timestamp': datetime.now().isoformat(),
        'clients': []
    }

    summary = {'total': 0, 'starter': 0, 'business': 0, 'enterprise': 0, 'with_alerts': 0}

    for result in results:
        summary['total'] += 1

        if result['status'] == 'error':
            summary['with_alerts'] += 1
            output['clients'].append({
                'name': result['name'],
                'status': 'error',
                'error': result['error']
            })
        else:
            data = result['data']
            plan = data.get('plan', 'unknown').lower()

            if plan in summary:
                summary[plan] += 1

            alert_level = get_alert_level(data)
            if alert_level != 'ok':
                summary['with_alerts'] += 1

            output['clients'].append({
                'name': result['name'],
                'status': 'ok',
                'company': data.get('company', ''),
                'plan': plan,
                'usage': data.get('usage', {}),
                'limits': data.get('limits', {}),
                'pct_documents': data.get('pct_documents', 0),
                'pct_users': data.get('pct_users', 0),
                'warnings': data.get('warnings', []),
                'alert_level': alert_level
            })

    output['summary'] = summary
    print(json.dumps(output, indent=2))


def main():
    """Main entry point."""
    json_output = '--json' in sys.argv

    # Load clients
    clients = load_clients()

    if not clients:
        print(f"{Colors.RED}Error: No clients found in clients.json{Colors.RESET}")
        sys.exit(1)

    # Fetch status in parallel
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(get_client_status, client): client for client in clients}

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    # Sort by name for consistent output
    results.sort(key=lambda x: x['name'])

    # Output results
    if json_output:
        print_json(results)
    else:
        print_table(results)


if __name__ == '__main__':
    main()
