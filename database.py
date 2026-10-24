import random
import sqlite3
import threading
from datetime import datetime


DEFAULT_THRESHOLDS = {
    "cpu": {"warning_threshold": 70.0, "critical_threshold": 90.0},
    "memory": {"warning_threshold": 75.0, "critical_threshold": 90.0},
    "disk": {"warning_threshold": 80.0, "critical_threshold": 95.0},
    "network": {"warning_threshold": 75.0, "critical_threshold": 90.0},
}


class Database:
    def __init__(self, db_path="server_monitoring.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self.init_db()

    def connect(self):
        conn = sqlite3.connect(self.db_path, timeout=60)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout = 60000")
        return conn

    def _now(self):
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    def init_db(self):
        with self._lock:
            with self.connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS servers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        server_id TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        ip_address TEXT NOT NULL,
                        region TEXT NOT NULL,
                        operating_system TEXT NOT NULL,
                        status TEXT NOT NULL,
                        cpu_usage REAL NOT NULL,
                        memory_usage REAL NOT NULL,
                        disk_usage REAL NOT NULL,
                        network_usage REAL NOT NULL,
                        health_score INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        last_checked TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS monitoring_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        server_id TEXT NOT NULL,
                        cpu_usage REAL NOT NULL,
                        memory_usage REAL NOT NULL,
                        disk_usage REAL NOT NULL,
                        network_usage REAL NOT NULL,
                        health_score INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        server_id TEXT NOT NULL,
                        resource_type TEXT NOT NULL,
                        current_value REAL NOT NULL,
                        threshold REAL NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        resolved_at TEXT
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS thresholds (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        resource_type TEXT NOT NULL UNIQUE,
                        warning_threshold REAL NOT NULL,
                        critical_threshold REAL NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        server_id TEXT,
                        event_type TEXT NOT NULL,
                        description TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                    """
                )

        self.seed_default_thresholds()
        self.seed_default_servers()

    def seed_default_thresholds(self):
        with self._lock:
            with self.connect() as conn:
                for resource, values in DEFAULT_THRESHOLDS.items():
                    existing = conn.execute(
                        "SELECT 1 FROM thresholds WHERE resource_type = ?",
                        (resource,),
                    ).fetchone()
                    if not existing:
                        conn.execute(
                            """
                            INSERT INTO thresholds (resource_type, warning_threshold, critical_threshold, updated_at)
                            VALUES (?, ?, ?, ?)
                            """,
                            (resource, values["warning_threshold"], values["critical_threshold"], self._now()),
                        )

    def add_event(self, server_id, event_type, description):
        with self._lock:
            with self.connect() as conn:
                conn.execute(
                    "INSERT INTO events (server_id, event_type, description, timestamp) VALUES (?, ?, ?, ?)",
                    (server_id, event_type, description, self._now()),
                )

    def seed_default_servers(self):
        with self._lock:
            with self.connect() as conn:
                count = conn.execute("SELECT COUNT(*) FROM servers").fetchone()[0]
                if count > 0:
                    return

                default_servers = [
                    {"server_id": "server-01", "name": "Server 01", "ip_address": "10.10.10.11", "region": "Chennai", "operating_system": "Ubuntu 22.04 LTS", "status": "ONLINE", "cpu_usage": 42, "memory_usage": 58, "disk_usage": 61, "network_usage": 38, "health_score": 82},
                    {"server_id": "server-02", "name": "Server 02", "ip_address": "10.10.10.12", "region": "Mumbai", "operating_system": "CentOS 9", "status": "ONLINE", "cpu_usage": 68, "memory_usage": 74, "disk_usage": 72, "network_usage": 54, "health_score": 71},
                    {"server_id": "server-03", "name": "Server 03", "ip_address": "10.10.10.13", "region": "Bangalore", "operating_system": "Debian 12", "status": "WARNING", "cpu_usage": 78, "memory_usage": 81, "disk_usage": 73, "network_usage": 68, "health_score": 63},
                    {"server_id": "server-04", "name": "Server 04", "ip_address": "10.10.10.14", "region": "Delhi", "operating_system": "Windows Server 2022", "status": "CRITICAL", "cpu_usage": 92, "memory_usage": 94, "disk_usage": 88, "network_usage": 81, "health_score": 38},
                    {"server_id": "server-05", "name": "Server 05", "ip_address": "10.10.10.15", "region": "Hyderabad", "operating_system": "Rocky Linux 9", "status": "ONLINE", "cpu_usage": 37, "memory_usage": 46, "disk_usage": 57, "network_usage": 45, "health_score": 86},
                ]
                now = self._now()
                for row in default_servers:
                    conn.execute(
                        """
                        INSERT INTO servers (
                            server_id, name, ip_address, region, operating_system, status,
                            cpu_usage, memory_usage, disk_usage, network_usage, health_score,
                            created_at, last_checked
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["server_id"], row["name"], row["ip_address"], row["region"], row["operating_system"], row["status"],
                            row["cpu_usage"], row["memory_usage"], row["disk_usage"], row["network_usage"], row["health_score"],
                            now, now,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO monitoring_history (
                            server_id, cpu_usage, memory_usage, disk_usage, network_usage, health_score, status, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (row["server_id"], row["cpu_usage"], row["memory_usage"], row["disk_usage"], row["network_usage"], row["health_score"], row["status"], now),
                    )
                    conn.execute(
                        "INSERT INTO events (server_id, event_type, description, timestamp) VALUES (?, ?, ?, ?)",
                        (row["server_id"], "SERVER_CREATED", f"Simulated server {row['server_id']} initialized.", now),
                    )

    def _generate_server_id(self, name):
        base = name.strip().lower().replace(" ", "-")
        clean = "".join(ch for ch in base if ch.isalnum() or ch in "-")
        if not clean:
            clean = "server"
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT server_id FROM servers WHERE server_id LIKE ? ORDER BY server_id DESC",
                (f"{clean}%",),
            ).fetchall()
        suffix = 1
        candidate = clean
        while True:
            current = candidate if suffix == 1 else f"{clean}-{suffix:02d}"
            if not any(row["server_id"] == current for row in existing):
                return current
            suffix += 1

    def get_threshold_map(self):
        with self._lock:
            with self.connect() as conn:
                rows = conn.execute(
                    "SELECT resource_type, warning_threshold, critical_threshold FROM thresholds"
                ).fetchall()
        result = {}
        for row in rows:
            result[row["resource_type"]] = {
                "warning_threshold": float(row["warning_threshold"]),
                "critical_threshold": float(row["critical_threshold"]),
            }
        return result

    def set_thresholds(self, payload):
        with self._lock:
            with self.connect() as conn:
                for resource_type, values in payload.items():
                    warning = float(values.get("warning_threshold"))
                    critical = float(values.get("critical_threshold"))
                    if critical < warning:
                        critical = warning
                    conn.execute(
                        """
                        INSERT INTO thresholds (resource_type, warning_threshold, critical_threshold, updated_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(resource_type)
                        DO UPDATE SET warning_threshold = excluded.warning_threshold,
                                      critical_threshold = excluded.critical_threshold,
                                      updated_at = excluded.updated_at
                        """,
                        (resource_type, warning, critical, self._now()),
                    )
                self.add_event(None, "THRESHOLD_UPDATED", f"Thresholds updated for {', '.join(payload.keys())}.")

    def get_servers(self):
        with self._lock:
            with self.connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM servers ORDER BY name ASC"
                ).fetchall()
                return [dict(row) for row in rows]

    def get_server_by_id(self, server_id):
        with self._lock:
            with self.connect() as conn:
                row = conn.execute("SELECT * FROM servers WHERE server_id = ?", (server_id,)).fetchone()
                if not row:
                    return None
                return dict(row)

    def calculate_health_score(self, cpu, memory, disk, network, status):
        if status == "OFFLINE":
            return 0
        composite = (cpu * 0.35) + (memory * 0.25) + (disk * 0.2) + (network * 0.2)
        score = 100 - composite
        score = max(0, min(100, round(score)))
        return score

    def determine_status(self, cpu, memory, disk, network, status):
        if status == "OFFLINE":
            return "OFFLINE"
        thresholds = self.get_threshold_map()
        max_value = max(cpu, memory, disk, network)
        if (
            cpu >= thresholds.get("cpu", {}).get("critical_threshold", 90)
            or memory >= thresholds.get("memory", {}).get("critical_threshold", 90)
            or disk >= thresholds.get("disk", {}).get("critical_threshold", 95)
            or network >= thresholds.get("network", {}).get("critical_threshold", 90)
            or max_value >= 90
        ):
            return "CRITICAL"
        if (
            cpu >= thresholds.get("cpu", {}).get("warning_threshold", 70)
            or memory >= thresholds.get("memory", {}).get("warning_threshold", 75)
            or disk >= thresholds.get("disk", {}).get("warning_threshold", 80)
            or network >= thresholds.get("network", {}).get("warning_threshold", 75)
        ):
            return "WARNING"
        return "ONLINE"

    def insert_history_snapshot(self, server_id, status, cpu, memory, disk, network, health):
        with self._lock:
            with self.connect() as conn:
                conn.execute(
                    """
                    INSERT INTO monitoring_history (
                        server_id, cpu_usage, memory_usage, disk_usage, network_usage, health_score, status, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (server_id, cpu, memory, disk, network, health, status, self._now()),
                )
                conn.execute(
                    "DELETE FROM monitoring_history WHERE id NOT IN (SELECT id FROM monitoring_history WHERE server_id = ? ORDER BY timestamp DESC LIMIT 40) AND server_id = ?",
                    (server_id, server_id),
                )

    def update_server_metrics(self, server_id, cpu, memory, disk, network, status):
        health = self.calculate_health_score(cpu, memory, disk, network, status)
        status = self.determine_status(cpu, memory, disk, network, status)
        with self._lock:
            with self.connect() as conn:
                conn.execute(
                    """
                    UPDATE servers
                    SET cpu_usage = ?, memory_usage = ?, disk_usage = ?, network_usage = ?,
                        status = ?, health_score = ?, last_checked = ?
                    WHERE server_id = ?
                    """,
                    (cpu, memory, disk, network, status, health, self._now(), server_id),
                )
        self.insert_history_snapshot(server_id, status, cpu, memory, disk, network, health)
        return {"server_id": server_id, "cpu_usage": cpu, "memory_usage": memory, "disk_usage": disk, "network_usage": network, "status": status, "health_score": health}

    def create_alert(self, server_id, resource_type, current_value, threshold, severity, message):
        with self._lock:
            with self.connect() as conn:
                existing = conn.execute(
                    "SELECT * FROM alerts WHERE server_id = ? AND resource_type = ? AND status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1",
                    (server_id, resource_type),
                ).fetchone()
                if existing:
                    return dict(existing)

                conn.execute(
                    """
                    INSERT INTO alerts (server_id, resource_type, current_value, threshold, severity, message, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
                    """,
                    (server_id, resource_type, current_value, threshold, severity, message, self._now()),
                )
                conn.execute(
                    "INSERT INTO events (server_id, event_type, description, timestamp) VALUES (?, ?, ?, ?)",
                    (server_id, "ALERT_CREATED", message, self._now()),
                )
                alert = conn.execute(
                    "SELECT * FROM alerts WHERE server_id = ? AND resource_type = ? AND status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1",
                    (server_id, resource_type),
                ).fetchone()
                return dict(alert) if alert else None

    def resolve_alert(self, alert_id):
        with self._lock:
            with self.connect() as conn:
                alert = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
                if not alert:
                    return None
                conn.execute(
                    "UPDATE alerts SET status = 'RESOLVED', resolved_at = ? WHERE id = ?",
                    (self._now(), alert_id),
                )
                conn.execute(
                    "INSERT INTO events (server_id, event_type, description, timestamp) VALUES (?, ?, ?, ?)",
                    (alert["server_id"], "ALERT_RESOLVED", f"Alert {alert_id} marked as resolved.", self._now()),
                )
                return [dict(row) for row in conn.execute("SELECT * FROM alerts ORDER BY created_at DESC").fetchall()]

    def get_alerts(self):
        with self._lock:
            with self.connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM alerts ORDER BY created_at DESC"
                ).fetchall()
                return [dict(row) for row in rows]

    def get_history(self, server_id):
        with self._lock:
            with self.connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM monitoring_history WHERE server_id = ? ORDER BY timestamp ASC",
                    (server_id,),
                ).fetchall()
                return [dict(row) for row in rows]

    def create_server(self, payload):
        base_name = payload.get("name", "").strip()
        region = payload.get("region", "").strip()
        operating_system = payload.get("operating_system", "").strip()
        ip_address = payload.get("ip_address", "").strip()
        if not base_name or not region or not operating_system or not ip_address:
            raise ValueError("Server name, region, OS and IP are required.")

        server_id = self._generate_server_id(base_name)
        now = self._now()
        base_cpu = 28
        base_memory = 34
        base_disk = 41
        base_network = 30
        health = self.calculate_health_score(base_cpu, base_memory, base_disk, base_network, "ONLINE")
        status = self.determine_status(base_cpu, base_memory, base_disk, base_network, "ONLINE")
        with self._lock:
            with self.connect() as conn:
                conn.execute(
                    """
                    INSERT INTO servers (
                        server_id, name, ip_address, region, operating_system, status,
                        cpu_usage, memory_usage, disk_usage, network_usage, health_score,
                        created_at, last_checked
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (server_id, base_name, ip_address, region, operating_system, status, base_cpu, base_memory, base_disk, base_network, health, now, now),
                )
                conn.execute(
                    "INSERT INTO monitoring_history (server_id, cpu_usage, memory_usage, disk_usage, network_usage, health_score, status, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (server_id, base_cpu, base_memory, base_disk, base_network, health, status, now),
                )
        self.add_event(server_id, "SERVER_CREATED", f"Server {server_id} added by administrator.")
        return self.get_server_by_id(server_id)

    def delete_server(self, server_id):
        with self._lock:
            with self.connect() as conn:
                if not conn.execute("SELECT 1 FROM servers WHERE server_id = ?", (server_id,)).fetchone():
                    return False
                conn.execute("DELETE FROM servers WHERE server_id = ?", (server_id,))
                conn.execute("DELETE FROM monitoring_history WHERE server_id = ?", (server_id,))
                conn.execute("DELETE FROM alerts WHERE server_id = ?", (server_id,))
        self.add_event(server_id, "SERVER_REMOVED", f"Server {server_id} was removed from the dashboard.")
        return True

    def fail_server(self, server_id):
        server = self.get_server_by_id(server_id)
        if not server:
            return None
        with self._lock:
            with self.connect() as conn:
                conn.execute(
                    "UPDATE servers SET status = 'OFFLINE', cpu_usage = 0, memory_usage = 0, disk_usage = 0, network_usage = 0, health_score = 0, last_checked = ? WHERE server_id = ?",
                    (self._now(), server_id),
                )
        self.add_event(server_id, "SERVER_FAILED", f"Server {server_id} failed and went offline.")
        self.create_alert(server_id, "AVAILABILITY", 0, 0, "CRITICAL", f"Server {server_id} failed and is now offline.")
        self.insert_history_snapshot(server_id, "OFFLINE", 0, 0, 0, 0, 0)
        return self.get_server_by_id(server_id)

    def recover_server(self, server_id):
        server = self.get_server_by_id(server_id)
        if not server:
            return None
        cpu = 22
        memory = 30
        disk = 40
        network = 25
        status = "ONLINE"
        health = self.calculate_health_score(cpu, memory, disk, network, status)
        with self._lock:
            with self.connect() as conn:
                conn.execute(
                    "UPDATE servers SET status = ?, cpu_usage = ?, memory_usage = ?, disk_usage = ?, network_usage = ?, health_score = ?, last_checked = ? WHERE server_id = ?",
                    (status, cpu, memory, disk, network, health, self._now(), server_id),
                )
                active_alerts = conn.execute(
                    "SELECT * FROM alerts WHERE server_id = ? AND status = 'ACTIVE' ORDER BY created_at DESC",
                    (server_id,),
                ).fetchall()
                for alert in active_alerts:
                    if alert["resource_type"] == "AVAILABILITY" or alert["severity"] == "CRITICAL":
                        conn.execute(
                            "UPDATE alerts SET status = 'RESOLVED', resolved_at = ? WHERE id = ?",
                            (self._now(), alert["id"]),
                        )
        self.add_event(server_id, "SERVER_RECOVERED", f"Server {server_id} recovered and returned to online service.")
        self.insert_history_snapshot(server_id, status, cpu, memory, disk, network, health)
        return self.get_server_by_id(server_id)

    def simulate_next_cycle(self):
        servers = self.get_servers()
        thresholds = self.get_threshold_map()
        for server in servers:
            if server["status"] == "OFFLINE":
                continue
            rng = random.Random(server["server_id"])
            cpu = server["cpu_usage"]
            memory = server["memory_usage"]
            disk = server["disk_usage"]
            network = server["network_usage"]

            cpu = max(0, min(100, cpu + rng.uniform(-7, 8)))
            memory = max(0, min(100, memory + rng.uniform(-6, 7)))
            disk = max(0, min(100, disk + rng.uniform(-5, 6)))
            network = max(0, min(100, network + rng.uniform(-6, 8)))

            if cpu >= 85 or memory >= 88 or disk >= 92 or network >= 80:
                server["status"] = "CRITICAL"
            elif cpu >= 70 or memory >= 75 or disk >= 80 or network >= 75:
                server["status"] = "WARNING"
            else:
                server["status"] = "ONLINE"

            health_score = self.calculate_health_score(cpu, memory, disk, network, server["status"])
            updated = self.update_server_metrics(server["server_id"], cpu, memory, disk, network, server["status"])
            if health_score < 50:
                self.create_alert(server["server_id"], "OVERALL", health_score, 50, "CRITICAL", f"{server['server_id']} health score dropped to {health_score}.")

            resources = [
                ("cpu", "CPU", cpu, thresholds.get("cpu", {}).get("warning_threshold", 70), thresholds.get("cpu", {}).get("critical_threshold", 90)),
                ("memory", "Memory", memory, thresholds.get("memory", {}).get("warning_threshold", 75), thresholds.get("memory", {}).get("critical_threshold", 90)),
                ("disk", "Disk", disk, thresholds.get("disk", {}).get("warning_threshold", 80), thresholds.get("disk", {}).get("critical_threshold", 95)),
                ("network", "Network", network, thresholds.get("network", {}).get("warning_threshold", 75), thresholds.get("network", {}).get("critical_threshold", 90)),
            ]
            for resource_type, label, value, warning, critical in resources:
                if value >= critical:
                    self.create_alert(server["server_id"], resource_type.upper(), value, critical, "CRITICAL", f"{server['server_id']} {label} usage reached {value:.0f}%.")
                elif value >= warning:
                    self.create_alert(server["server_id"], resource_type.upper(), value, warning, "WARNING", f"{server['server_id']} {label} usage reached {value:.0f}%.")
                else:
                    with self.connect() as conn:
                        active = conn.execute(
                            "SELECT * FROM alerts WHERE server_id = ? AND resource_type = ? AND status = 'ACTIVE'",
                            (server["server_id"], resource_type.upper()),
                        ).fetchall()
                        for alert in active:
                            if alert["current_value"] < warning:
                                conn.execute(
                                    "UPDATE alerts SET status = 'RESOLVED', resolved_at = ? WHERE id = ?",
                                    (self._now(), alert["id"]),
                                )
                            else:
                                pass

    def get_dashboard_summary(self):
        servers = self.get_servers()
        total_servers = len(servers)
        online_servers = sum(1 for server in servers if server["status"] == "ONLINE")
        warning_servers = sum(1 for server in servers if server["status"] == "WARNING")
        critical_servers = sum(1 for server in servers if server["status"] == "CRITICAL")
        offline_servers = sum(1 for server in servers if server["status"] == "OFFLINE")
        avg_cpu = round(sum(server["cpu_usage"] for server in servers) / total_servers, 2) if total_servers else 0
        avg_memory = round(sum(server["memory_usage"] for server in servers) / total_servers, 2) if total_servers else 0
        avg_disk = round(sum(server["disk_usage"] for server in servers) / total_servers, 2) if total_servers else 0
        avg_network = round(sum(server["network_usage"] for server in servers) / total_servers, 2) if total_servers else 0
        overall_health = round(sum(server["health_score"] for server in servers) / total_servers, 2) if total_servers else 0
        healthy_servers = sum(1 for server in servers if server["health_score"] >= 75 and server["status"] == "ONLINE")

        alerts = self.get_alerts()
        active_alerts = sum(1 for alert in alerts if alert["status"] == "ACTIVE")
        critical_alerts = sum(1 for alert in alerts if alert["status"] == "ACTIVE" and alert["severity"] == "CRITICAL")
        warning_alerts = sum(1 for alert in alerts if alert["status"] == "ACTIVE" and alert["severity"] == "WARNING")
        resolved_alerts = sum(1 for alert in alerts if alert["status"] == "RESOLVED")

        return {
            "total_servers": total_servers,
            "online_servers": online_servers,
            "offline_servers": offline_servers,
            "warning_servers": warning_servers,
            "critical_servers": critical_servers,
            "average_cpu_usage": avg_cpu,
            "average_memory_usage": avg_memory,
            "average_disk_usage": avg_disk,
            "average_network_usage": avg_network,
            "overall_infrastructure_health": overall_health,
            "healthy_servers": healthy_servers,
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "warning_alerts": warning_alerts,
            "resolved_alerts": resolved_alerts,
            "servers": servers,
            "alerts": alerts,
            "thresholds": self.get_threshold_map(),
        }
