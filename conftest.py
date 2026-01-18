# Pytest collection configuration to ignore Django management commands named like tests
collect_ignore_glob = [
    "*/management/commands/test_*.py",
]
