import os


def get_app_base_dir() -> str:
    return os.path.join(os.environ.get("APPDATA", os.getcwd()), "GameChanger")


def ensure_app_dirs() -> tuple[str, str, str]:
    base_dir = get_app_base_dir()
    logs_dir = os.path.join(base_dir, "logs")
    diag_dir = os.path.join(base_dir, "diagnostics")
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(diag_dir, exist_ok=True)
    return base_dir, logs_dir, diag_dir
