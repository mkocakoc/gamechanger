import heapq
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import psutil

from app_paths import get_app_base_dir


CANDIDATE_PROCESSES = {
    "chrome.exe",
    "msedge.exe",
    "opera.exe",
    "firefox.exe",
    "discord.exe",
    "steamwebhelper.exe",
    "onedrive.exe",
    "teams.exe",
    "spotify.exe",
    "epicwebhelper.exe",
    "battle.net.exe",
    "adobeipcbroker.exe",
    "gameoverlayui.exe",
}

LOL_CLIENT_PROCESSES = {
    "leagueclient.exe",
    "leagueclientux.exe",
    "leagueclientuxrender.exe",
    "riotclientservices.exe",
}

LOL_RENDER_PROCESS = "leagueclientuxrender.exe"

CS2_PRIORITY_MAP = {
    "cs2.exe": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
    "steam.exe": psutil.BELOW_NORMAL_PRIORITY_CLASS,
    "steamwebhelper.exe": psutil.IDLE_PRIORITY_CLASS,
    "gameoverlayui.exe": psutil.IDLE_PRIORITY_CLASS,
}

HDD_BG_IO_PROCESSES = {
    "chrome.exe",
    "msedge.exe",
    "opera.exe",
    "firefox.exe",
    "discord.exe",
    "teams.exe",
    "onedrive.exe",
    "spotify.exe",
    "adobeipcbroker.exe",
}

GAME_DIR_CANDIDATES = [
    r"C:\Riot Games\League of Legends",
    r"C:\Program Files\Riot Games\League of Legends",
    r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive",
    r"D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive",
    r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive",
]


@dataclass
class ProcessItem:
    name: str
    pid: int
    mem_mb: float


@dataclass
class TweakDefinition:
    id: str
    label: str
    safety_level: str
    requires_admin: bool
    rollback: bool


@dataclass
class TweakResult:
    tweak_id: str
    ok: bool
    dry_run: bool
    changed: int = 0
    failed: int = 0
    messages: list[str] = field(default_factory=list)
    rollback_available: bool = False

    def summary(self) -> str:
        base = f"{self.tweak_id}: {'OK' if self.ok else 'FAIL'}"
        return f"{base} (changed={self.changed}, failed={self.failed}, dry_run={self.dry_run})"


@dataclass
class ProfileDefinition:
    id: str
    label: str
    tweak_ids: list[str]
    rollback_tweak_ids: list[str]


@dataclass
class ProfileResult:
    profile_id: str
    ok: bool
    dry_run: bool
    changed: int
    failed: int
    warnings: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    def summary(self) -> str:
        base = f"profile:{self.profile_id} {'OK' if self.ok else 'FAIL'}"
        return f"{base} (changed={self.changed}, failed={self.failed}, dry_run={self.dry_run})"


class TweakEngine:
    def __init__(self) -> None:
        self.state_dir = get_app_base_dir()
        self.state_file = os.path.join(self.state_dir, "tweak_state.json")
        os.makedirs(self.state_dir, exist_ok=True)
        self.tweaks = self._build_tweak_catalog()
        self.profiles = self._build_profile_catalog()

    def _build_tweak_catalog(self) -> dict[str, TweakDefinition]:
        return {
            "power_high_performance": TweakDefinition(
                id="power_high_performance",
                label="Switch to High Performance power plan",
                safety_level="safe",
                requires_admin=False,
                rollback=True,
            ),
            "power_balanced": TweakDefinition(
                id="power_balanced",
                label="Switch to Balanced power plan",
                safety_level="safe",
                requires_admin=False,
                rollback=True,
            ),
            "windows_light_mode": TweakDefinition(
                id="windows_light_mode",
                label="Reduce Windows visual effects",
                safety_level="safe",
                requires_admin=False,
                rollback=True,
            ),
            "windows_normal_mode": TweakDefinition(
                id="windows_normal_mode",
                label="Restore default Windows visual effects",
                safety_level="safe",
                requires_admin=False,
                rollback=True,
            ),
            "lol_cpu_relief": TweakDefinition(
                id="lol_cpu_relief",
                label="Lower LoL client process priorities",
                safety_level="safe",
                requires_admin=True,
                rollback=False,
            ),
            "cs2_cpu_disk_optimize": TweakDefinition(
                id="cs2_cpu_disk_optimize",
                label="Tune CS2/Steam process priorities and I/O",
                safety_level="safe",
                requires_admin=True,
                rollback=False,
            ),
            "hdd_game_mode": TweakDefinition(
                id="hdd_game_mode",
                label="Reduce background I/O pressure for HDD systems",
                safety_level="safe",
                requires_admin=True,
                rollback=False,
            ),
        }

    def _build_profile_catalog(self) -> dict[str, ProfileDefinition]:
        return {
            "LOL_SAFE": ProfileDefinition(
                id="LOL_SAFE",
                label="LoL guvenli profil",
                tweak_ids=["power_high_performance", "lol_cpu_relief", "windows_light_mode"],
                rollback_tweak_ids=["windows_light_mode", "power_high_performance"],
            ),
            "CS2_HDD": ProfileDefinition(
                id="CS2_HDD",
                label="CS2 HDD profil",
                tweak_ids=["power_high_performance", "hdd_game_mode", "cs2_cpu_disk_optimize", "windows_light_mode"],
                rollback_tweak_ids=["windows_light_mode", "hdd_game_mode", "power_high_performance"],
            ),
            "DESKTOP_LIGHT": ProfileDefinition(
                id="DESKTOP_LIGHT",
                label="Masaustu hafif profil",
                tweak_ids=["windows_light_mode", "power_balanced"],
                rollback_tweak_ids=["windows_light_mode", "power_balanced"],
            ),
        }

    def list_tweaks(self) -> list[TweakDefinition]:
        return [self.tweaks[k] for k in sorted(self.tweaks.keys())]

    def list_profiles(self) -> list[ProfileDefinition]:
        return [self.profiles[k] for k in sorted(self.profiles.keys())]

    def validate_profile(self, profile_id: str) -> list[str]:
        if profile_id not in self.profiles:
            return ["Bilinmeyen profil secildi."]

        warnings: list[str] = []
        running_names = self._running_process_names()

        if profile_id == "LOL_SAFE":
            if not any(name in running_names for name in LOL_CLIENT_PROCESSES):
                warnings.append("LoL client sureci algilanmadi. Profil yine de uygulanabilir.")

        if profile_id == "CS2_HDD":
            cs2_related = {"cs2.exe", "steam.exe", "steamwebhelper.exe", "gameoverlayui.exe"}
            if not any(name in running_names for name in cs2_related):
                warnings.append("CS2/Steam sureci algilanmadi. Profili oyun acmadan hemen once calistirman onerilir.")
            if not self._has_known_game_dir():
                warnings.append("Bilinen LoL/CS2 klasoru bulunamadi. Cache isitma adimi etkisiz kalabilir.")

        if profile_id == "DESKTOP_LIGHT":
            warnings.append("Bu profil goruntusel kaliteyi azaltip akiciligi arttirmayi hedefler.")

        return warnings

    def apply_profile(self, profile_id: str, dry_run: bool = False) -> ProfileResult:
        profile = self.profiles.get(profile_id)
        if profile is None:
            return ProfileResult(
                profile_id=profile_id,
                ok=False,
                dry_run=dry_run,
                changed=0,
                failed=1,
                warnings=["Bilinmeyen profil secildi."],
            )

        warnings = self.validate_profile(profile_id)
        changed = 0
        failed = 0
        messages: list[str] = []

        for tweak_id in profile.tweak_ids:
            result = self.execute_tweak(tweak_id, dry_run=dry_run)
            changed += result.changed
            failed += result.failed
            messages.append(result.summary())
            messages.extend(result.messages)

        return ProfileResult(
            profile_id=profile_id,
            ok=failed == 0,
            dry_run=dry_run,
            changed=changed,
            failed=failed,
            warnings=warnings,
            messages=messages,
        )

    def rollback_profile(self, profile_id: str, dry_run: bool = False) -> ProfileResult:
        profile = self.profiles.get(profile_id)
        if profile is None:
            return ProfileResult(
                profile_id=profile_id,
                ok=False,
                dry_run=dry_run,
                changed=0,
                failed=1,
                warnings=["Bilinmeyen profil secildi."],
            )

        changed = 0
        failed = 0
        messages: list[str] = []
        for tweak_id in profile.rollback_tweak_ids:
            result = self.rollback_tweak(tweak_id, dry_run=dry_run)
            changed += result.changed
            failed += result.failed
            messages.append(result.summary())
            messages.extend(result.messages)

        return ProfileResult(
            profile_id=profile_id,
            ok=failed == 0,
            dry_run=dry_run,
            changed=changed,
            failed=failed,
            messages=messages,
        )

    def _running_process_names(self) -> set[str]:
        names: set[str] = set()
        for proc in psutil.process_iter(["name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name:
                    names.add(name)
            except Exception:
                continue
        return names

    def _has_known_game_dir(self) -> bool:
        return bool(self._existing_game_dirs())

    def _existing_game_dirs(self) -> list[str]:
        return [p for p in GAME_DIR_CANDIDATES if os.path.isdir(p)]

    def execute_tweak(self, tweak_id: str, dry_run: bool = False) -> TweakResult:
        if tweak_id not in self.tweaks:
            return TweakResult(
                tweak_id=tweak_id,
                ok=False,
                dry_run=dry_run,
                failed=1,
                messages=["Unknown tweak id."],
            )

        if tweak_id == "power_high_performance":
            return self._apply_power_tweak(tweak_id, "SCHEME_MIN", dry_run)
        if tweak_id == "power_balanced":
            return self._apply_power_tweak(tweak_id, "SCHEME_BALANCED", dry_run)
        if tweak_id == "windows_light_mode":
            return self._apply_windows_visual_tweak(tweak_id, True, dry_run)
        if tweak_id == "windows_normal_mode":
            return self._apply_windows_visual_tweak(tweak_id, False, dry_run)
        if tweak_id == "lol_cpu_relief":
            return self._apply_lol_cpu_relief(dry_run)
        if tweak_id == "cs2_cpu_disk_optimize":
            return self._apply_cs2_optimize(dry_run)
        if tweak_id == "hdd_game_mode":
            return self._apply_hdd_game_mode(dry_run)

        return TweakResult(
            tweak_id=tweak_id,
            ok=False,
            dry_run=dry_run,
            failed=1,
            messages=["No handler implemented for tweak id."],
        )

    def rollback_tweak(self, tweak_id: str, dry_run: bool = False) -> TweakResult:
        if tweak_id in ("power_high_performance", "power_balanced", "hdd_game_mode"):
            return self._rollback_power_tweak(tweak_id, dry_run)
        if tweak_id in ("windows_light_mode", "windows_normal_mode"):
            return self._rollback_windows_visual_tweak(tweak_id, dry_run)

        return TweakResult(
            tweak_id=tweak_id,
            ok=False,
            dry_run=dry_run,
            failed=1,
            messages=["Rollback not supported for this tweak."],
        )

    def _load_state(self) -> dict:
        if not os.path.isfile(self.state_file):
            return {"tweaks": {}}
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {"tweaks": {}}
            if "tweaks" not in data or not isinstance(data["tweaks"], dict):
                data["tweaks"] = {}
            return data
        except Exception:
            return {"tweaks": {}}

    def _save_state(self, data: dict) -> None:
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _remember_state(self, tweak_id: str, payload: dict) -> None:
        data = self._load_state()
        data["tweaks"][tweak_id] = {
            "timestamp": int(time.time()),
            "payload": payload,
        }
        self._save_state(data)

    def _get_tweak_state(self, tweak_id: str) -> Optional[dict]:
        data = self._load_state()
        entry = data.get("tweaks", {}).get(tweak_id)
        if not isinstance(entry, dict):
            return None
        payload = entry.get("payload")
        if not isinstance(payload, dict):
            return None
        return payload

    def _extract_power_guid(self, text: str) -> Optional[str]:
        match = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", text)
        if not match:
            return None
        return match.group(1)

    def _get_active_power_scheme(self) -> tuple[bool, str]:
        code, output = self.run_cmd(["powercfg", "/GETACTIVESCHEME"])
        if code != 0:
            return False, output
        guid = self._extract_power_guid(output)
        if not guid:
            return False, output
        return True, guid

    def _set_power_scheme_by_id(self, scheme_id: str, dry_run: bool) -> TweakResult:
        if dry_run:
            return TweakResult(
                tweak_id="_set_power_scheme",
                ok=True,
                dry_run=True,
                changed=1,
                messages=[f"Would run: powercfg /S {scheme_id}"],
            )
        code, output = self.run_cmd(["powercfg", "/S", scheme_id])
        return TweakResult(
            tweak_id="_set_power_scheme",
            ok=code == 0,
            dry_run=False,
            changed=1 if code == 0 else 0,
            failed=0 if code == 0 else 1,
            messages=[output] if output else [],
        )

    def _apply_power_tweak(self, tweak_id: str, target_scheme: str, dry_run: bool) -> TweakResult:
        got_current, current_or_msg = self._get_active_power_scheme()
        if not got_current:
            return TweakResult(
                tweak_id=tweak_id,
                ok=False,
                dry_run=dry_run,
                failed=1,
                messages=[f"Could not read current power plan: {current_or_msg}"],
            )

        if dry_run:
            return TweakResult(
                tweak_id=tweak_id,
                ok=True,
                dry_run=True,
                changed=1,
                rollback_available=True,
                messages=[
                    f"Would switch power plan to {target_scheme}.",
                    f"Would save rollback GUID: {current_or_msg}",
                ],
            )

        set_result = self._set_power_scheme_by_id(target_scheme, dry_run=False)
        ok = set_result.ok
        messages = [f"Target scheme: {target_scheme}"]
        messages.extend(set_result.messages)
        if ok:
            self._remember_state(tweak_id, {"previous_scheme_guid": current_or_msg})

        return TweakResult(
            tweak_id=tweak_id,
            ok=ok,
            dry_run=False,
            changed=1 if ok else 0,
            failed=0 if ok else 1,
            rollback_available=ok,
            messages=messages,
        )

    def _rollback_power_tweak(self, tweak_id: str, dry_run: bool) -> TweakResult:
        state = self._get_tweak_state(tweak_id)
        if not state:
            return TweakResult(
                tweak_id=tweak_id,
                ok=False,
                dry_run=dry_run,
                failed=1,
                messages=["No saved rollback state found."],
            )
        guid = state.get("previous_scheme_guid")
        if not isinstance(guid, str) or not guid:
            return TweakResult(
                tweak_id=tweak_id,
                ok=False,
                dry_run=dry_run,
                failed=1,
                messages=["Rollback state is missing previous power scheme GUID."],
            )

        if dry_run:
            return TweakResult(
                tweak_id=tweak_id,
                ok=True,
                dry_run=True,
                changed=1,
                messages=[f"Would rollback power plan to GUID {guid}"],
            )

        set_result = self._set_power_scheme_by_id(guid, dry_run=False)
        return TweakResult(
            tweak_id=tweak_id,
            ok=set_result.ok,
            dry_run=False,
            changed=1 if set_result.ok else 0,
            failed=0 if set_result.ok else 1,
            messages=set_result.messages or [f"Rollback target GUID: {guid}"],
        )

    def _query_reg_value(self, key: str, value_name: str) -> Optional[str]:
        code, output = self.run_cmd(["reg", "query", key, "/v", value_name])
        if code != 0 or not output:
            return None
        for line in output.splitlines():
            if value_name.lower() not in line.lower():
                continue
            parts = line.split()
            if len(parts) >= 3:
                return parts[-1]
        return None

    def _set_reg_value(self, key: str, value_name: str, reg_type: str, value: str, dry_run: bool) -> tuple[bool, str]:
        if dry_run:
            return True, f"Would set {key}\\{value_name}={value} ({reg_type})"
        code, output = self.run_cmd(
            ["reg", "add", key, "/v", value_name, "/t", reg_type, "/d", value, "/f"]
        )
        return code == 0, output

    def _visual_targets(self, light_mode: bool) -> dict[str, tuple[str, str, str]]:
        if light_mode:
            min_animate = "0"
            taskbar_animations = "0"
            transparency = "0"
        else:
            min_animate = "1"
            taskbar_animations = "1"
            transparency = "1"

        return {
            "MinAnimate": (r"HKCU\Control Panel\Desktop\WindowMetrics", "REG_SZ", min_animate),
            "TaskbarAnimations": (
                r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "REG_DWORD",
                taskbar_animations,
            ),
            "EnableTransparency": (
                r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                "REG_DWORD",
                transparency,
            ),
        }

    def _apply_windows_visual_tweak(self, tweak_id: str, light_mode: bool, dry_run: bool) -> TweakResult:
        targets = self._visual_targets(light_mode)
        previous: dict[str, dict[str, str]] = {}
        messages: list[str] = []

        for value_name, (key, reg_type, new_value) in targets.items():
            prev = self._query_reg_value(key, value_name)
            if prev is not None:
                previous[value_name] = {"key": key, "type": reg_type, "value": prev}

            ok, msg = self._set_reg_value(key, value_name, reg_type, new_value, dry_run)
            messages.append(msg)
            if not ok:
                return TweakResult(
                    tweak_id=tweak_id,
                    ok=False,
                    dry_run=dry_run,
                    changed=0,
                    failed=1,
                    messages=messages,
                )

        if not dry_run:
            self._remember_state(tweak_id, {"previous": previous})

        return TweakResult(
            tweak_id=tweak_id,
            ok=True,
            dry_run=dry_run,
            changed=len(targets),
            failed=0,
            rollback_available=True,
            messages=messages,
        )

    def _rollback_windows_visual_tweak(self, tweak_id: str, dry_run: bool) -> TweakResult:
        state = self._get_tweak_state(tweak_id)
        if not state:
            return TweakResult(
                tweak_id=tweak_id,
                ok=False,
                dry_run=dry_run,
                failed=1,
                messages=["No saved rollback state found."],
            )

        previous = state.get("previous")
        if not isinstance(previous, dict) or not previous:
            return TweakResult(
                tweak_id=tweak_id,
                ok=False,
                dry_run=dry_run,
                failed=1,
                messages=["Rollback state has no previous registry values."],
            )

        changed = 0
        failed = 0
        messages: list[str] = []
        for value_name, rec in previous.items():
            if not isinstance(rec, dict):
                failed += 1
                continue
            key = rec.get("key")
            reg_type = rec.get("type")
            old_value = rec.get("value")
            if not isinstance(key, str) or not isinstance(reg_type, str) or old_value is None:
                failed += 1
                continue

            ok, msg = self._set_reg_value(key, value_name, reg_type, str(old_value), dry_run)
            messages.append(msg)
            if ok:
                changed += 1
            else:
                failed += 1

        return TweakResult(
            tweak_id=tweak_id,
            ok=failed == 0,
            dry_run=dry_run,
            changed=changed,
            failed=failed,
            messages=messages,
        )

    def _apply_lol_cpu_relief(self, dry_run: bool) -> TweakResult:
        updated = 0
        failed = 0
        messages: list[str] = []

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name not in LOL_CLIENT_PROCESSES:
                    continue

                p = psutil.Process(proc.info["pid"])
                if name == LOL_RENDER_PROCESS:
                    target = psutil.IDLE_PRIORITY_CLASS
                else:
                    target = psutil.BELOW_NORMAL_PRIORITY_CLASS

                if dry_run:
                    messages.append(f"Would set priority: {name} (PID {p.pid}) -> {target}")
                else:
                    p.nice(target)
                    messages.append(f"Priority updated: {name} (PID {p.pid})")
                updated += 1
            except Exception as ex:
                messages.append(f"Priority update failed: {proc.info.get('name')} - {ex}")
                failed += 1

        return TweakResult(
            tweak_id="lol_cpu_relief",
            ok=failed == 0,
            dry_run=dry_run,
            changed=updated,
            failed=failed,
            rollback_available=False,
            messages=messages,
        )

    def _apply_cs2_optimize(self, dry_run: bool) -> TweakResult:
        updated = 0
        failed = 0
        messages: list[str] = []

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                priority = CS2_PRIORITY_MAP.get(name)
                if priority is None:
                    continue

                p = psutil.Process(proc.info["pid"])
                if dry_run:
                    messages.append(f"Would set CS2 tuning: {name} (PID {p.pid})")
                else:
                    p.nice(priority)
                    if name != "cs2.exe":
                        p.ionice(psutil.IOPRIO_VERYLOW)
                    messages.append(f"CS2 tuning applied: {name} (PID {p.pid})")
                updated += 1
            except Exception as ex:
                messages.append(f"CS2 tuning failed: {proc.info.get('name')} - {ex}")
                failed += 1

        return TweakResult(
            tweak_id="cs2_cpu_disk_optimize",
            ok=failed == 0,
            dry_run=dry_run,
            changed=updated,
            failed=failed,
            rollback_available=False,
            messages=messages,
        )

    def _apply_hdd_game_mode(self, dry_run: bool) -> TweakResult:
        power_result = self._apply_power_tweak("hdd_game_mode", "SCHEME_MIN", dry_run)
        tuned = 0
        failed = power_result.failed
        messages = list(power_result.messages)

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name not in HDD_BG_IO_PROCESSES:
                    continue
                p = psutil.Process(proc.info["pid"])

                if dry_run:
                    messages.append(f"Would set I/O idle: {name} (PID {p.pid})")
                else:
                    p.nice(psutil.IDLE_PRIORITY_CLASS)
                    p.ionice(psutil.IOPRIO_VERYLOW)
                    messages.append(f"I/O lowered: {name} (PID {p.pid})")
                tuned += 1
            except Exception as ex:
                messages.append(f"I/O lowering failed: {proc.info.get('name')} - {ex}")
                failed += 1

        return TweakResult(
            tweak_id="hdd_game_mode",
            ok=failed == 0,
            dry_run=dry_run,
            changed=tuned + power_result.changed,
            failed=failed,
            rollback_available=power_result.rollback_available,
            messages=messages,
        )

    def run_cmd(self, cmd: list[str]) -> tuple[int, str]:
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True, shell=False)
            out = (cp.stdout or "").strip()
            err = (cp.stderr or "").strip()
            return cp.returncode, out if out else err
        except Exception as ex:
            return 1, str(ex)

    def get_candidate_processes(self, current_pid: int) -> list[ProcessItem]:
        items: list[ProcessItem] = []

        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                pid = proc.info["pid"]
                if pid == current_pid:
                    continue

                name = (proc.info.get("name") or "").lower()
                if name not in CANDIDATE_PROCESSES:
                    continue

                mem_mb = 0.0
                mem_info = proc.info.get("memory_info")
                if mem_info:
                    mem_mb = mem_info.rss / 1024 / 1024

                items.append(ProcessItem(name=name, pid=pid, mem_mb=mem_mb))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        items.sort(key=lambda x: (x.name, -x.mem_mb))
        return items

    def set_high_performance(self) -> tuple[int, str]:
        result = self.execute_tweak("power_high_performance", dry_run=False)
        return (0 if result.ok else 1, " | ".join(result.messages) if result.messages else result.summary())

    def set_balanced(self) -> tuple[int, str]:
        result = self.execute_tweak("power_balanced", dry_run=False)
        return (0 if result.ok else 1, " | ".join(result.messages) if result.messages else result.summary())

    def optimize_lol_client(self, log: Callable[[str], None]) -> tuple[int, int]:
        result = self.execute_tweak("lol_cpu_relief", dry_run=False)
        for line in result.messages:
            log(line)
        return result.changed, result.failed

    def optimize_cs2_client(self, log: Callable[[str], None]) -> tuple[int, int]:
        result = self.execute_tweak("cs2_cpu_disk_optimize", dry_run=False)
        for line in result.messages:
            log(line)
        return result.changed, result.failed

    def set_windows_visual_effects(self, light_mode: bool) -> tuple[int, int]:
        tweak_id = "windows_light_mode" if light_mode else "windows_normal_mode"
        result = self.execute_tweak(tweak_id, dry_run=False)
        return result.changed, result.failed

    def enable_hdd_game_mode(self) -> tuple[bool, str, int, int]:
        result = self.execute_tweak("hdd_game_mode", dry_run=False)
        power_ok = result.ok
        output = " | ".join(result.messages) if result.messages else result.summary()
        tuned = result.changed
        failed = result.failed
        return power_ok, output, tuned, failed

    def warm_game_cache(self) -> tuple[bool, int, float]:
        game_dirs = self._existing_game_dirs()
        if not game_dirs:
            return False, 0, 0.0

        file_heap: list[tuple[int, str]] = []
        valid_ext = {".vpk", ".wad", ".wad.client", ".pak", ".bin", ".dat"}

        for gdir in game_dirs:
            for root, _, files in os.walk(gdir):
                for name in files:
                    path = os.path.join(root, name)
                    lower = name.lower()
                    ext = os.path.splitext(lower)[1]
                    if ext in valid_ext or lower.endswith(".wad.client"):
                        try:
                            size = os.path.getsize(path)
                            if size > 0:
                                file_heap.append((size, path))
                        except OSError:
                            continue

        if not file_heap:
            return False, 0, 0.0

        largest = heapq.nlargest(60, file_heap, key=lambda x: x[0])
        total_target = 1024 * 1024 * 768
        chunk_size = 1024 * 1024 * 8
        total_read = 0
        touched = 0

        for _, path in largest:
            if total_read >= total_target:
                break
            try:
                with open(path, "rb") as f:
                    data = f.read(chunk_size)
                    total_read += len(data)
                touched += 1
            except OSError:
                continue

        mb = total_read / 1024 / 1024
        return True, touched, mb

    def clean_temp_files(self) -> tuple[int, int, int]:
        total_files = 0
        total_dirs = 0
        total_errors = 0

        temp_paths = [
            tempfile.gettempdir(),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Temp"),
        ]

        seen: set[str] = set()
        for temp_path in temp_paths:
            if not os.path.isdir(temp_path):
                continue
            if temp_path in seen:
                continue
            seen.add(temp_path)

            for entry in os.listdir(temp_path):
                full = os.path.join(temp_path, entry)
                try:
                    if os.path.isfile(full) or os.path.islink(full):
                        os.remove(full)
                        total_files += 1
                    elif os.path.isdir(full):
                        shutil.rmtree(full, ignore_errors=False)
                        total_dirs += 1
                except Exception:
                    total_errors += 1

        return total_files, total_dirs, total_errors

    def close_processes(self, pids: list[int], log: Callable[[str], None]) -> tuple[int, int]:
        closed = 0
        failed = 0

        for pid in pids:
            try:
                p = psutil.Process(pid)
                name = p.name()
                p.terminate()
                try:
                    p.wait(timeout=3)
                except psutil.TimeoutExpired:
                    p.kill()
                log(f"Surec kapatildi: {name} (PID {pid})")
                closed += 1
            except Exception as ex:
                log(f"Surec kapatilamadi (PID {pid}): {ex}")
                failed += 1

        return closed, failed
