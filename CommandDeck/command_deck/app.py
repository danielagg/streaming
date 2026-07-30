from __future__ import annotations

import argparse
import ctypes
import queue
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from typing import Any, Callable

from .audio import WindowsAudioPlayer
from .config import ActionDefinition, AppConfig, load_config
from .remix import RemixClient, RemixConnectionError, RemixProtocolError


APP_DIRECTORY = Path(__file__).resolve().parent.parent
CONFIG_PATH = APP_DIRECTORY / "config.json"

COLORS = {
    "background": "#090D12",
    "panel": "#111820",
    "panel_hover": "#17212B",
    "panel_active": "#1C2732",
    "border": "#273442",
    "border_bright": "#3B4B5B",
    "text": "#EDF3F7",
    "muted": "#8996A3",
    "dim": "#53606D",
    "green": "#91C47B",
    "amber": "#D5A653",
    "red": "#D66B6B",
}


class ActionCard(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        action: ActionDefinition,
        callback: Callable[[ActionDefinition], None],
        fonts: dict[str, tkfont.Font],
    ) -> None:
        super().__init__(
            parent,
            background=COLORS["background"],
            borderwidth=0,
            highlightthickness=0,
            cursor="hand2",
            height=320,
        )
        self.action = action
        self._callback = callback
        self._fonts = fonts
        self._hovered = False
        self._enabled = True
        self._active = False

        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def set_state(self, *, enabled: bool, active: bool = False) -> None:
        self._enabled = enabled
        self._active = active
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def _on_enter(self, _event: tk.Event[Any]) -> None:
        self._hovered = True
        self._draw()

    def _on_leave(self, _event: tk.Event[Any]) -> None:
        self._hovered = False
        self._draw()

    def _on_click(self, _event: tk.Event[Any]) -> None:
        if self._enabled:
            self._callback(self.action)

    def _rounded_rectangle(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius: float,
        **kwargs: Any,
    ) -> int:
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _draw(self, _event: tk.Event[Any] | None = None) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 280)
        height = max(self.winfo_height(), 300)

        if not self._enabled:
            fill = COLORS["panel"]
            outline = COLORS["border"]
        elif self._active:
            fill = COLORS["panel_active"]
            outline = self.action.accent
        elif self._hovered:
            fill = COLORS["panel_hover"]
            outline = COLORS["border_bright"]
        else:
            fill = COLORS["panel"]
            outline = COLORS["border"]

        self._rounded_rectangle(
            2,
            2,
            width - 2,
            height - 2,
            12,
            fill=fill,
            outline=outline,
            width=2 if self._active else 1,
        )
        self.create_rectangle(
            18,
            18,
            22,
            72,
            fill=self.action.accent if self._enabled else COLORS["dim"],
            outline="",
        )

        text_color = COLORS["text"] if self._enabled else COLORS["dim"]
        secondary = COLORS["muted"] if self._enabled else COLORS["dim"]

        self.create_text(
            40,
            23,
            text=self.action.number,
            anchor="nw",
            fill=self.action.accent if self._enabled else COLORS["dim"],
            font=self._fonts["micro_bold"],
        )
        self.create_text(
            width - 24,
            23,
            text=f"{self.action.duration_ms / 1000:g} SEC",
            anchor="ne",
            fill=secondary,
            font=self._fonts["micro"],
        )
        self.create_text(
            24,
            110,
            text=self.action.name.upper(),
            anchor="nw",
            width=width - 48,
            fill=text_color,
            font=self._fonts["card_title"],
        )
        self.create_text(
            24,
            185,
            text=self.action.description,
            anchor="nw",
            width=width - 48,
            fill=secondary,
            font=self._fonts["body"],
        )

        line_y = height - 66
        self.create_line(
            24,
            line_y,
            width - 24,
            line_y,
            fill=COLORS["border"],
        )
        if self._active:
            command_text = "●  RUNNING"
            command_color = self.action.accent
        elif self._enabled:
            command_text = "EXECUTE ACTION"
            command_color = self.action.accent
        else:
            command_text = "ACTION LOCKED"
            command_color = COLORS["dim"]

        self.create_text(
            24,
            height - 39,
            text=command_text,
            anchor="w",
            fill=command_color,
            font=self._fonts["micro_bold"],
        )
        self.create_text(
            width - 24,
            height - 39,
            text="→",
            anchor="e",
            fill=command_color,
            font=self._fonts["arrow"],
        )


class CommandDeckApp:
    def __init__(
        self,
        root: tk.Tk,
        config: AppConfig,
        *,
        enable_services: bool = True,
    ) -> None:
        self.root = root
        self.config = config
        self.enable_services = enable_services
        self.client = RemixClient(config.websocket_url)
        self.audio = WindowsAudioPlayer()
        self._work_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._ui_queue: queue.Queue[tuple[Any, ...]] = queue.Queue()
        self._stop_event = threading.Event()
        self._busy_action_id: str | None = None
        self._last_normal_state: str | None = None
        self._cards: dict[str, ActionCard] = {}
        self._clock_after_id: str | None = None
        self._queue_after_id: str | None = None
        self._health_after_id: str | None = None
        self._countdown_after_id: str | None = None
        self._countdown_end: float | None = None

        self._configure_window()
        self._fonts = self._create_fonts()
        self._build_interface()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._update_clock()
        self._poll_ui_queue()

        if enable_services:
            self._worker = threading.Thread(
                target=self._worker_loop,
                name="command-deck-worker",
                daemon=True,
            )
            self._worker.start()
            self._set_connection_status(
                "CONNECTING", COLORS["amber"], "Contacting PNGTuber Remix…"
            )
            self._work_queue.put(("connect", None))
            self._schedule_health_check()
        else:
            self._set_connection_status(
                "PREVIEW", COLORS["amber"], "Interface smoke test"
            )
            self._set_activity(
                "PREVIEW MODE",
                "Layout initialized. External services are disabled.",
            )

    def _configure_window(self) -> None:
        self.root.title(self.config.app_name)
        self.root.configure(background=COLORS["background"])
        self.root.geometry("1180x720")
        self.root.minsize(940, 620)
        self.root.option_add("*tearOff", False)

        try:
            icon_path = (
                APP_DIRECTORY.parent / "Berry" / "ProfilePic.png"
            ).resolve()
            if icon_path.is_file():
                self._icon_image = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, self._icon_image)
        except tk.TclError:
            self._icon_image = None

    def _create_fonts(self) -> dict[str, tkfont.Font]:
        return {
            "kicker": tkfont.Font(
                family="Cascadia Mono", size=9, weight="bold"
            ),
            "title": tkfont.Font(
                family="Segoe UI Semibold", size=28, weight="bold"
            ),
            "section": tkfont.Font(
                family="Segoe UI Semibold", size=15, weight="bold"
            ),
            "card_title": tkfont.Font(
                family="Segoe UI Semibold", size=22, weight="bold"
            ),
            "body": tkfont.Font(family="Segoe UI", size=10),
            "micro": tkfont.Font(family="Cascadia Mono", size=8),
            "micro_bold": tkfont.Font(
                family="Cascadia Mono", size=8, weight="bold"
            ),
            "status": tkfont.Font(
                family="Cascadia Mono", size=9, weight="bold"
            ),
            "arrow": tkfont.Font(
                family="Segoe UI Semibold", size=17, weight="bold"
            ),
            "clock": tkfont.Font(
                family="Cascadia Mono", size=15, weight="bold"
            ),
        }

    def _build_interface(self) -> None:
        shell = tk.Frame(self.root, background=COLORS["background"])
        shell.pack(fill="both", expand=True, padx=42, pady=(30, 26))

        header = tk.Frame(shell, background=COLORS["background"])
        header.pack(fill="x")
        header.grid_columnconfigure(0, weight=1)

        brand = tk.Frame(header, background=COLORS["background"])
        brand.grid(row=0, column=0, sticky="w")
        tk.Label(
            brand,
            text="STREAM OPERATIONS  /  CONTROL SURFACE",
            background=COLORS["background"],
            foreground=COLORS["green"],
            font=self._fonts["kicker"],
        ).pack(anchor="w")
        tk.Label(
            brand,
            text="COMMAND DECK",
            background=COLORS["background"],
            foreground=COLORS["text"],
            font=self._fonts["title"],
        ).pack(anchor="w", pady=(4, 0))

        telemetry = tk.Frame(header, background=COLORS["background"])
        telemetry.grid(row=0, column=1, sticky="e")
        self._clock_label = tk.Label(
            telemetry,
            text="--:--:--",
            background=COLORS["background"],
            foreground=COLORS["text"],
            font=self._fonts["clock"],
        )
        self._clock_label.pack(anchor="e")

        connection_row = tk.Frame(
            telemetry, background=COLORS["background"], cursor="hand2"
        )
        connection_row.pack(anchor="e", pady=(8, 0))
        self._connection_dot = tk.Label(
            connection_row,
            text="●",
            background=COLORS["background"],
            foreground=COLORS["amber"],
            font=self._fonts["micro_bold"],
        )
        self._connection_dot.pack(side="left", padx=(0, 7))
        self._connection_label = tk.Label(
            connection_row,
            text="CONNECTING",
            background=COLORS["background"],
            foreground=COLORS["muted"],
            font=self._fonts["status"],
        )
        self._connection_label.pack(side="left")
        connection_row.bind("<Button-1>", self._request_reconnect)
        self._connection_dot.bind("<Button-1>", self._request_reconnect)
        self._connection_label.bind("<Button-1>", self._request_reconnect)

        endpoint = self.config.websocket_url.removeprefix("ws://")
        self._endpoint_label = tk.Label(
            telemetry,
            text=f"REMIX  /  {endpoint}",
            background=COLORS["background"],
            foreground=COLORS["dim"],
            font=self._fonts["micro"],
        )
        self._endpoint_label.pack(anchor="e", pady=(3, 0))

        tk.Frame(
            shell, background=COLORS["border"], height=1
        ).pack(fill="x", pady=(24, 24))

        section_header = tk.Frame(shell, background=COLORS["background"])
        section_header.pack(fill="x", pady=(0, 14))
        tk.Label(
            section_header,
            text="BERRY ANIMATIONS",
            background=COLORS["background"],
            foreground=COLORS["text"],
            font=self._fonts["section"],
        ).pack(side="left")
        tk.Label(
            section_header,
            text=f"{len(self.config.actions):02d}  ASSIGNED ACTIONS",
            background=COLORS["background"],
            foreground=COLORS["dim"],
            font=self._fonts["micro"],
        ).pack(side="right", pady=(5, 0))

        cards = tk.Frame(shell, background=COLORS["background"])
        cards.pack(fill="both", expand=True)
        for index, action in enumerate(self.config.actions):
            cards.grid_columnconfigure(index, weight=1, uniform="actions")
            card = ActionCard(
                cards, action, self.request_action, self._fonts
            )
            horizontal_padding = (0, 9) if index == 0 else (9, 9)
            if index == len(self.config.actions) - 1:
                horizontal_padding = (9, 0)
            card.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=horizontal_padding,
            )
            self._cards[action.id] = card
        cards.grid_rowconfigure(0, weight=1)

        activity = tk.Frame(
            shell,
            background=COLORS["panel"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        activity.pack(fill="x", pady=(20, 0))
        tk.Label(
            activity,
            text="SYSTEM FEED",
            background=COLORS["panel"],
            foreground=COLORS["dim"],
            font=self._fonts["micro_bold"],
            width=17,
            anchor="w",
        ).pack(side="left", padx=(16, 0), pady=12)
        self._activity_code = tk.Label(
            activity,
            text="BOOT",
            background=COLORS["panel"],
            foreground=COLORS["amber"],
            font=self._fonts["micro_bold"],
            width=14,
            anchor="w",
        )
        self._activity_code.pack(side="left", pady=12)
        self._activity_message = tk.Label(
            activity,
            text="Initializing Command Deck…",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            font=self._fonts["body"],
            anchor="w",
        )
        self._activity_message.pack(
            side="left", fill="x", expand=True, padx=(0, 16), pady=12
        )

    def request_action(self, action: ActionDefinition) -> None:
        if not self.enable_services:
            return
        if self._busy_action_id is not None:
            active = self._action_by_id(self._busy_action_id)
            self._set_activity(
                "BUSY",
                f"{active.name} is already running. Wait for it to finish.",
            )
            return

        self._busy_action_id = action.id
        self._set_cards_busy(action.id)
        self._set_connection_status(
            "EXECUTING", action.accent, f"Running {action.name}…"
        )
        self._set_activity(
            "QUEUED",
            f"{action.name} sent to the action controller.",
        )
        self._work_queue.put(("action", action))

    def _request_reconnect(self, _event: tk.Event[Any] | None = None) -> None:
        if not self.enable_services or self._busy_action_id is not None:
            return
        self._set_connection_status(
            "CONNECTING", COLORS["amber"], "Contacting PNGTuber Remix…"
        )
        self._set_activity(
            "RECONNECT", "Retrying the local Remix connection."
        )
        self._work_queue.put(("connect", None))

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                job, payload = self._work_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                if job == "connect":
                    self._connect_and_validate()
                elif job == "health":
                    self._check_health()
                elif job == "action":
                    self._execute_action(payload)
            finally:
                self._work_queue.task_done()

    def _connect_and_validate(self) -> None:
        try:
            self.client.connect()
            states = self.client.list_states()
            available_names = {
                str(state.get("name")) for state in states if state.get("name")
            }
            missing = [
                action.state_name
                for action in self.config.actions
                if action.state_name not in available_names
            ]
            if missing:
                missing_text = ", ".join(missing)
                self._ui_queue.put(
                    (
                        "connection",
                        "CONFIG ERROR",
                        COLORS["red"],
                        f"Missing Remix state(s): {missing_text}",
                    )
                )
                return

            self._ui_queue.put(
                (
                    "connection",
                    "ONLINE",
                    COLORS["green"],
                    f"Remix online. {len(states)} states reported.",
                )
            )
        except (RemixConnectionError, RemixProtocolError) as error:
            self.client.close()
            self._ui_queue.put(
                (
                    "connection",
                    "OFFLINE",
                    COLORS["red"],
                    f"{error} Click OFFLINE to retry.",
                )
            )

    def _check_health(self) -> None:
        if self._busy_action_id is not None:
            return
        try:
            states = self.client.list_states()
            self._ui_queue.put(
                (
                    "connection",
                    "ONLINE",
                    COLORS["green"],
                    f"Remix online. {len(states)} states reported.",
                )
            )
        except (RemixConnectionError, RemixProtocolError) as error:
            self.client.close()
            self._ui_queue.put(
                (
                    "connection",
                    "OFFLINE",
                    COLORS["red"],
                    f"{error} Click OFFLINE to retry.",
                )
            )

    def _execute_action(self, action: ActionDefinition) -> None:
        normal_state: str | None = None
        state_changed = False
        failure: Exception | None = None

        try:
            states = self.client.list_states()
            available_names = {
                str(state.get("name")) for state in states if state.get("name")
            }
            if action.state_name not in available_names:
                raise RuntimeError(
                    f"Remix has no state named '{action.state_name}'."
                )

            action_states = {
                definition.state_name for definition in self.config.actions
            }
            current = next(
                (state for state in states if state.get("is_current")),
                None,
            )
            if current and current.get("name") not in action_states:
                normal_state = str(current["name"])
            elif (
                self._last_normal_state
                and self._last_normal_state in available_names
            ):
                normal_state = self._last_normal_state
            else:
                fallback = next(
                    (
                        state
                        for state in states
                        if state.get("name") not in action_states
                    ),
                    None,
                )
                if fallback:
                    normal_state = str(fallback["name"])

            if not normal_state:
                raise RuntimeError(
                    "Remix has no normal state to return to after the action."
                )
            self._last_normal_state = normal_state

            self.client.set_state(action.state_name)
            state_changed = True
            if action.audio_path is not None:
                self.audio.play(action.audio_path)

            self._ui_queue.put(
                (
                    "action_started",
                    action.id,
                    action.name,
                    normal_state,
                    action.duration_ms,
                )
            )
            self._stop_event.wait(action.duration_ms / 1000)
        except Exception as error:
            failure = error
        finally:
            try:
                self.audio.stop()
            except Exception as error:
                if failure is None:
                    failure = error

            if state_changed and normal_state:
                try:
                    self.client.set_state(normal_state)
                except Exception as error:
                    if failure is None:
                        failure = error

        if failure is None:
            self._ui_queue.put(
                ("action_complete", action.id, action.name, normal_state)
            )
        else:
            connection_failure = isinstance(
                failure, (RemixConnectionError, RemixProtocolError)
            )
            if connection_failure:
                self.client.close()
            self._ui_queue.put(
                (
                    "action_error",
                    action.id,
                    action.name,
                    str(failure),
                    connection_failure,
                )
            )

    def _poll_ui_queue(self) -> None:
        try:
            while True:
                event = self._ui_queue.get_nowait()
                event_name = event[0]
                if event_name == "connection":
                    _, label, color, message = event
                    if self._busy_action_id is None:
                        self._set_connection_status(label, color, message)
                        self._set_activity(label, message)
                elif event_name == "action_started":
                    _, action_id, action_name, normal_state, duration_ms = event
                    if self._busy_action_id == action_id:
                        self._countdown_end = (
                            time.monotonic() + duration_ms / 1000
                        )
                        self._set_activity(
                            "RUNNING",
                            f"{action_name} active. Return state: {normal_state}.",
                        )
                        self._update_countdown()
                elif event_name == "action_complete":
                    _, action_id, action_name, normal_state = event
                    if self._busy_action_id == action_id:
                        self._finish_action_ui()
                        self._set_connection_status(
                            "ONLINE",
                            COLORS["green"],
                            "PNGTuber Remix is ready.",
                        )
                        self._set_activity(
                            "COMPLETE",
                            f"{action_name} finished. Restored {normal_state}.",
                        )
                elif event_name == "action_error":
                    (
                        _,
                        action_id,
                        action_name,
                        message,
                        connection_failure,
                    ) = event
                    if self._busy_action_id == action_id:
                        self._finish_action_ui()
                        status = "OFFLINE" if connection_failure else "ACTION ERROR"
                        self._set_connection_status(
                            status,
                            COLORS["red"],
                            f"{action_name} failed.",
                        )
                        self._set_activity("FAILED", message)
                self._ui_queue.task_done()
        except queue.Empty:
            pass

        if not self._stop_event.is_set():
            self._queue_after_id = self.root.after(
                60, self._poll_ui_queue
            )

    def _set_cards_busy(self, active_action_id: str) -> None:
        for action_id, card in self._cards.items():
            card.set_state(
                enabled=action_id == active_action_id,
                active=action_id == active_action_id,
            )

    def _finish_action_ui(self) -> None:
        self._busy_action_id = None
        self._countdown_end = None
        if self._countdown_after_id is not None:
            self.root.after_cancel(self._countdown_after_id)
            self._countdown_after_id = None
        for card in self._cards.values():
            card.set_state(enabled=True, active=False)

    def _update_countdown(self) -> None:
        if self._busy_action_id is None or self._countdown_end is None:
            return
        action = self._action_by_id(self._busy_action_id)
        remaining = max(0.0, self._countdown_end - time.monotonic())
        self._connection_label.configure(
            text=f"EXECUTING  {remaining:0.1f}S",
            foreground=action.accent,
        )
        if remaining > 0:
            self._countdown_after_id = self.root.after(
                100, self._update_countdown
            )

    def _set_connection_status(
        self, label: str, color: str, message: str
    ) -> None:
        self._connection_dot.configure(foreground=color)
        self._connection_label.configure(text=label, foreground=color)
        self._connection_label.master.configure(cursor="hand2")
        self.root.title(f"{self.config.app_name} — {label.title()}")

    def _set_activity(self, code: str, message: str) -> None:
        self._activity_code.configure(text=code)
        self._activity_message.configure(text=message)

    def _update_clock(self) -> None:
        self._clock_label.configure(text=time.strftime("%H:%M:%S"))
        if not self._stop_event.is_set():
            self._clock_after_id = self.root.after(1000, self._update_clock)

    def _schedule_health_check(self) -> None:
        if self._stop_event.is_set():
            return
        if self._busy_action_id is None and self._work_queue.empty():
            self._work_queue.put(("health", None))
        self._health_after_id = self.root.after(
            8000, self._schedule_health_check
        )

    def _action_by_id(self, action_id: str) -> ActionDefinition:
        return next(
            action for action in self.config.actions if action.id == action_id
        )

    def close(self) -> None:
        if self._stop_event.is_set():
            return
        self._stop_event.set()
        try:
            self.audio.stop()
        finally:
            worker = getattr(self, "_worker", None)
            if worker is not None and worker.is_alive():
                worker.join(timeout=1.0)
            self.client.close()
            if worker is not None and worker.is_alive():
                worker.join(timeout=0.5)
        self.root.destroy()


def _set_windows_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--smoke-test", action="store_true")
    args, _unknown = parser.parse_known_args()

    _set_windows_dpi_awareness()
    config = load_config(CONFIG_PATH)
    root = tk.Tk()
    app = CommandDeckApp(
        root,
        config,
        enable_services=not args.smoke_test,
    )
    if args.smoke_test:
        root.update_idletasks()
        root.update()
        app.close()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
