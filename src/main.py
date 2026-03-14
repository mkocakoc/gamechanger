import ctypes
import os
import threading
import time
import tkinter as tk
from typing import Callable
from tkinter import ttk

import psutil

from observability import Observability
from tweaks_engine import TweakEngine
from version import APP_NAME, __version__


class GameChangerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"{APP_NAME} v{__version__} - Game Prep")
        self.root.geometry("880x620")
        self.root.minsize(820, 560)

        self.engine = TweakEngine()
        self.obs = Observability()
        self.proc_map: dict[int, int] = {}
        self.last_snapshot = self.obs.capture_snapshot("app_start")

        self._build_ui()
        self.refresh_process_list()
        self.update_stats_loop()

        if not self.is_admin():
            self.log("Uygulama yonetici olarak calismiyor. Bazi ayarlar kisitli olabilir.")
            self.log("Daha iyi sonuc icin uygulamayi 'Run as administrator' ile ac.")
        else:
            self.log("Yonetici modu aktif.")
        self.log(f"Surum: {__version__}")

    @staticmethod
    def is_admin() -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill="x")

        self.cpu_var = tk.StringVar(value="CPU: -- %")
        self.ram_var = tk.StringVar(value="RAM: -- %")
        self.proc_var = tk.StringVar(value="Process: --")

        ttk.Label(top, textvariable=self.cpu_var, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 18))
        ttk.Label(top, textvariable=self.ram_var, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 18))
        ttk.Label(top, textvariable=self.proc_var, font=("Segoe UI", 11)).pack(side="left")

        body = ttk.Frame(self.root, padding=(12, 6, 12, 12))
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(body)
        right.pack(side="right", fill="both", expand=False, padx=(10, 0))

        ttk.Label(left, text="Kapatilabilir Arka Plan Surecleri", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(
            left,
            text="Ctrl ile birden fazla secim yapabilirsin. Sistem surecleri listelenmez.",
            foreground="#555",
        ).pack(anchor="w", pady=(0, 6))

        list_wrap = ttk.Frame(left)
        list_wrap.pack(fill="both", expand=True)

        self.proc_list = tk.Listbox(list_wrap, selectmode=tk.EXTENDED, font=("Consolas", 10), height=14)
        self.proc_list.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(list_wrap, orient="vertical", command=self.proc_list.yview)
        sb.pack(side="right", fill="y")
        self.proc_list.config(yscrollcommand=sb.set)

        buttons = ttk.Frame(left)
        buttons.pack(fill="x", pady=(8, 0))

        ttk.Button(buttons, text="Listeyi Yenile", command=self.refresh_process_list).pack(side="left")
        ttk.Button(buttons, text="Secilenleri Kapat", command=self.close_selected).pack(side="left", padx=8)

        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=(0, 10))

        ttk.Label(right, text="Hizli Aksiyon", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Button(right, text="Oyun Oncesi Optimize", command=self.optimize_now, width=28).pack(anchor="w", pady=(8, 4))
        ttk.Button(right, text="LoL Client CPU Dusur", command=self.optimize_lol_client, width=28).pack(anchor="w", pady=4)
        ttk.Button(right, text="CS2 CPU/Disk Optimize", command=self.optimize_cs2_client, width=28).pack(anchor="w", pady=4)
        ttk.Button(right, text="HDD Oyun Modu (I/O)", command=self.enable_hdd_game_mode, width=28).pack(anchor="w", pady=4)
        ttk.Button(right, text="HDD Cache Isit (LoL/CS2)", command=self.warm_game_cache, width=28).pack(anchor="w", pady=4)
        ttk.Button(right, text="Windows Hafif Mod", command=self.enable_windows_light_mode, width=28).pack(anchor="w", pady=4)
        ttk.Button(right, text="Windows Normal Mod", command=self.disable_windows_light_mode, width=28).pack(anchor="w", pady=4)
        ttk.Button(right, text="Dry Run (Guvenli Onizleme)", command=self.run_dry_preview, width=28).pack(anchor="w", pady=4)
        ttk.Button(right, text="Kayitli Ayarlari Geri Al", command=self.rollback_safe_tweaks, width=28).pack(anchor="w", pady=4)
        ttk.Button(right, text="Diagnostics Export", command=self.export_diagnostics, width=28).pack(anchor="w", pady=4)

        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=(10, 6))
        ttk.Label(right, text="Profil", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.profile_var = tk.StringVar(value="LOL_SAFE")
        self.profile_combo = ttk.Combobox(
            right,
            textvariable=self.profile_var,
            values=[p.id for p in self.engine.list_profiles()],
            state="readonly",
            width=25,
        )
        self.profile_combo.pack(anchor="w", pady=(4, 6))
        ttk.Button(right, text="Profili Uygula", command=self.apply_selected_profile, width=28).pack(anchor="w", pady=2)
        ttk.Button(right, text="Profili Geri Al", command=self.rollback_selected_profile, width=28).pack(anchor="w", pady=2)
        ttk.Button(right, text="Profil Uyarilarini Goster", command=self.preview_profile_warnings, width=28).pack(anchor="w", pady=2)

        ttk.Button(right, text="Yuksek Performans Plani", command=self.set_high_performance, width=28).pack(anchor="w", pady=4)
        ttk.Button(right, text="Dengeli Plan", command=self.set_balanced, width=28).pack(anchor="w", pady=4)
        ttk.Button(right, text="Gecici Dosya Temizligi", command=self.clean_temp_files, width=28).pack(anchor="w", pady=4)

        ttk.Label(
            right,
            text=(
                "Notlar:\n"
                "- Oyun oncesi optimize: plan + temp temizligi +\n"
                "  secilen surecleri kapatma\n"
                "- HDD modu: arka plan I/O onceligini dusurur\n"
                "- Hafif mod: Windows animasyonlarini azaltir\n"
                "- Dry run: degisiklik oncesi guvenli onizleme\n"
                "- Profiller: LOL_SAFE, CS2_HDD, DESKTOP_LIGHT\n"
                "- Yonetici hakki varsa daha iyi calisir"
            ),
            foreground="#555",
            justify="left",
        ).pack(anchor="w", pady=(14, 0))

        log_frame = ttk.LabelFrame(self.root, text="Islem Gunlugu", padding=(10, 8))
        log_frame.pack(fill="both", expand=False, padx=12, pady=(0, 12))

        self.log_box = tk.Text(log_frame, height=9, wrap="word", font=("Consolas", 9))
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

    def log(self, text: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{ts}] {text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.obs.write_log("INFO", text)

    def _run_action(self, action_name: str, fn: Callable[[], None]) -> None:
        def worker() -> None:
            before = self.obs.capture_snapshot(f"{action_name}_before")
            self.obs.write_log("INFO", "action_start", {"action": action_name, "snapshot": before})
            try:
                fn()
            except Exception as ex:
                self.obs.write_log("ERROR", "action_error", {"action": action_name, "error": str(ex)})
                self.log(f"{action_name} hatasi: {ex}")
            finally:
                after = self.obs.capture_snapshot(f"{action_name}_after")
                delta = self.obs.snapshot_delta(before, after)
                self.last_snapshot = after
                self.obs.write_log(
                    "INFO",
                    "action_end",
                    {"action": action_name, "before": before, "after": after, "delta": delta},
                )
                self.log(
                    f"Snapshot {action_name}: CPU {before['cpu_percent']:.1f}->{after['cpu_percent']:.1f} | "
                    f"RAM {before['ram_percent']:.1f}->{after['ram_percent']:.1f} | "
                    f"PROC {before['process_count']}->{after['process_count']}"
                )

        threading.Thread(target=worker, daemon=True).start()

    def update_stats_loop(self) -> None:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        total_proc = len(psutil.pids())

        self.cpu_var.set(f"CPU: {cpu:.1f} %")
        self.ram_var.set(f"RAM: {ram:.1f} %")
        self.proc_var.set(f"Process: {total_proc}")

        self.root.after(1400, self.update_stats_loop)

    def refresh_process_list(self) -> None:
        self.proc_list.delete(0, "end")
        self.proc_map.clear()

        items = self.engine.get_candidate_processes(current_pid=os.getpid())
        for i, item in enumerate(items):
            name = item.name
            pid = item.pid
            mem_mb = item.mem_mb
            line = f"{name:<20} PID {pid:<7} RAM {mem_mb:>7.1f} MB"
            self.proc_list.insert("end", line)
            self.proc_map[i] = pid

        self.log(f"Surec listesi yenilendi. {len(items)} aday surec bulundu.")

    def set_high_performance(self) -> None:
        def job() -> None:
            code, output = self.engine.set_high_performance()
            if code == 0:
                self.log("Guc plani yuksek performansa alindi.")
            else:
                self.log(f"Guc plani degistirilemedi: {output}")

        self._run_action("set_high_performance", job)

    def set_balanced(self) -> None:
        def job() -> None:
            code, output = self.engine.set_balanced()
            if code == 0:
                self.log("Guc plani dengeli moda alindi.")
            else:
                self.log(f"Guc plani degistirilemedi: {output}")

        self._run_action("set_balanced", job)

    def optimize_lol_client(self) -> None:
        def job() -> None:
            if not self.is_admin():
                self.log("LoL client optimizasyonu icin yonetici izni onerilir.")

            updated, failed = self.engine.optimize_lol_client(self.log)

            if updated == 0 and failed == 0:
                self.log("LoL client sureci bulunamadi.")
                return

            self.log(f"LoL client optimizasyonu tamamlandi. Basarili: {updated}, basarisiz: {failed}.")

        self._run_action("optimize_lol_client", job)

    def optimize_cs2_client(self) -> None:
        def job() -> None:
            updated, failed = self.engine.optimize_cs2_client(self.log)

            if updated == 0 and failed == 0:
                self.log("CS2/Steam sureci bulunamadi.")
                return

            self.log(f"CS2 optimizasyonu tamamlandi. Basarili: {updated}, basarisiz: {failed}.")

        self._run_action("optimize_cs2_client", job)

    def enable_windows_light_mode(self) -> None:
        def job() -> None:
            ok, fail = self.engine.set_windows_visual_effects(light_mode=True)
            self.log(f"Windows hafif mod uygulandi. Basarili ayar: {ok}, basarisiz: {fail}.")
            self.log("Degisikliklerin tam etkisi icin oturumu kapatip ac veya Explorer'i yeniden baslat.")

        self._run_action("enable_windows_light_mode", job)

    def disable_windows_light_mode(self) -> None:
        def job() -> None:
            ok, fail = self.engine.set_windows_visual_effects(light_mode=False)
            self.log(f"Windows normal mod uygulandi. Basarili ayar: {ok}, basarisiz: {fail}.")
            self.log("Degisikliklerin tam etkisi icin oturumu kapatip ac veya Explorer'i yeniden baslat.")

        self._run_action("disable_windows_light_mode", job)

    def run_dry_preview(self) -> None:
        def job() -> None:
            preview_ids = ["power_high_performance", "windows_light_mode", "hdd_game_mode"]
            self.log("Dry run basladi (degisiklik uygulanmaz).")
            for tweak_id in preview_ids:
                result = self.engine.execute_tweak(tweak_id, dry_run=True)
                self.log(result.summary())
                for line in result.messages:
                    self.log(f"  {line}")
            self.log("Dry run tamamlandi.")

        self._run_action("run_dry_preview", job)

    def rollback_safe_tweaks(self) -> None:
        def job() -> None:
            rollback_ids = ["power_high_performance", "power_balanced", "windows_light_mode", "windows_normal_mode"]
            self.log("Kayitli rollback basladi...")
            success = 0
            failed = 0
            for tweak_id in rollback_ids:
                result = self.engine.rollback_tweak(tweak_id, dry_run=False)
                if result.ok:
                    success += 1
                else:
                    failed += 1
                self.log(result.summary())
                for line in result.messages:
                    self.log(f"  {line}")

            self.log(f"Rollback tamamlandi. Basarili: {success}, basarisiz: {failed}.")

        self._run_action("rollback_safe_tweaks", job)

    def _selected_profile_id(self) -> str:
        value = (self.profile_var.get() or "LOL_SAFE").strip()
        return value if value else "LOL_SAFE"

    def preview_profile_warnings(self) -> None:
        def job() -> None:
            profile_id = self._selected_profile_id()
            warnings = self.engine.validate_profile(profile_id)
            if not warnings:
                self.log(f"{profile_id} icin uyari yok.")
                return
            self.log(f"{profile_id} profil uyari listesi:")
            for w in warnings:
                self.log(f"  - {w}")

        self._run_action("preview_profile_warnings", job)

    def apply_selected_profile(self) -> None:
        def job() -> None:
            profile_id = self._selected_profile_id()
            result = self.engine.apply_profile(profile_id, dry_run=False)
            self.log(result.summary())
            for w in result.warnings:
                self.log(f"UYARI: {w}")
            for line in result.messages:
                self.log(f"  {line}")

        self._run_action("apply_selected_profile", job)

    def rollback_selected_profile(self) -> None:
        def job() -> None:
            profile_id = self._selected_profile_id()
            result = self.engine.rollback_profile(profile_id, dry_run=False)
            self.log(result.summary())
            for w in result.warnings:
                self.log(f"UYARI: {w}")
            for line in result.messages:
                self.log(f"  {line}")

        self._run_action("rollback_selected_profile", job)

    def enable_hdd_game_mode(self) -> None:
        def job() -> None:
            self.log("HDD oyun modu basladi...")

            power_ok, output, tuned, failed = self.engine.enable_hdd_game_mode()
            if power_ok:
                self.log("1/2 Guc plani: yuksek performans")
            else:
                self.log(f"1/2 Guc plani gecisi basarisiz: {output}")

            self.log(f"2/2 Arka plan I/O dusurme tamamlandi. Basarili: {tuned}, basarisiz: {failed}.")

        self._run_action("enable_hdd_game_mode", job)

    def warm_game_cache(self) -> None:
        def job() -> None:
            self.log("HDD cache isitma basladi...")

            found, touched, mb = self.engine.warm_game_cache()
            if not found:
                self.log("Otomatik oyun klasoru bulunamadi. Varsayilan LoL/CS2 yollari yok.")
                return
            self.log(f"HDD cache isitma tamamlandi. Islenen dosya: {touched}, okunan veri: {mb:.1f} MB")

        self._run_action("warm_game_cache", job)

    def clean_temp_files(self) -> None:
        def job() -> None:
            total_files, total_dirs, total_errors = self.engine.clean_temp_files()

            self.log(
                f"Temp temizligi tamamlandi. Silinen dosya: {total_files}, klasor: {total_dirs}, atlanan: {total_errors}."
            )

        self._run_action("clean_temp_files", job)

    def close_selected(self) -> None:
        selected = self.proc_list.curselection()
        if not selected:
            self.log("Kapatma icin surec secilmedi.")
            return

        pid_list: list[int] = []
        for idx in selected:
            pid = self.proc_map.get(idx)
            if pid:
                pid_list.append(pid)

        closed, failed = self.engine.close_processes(pid_list, self.log)

        self.log(f"Secilen surecler tamamlandi. Basarili: {closed}, basarisiz: {failed}.")
        self.refresh_process_list()

    def optimize_now(self) -> None:
        def job() -> None:
            self.log("Oyun oncesi optimize basladi...")

            code, output = self.engine.set_high_performance()
            if code == 0:
                self.log("1/3 Guc plani: yuksek performans")
            else:
                self.log(f"1/3 Guc plani gecisi basarisiz: {output}")

            total_files, total_dirs, total_errors = self.engine.clean_temp_files()
            self.log(
                f"2/3 Temp temizligi tamamlandi. Silinen dosya: {total_files}, klasor: {total_dirs}, atlanan: {total_errors}."
            )

            selected = self.proc_list.curselection()
            if selected:
                self.log("3/3 Secilen surecler kapatiliyor")
                pid_list: list[int] = []
                for idx in selected:
                    pid = self.proc_map.get(idx)
                    if pid:
                        pid_list.append(pid)
                closed, failed = self.engine.close_processes(pid_list, self.log)
                self.log(f"Secilen surecler tamamlandi. Basarili: {closed}, basarisiz: {failed}.")
                self.refresh_process_list()
            else:
                self.log("3/3 Surec kapatma atlandi (secim yok)")

            self.log("Optimize adimlari tamamlandi.")

        self._run_action("optimize_now", job)

    def export_diagnostics(self) -> None:
        def job() -> None:
            out_path = self.obs.export_diagnostics(self.engine, latest_snapshot=self.last_snapshot)
            self.log(f"Diagnostics export hazir: {out_path}")

        self._run_action("export_diagnostics", job)


def main() -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    app = GameChangerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
