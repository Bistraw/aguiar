"""Full-screen interview shown to both the psychologist and the patient."""

import io
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from active_records import CardActiveRecord, InterviewActiveRecord, Outcome, ValidationError
from services.csv_export import export_interview_csv, suggested_file_name
from services.interview_service import InterviewSession
from services.qr_scanner import CameraError, QrScanner
from ui import theme
from ui.common import Dialog, ThinBar, make_button, run_action, show_error
from ui.icons import icon
from ui.settings_view import current_camera_index
from ui.theme import px

POLL_MS = 50
REARM_SECONDS = 1.0  # card must be out of view this long before a new answer is accepted
IGNORED_HINT_SECONDS = 1.5  # how long "try another card" stays after a card that is not an option
PREVIEW_SIZE = (200, 150)
LONG_QUESTION_CHARS = 140
BG = theme.SURFACE

MODE_QUESTION = "question"
MODE_FEEDBACK = "feedback"
MODE_DIALOG = "dialog"
MODE_FINISHED = "finished"

# Scan cue next to the camera preview: (icon, icon/border color, text). Neutral on purpose: it confirms that a
# card was read, never whether the answer was the expected one.
SCAN_READY = ("target", theme.ACCENT, "Show your card to the camera")
SCAN_READ = ("checkmark", theme.SUCCESS, "Card read. Please remove it")
SCAN_IGNORED = ("information", theme.WARNING, "That card is not an option here. Try another one")


def export_csv_dialog(parent, interview):
    patient = interview.patient()
    path = filedialog.asksaveasfilename(
        parent=parent,
        title="Export CSV",
        defaultextension=".csv",
        initialfile=suggested_file_name(patient.name if patient else None, interview.start),
        filetypes=[("CSV file", "*.csv")],
    )
    if path and run_action(parent, lambda: export_interview_csv(interview.id, path)):
        messagebox.showinfo("Export CSV", f"Results saved to:\n{path}", parent=parent)


def open_interview_screen(parent, interview_id, on_close=None):
    """Open the camera, then the interview. Shows an error and returns None if the camera is unavailable."""
    interview = InterviewActiveRecord.get(interview_id)
    if interview is None:
        return None
    scanner = QrScanner(current_camera_index())
    parent.winfo_toplevel().configure(cursor="watch")
    parent.update_idletasks()
    try:
        scanner.start()
    except CameraError as exc:
        messagebox.showerror("Camera", f"{exc}\n\nThe interview cannot start without a camera.", parent=parent)
        return None
    finally:
        parent.winfo_toplevel().configure(cursor="")

    session = InterviewSession(interview)
    try:
        session.start()
    except ValidationError as exc:
        scanner.stop()
        show_error(parent, exc)
        return None
    return InterviewScreen(parent, session, scanner, on_close)


class InterviewScreen(tk.Toplevel):
    def __init__(self, parent, session, scanner, on_close=None):
        super().__init__(parent, background=BG)
        self.session = session
        self.scanner = scanner
        self.on_close = on_close
        self.mode = None
        self.armed = True
        self.deadline = None
        self.remaining = None
        self._poll_job = None
        self._preview_photo = None
        self._image_photo = None
        self._ignored_until = 0.0
        self._scan_state = None
        patient = session.interview.patient()
        self.title(f"Interview — {patient.name if patient else ''}")

        self._build()
        try:
            self.state("zoomed")
        except tk.TclError:
            self.attributes("-fullscreen", True)
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        self.bind("<space>", lambda e: self.skip())
        self.bind("<Escape>", lambda e: self.open_stop_dialog())
        self.focus_force()
        self.grab_set()

        self._show_next_question()
        self._poll()

    # --- layout ---

    def _build(self):
        self._build_top()
        self._build_bottom()
        self.center = ttk.Frame(self, style="Surface.TFrame", padding=px(24))
        self.center.pack(side="top", fill="both", expand=True)
        self.center.bind("<Configure>", self._on_center_resize)
        self._build_pages()

    def _build_top(self):
        self.progress_bar = ThinBar(self)
        self.progress_bar.pack(side="top", fill="x")
        top = ttk.Frame(self, style="Surface.TFrame", padding=(px(20), px(10)))
        top.pack(side="top", fill="x")
        self.progress_label = ttk.Label(top, style="SurfaceMuted.TLabel")
        self.progress_label.pack(side="right")

    def _build_bottom(self):
        bottom = ttk.Frame(self, style="Surface.TFrame", padding=(px(20), px(14)))
        bottom.pack(side="bottom", fill="x")

        # Patient side: camera preview and what to do with the card.
        self.scan_area = ttk.Frame(bottom, style="Surface.TFrame")
        self.scan_area.pack(side="left")
        self.preview_border = tk.Frame(self.scan_area, background=theme.BORDER, padx=px(3), pady=px(3))
        self.preview_border.pack(side="left")
        size = (px(PREVIEW_SIZE[0]), px(PREVIEW_SIZE[1]))
        self._preview_photo = ImageTk.PhotoImage(Image.new("RGB", size, theme.HOVER))  # keeps the layout until frame 1
        self.preview_label = tk.Label(self.preview_border, image=self._preview_photo, borderwidth=0)
        self.preview_label.pack()
        self.scan_icon = ttk.Label(self.scan_area, style="Surface.TLabel")
        self.scan_icon.pack(side="left", padx=(px(16), px(8)))
        self.scan_label = ttk.Label(self.scan_area, style="PatientHint.TLabel")
        self.scan_label.pack(side="left")

        # Psychologist side: small, discreet controls.
        self.controls = ttk.Frame(bottom, style="Surface.TFrame")
        self.controls.pack(side="right", anchor="s")
        self.timer_label = ttk.Label(self.controls, style="SurfaceSmall.TLabel")
        self.timer_bar = ThinBar(self.controls, color=theme.MUTED, thickness=4, width=100)
        if self.session.interview.answer_limit:
            self.timer_label.pack(side="left", padx=(0, px(6)))
            self.timer_bar.pack(side="left", padx=(0, px(14)))
        self.skip_button = make_button(self.controls, "Skip (Space)", self.skip, "next", "quiet", takefocus=False)
        self.skip_button.pack(side="left", padx=(0, px(4)))
        make_button(self.controls, "Pause / Stop (Esc)", self.open_stop_dialog, "pause", "quiet",
                    takefocus=False).pack(side="left")

    def _build_pages(self):
        # Question
        self.question_frame = ttk.Frame(self.center, style="Surface.TFrame")
        self.text_label = ttk.Label(self.question_frame, style="Surface.TLabel", justify="center", anchor="center")
        self.image_label = ttk.Label(self.question_frame, style="Surface.TLabel", anchor="center")

        # Feedback
        self.feedback_frame = ttk.Frame(self.center, style="Surface.TFrame")
        self.feedback_label = ttk.Label(self.feedback_frame, style="Surface.TLabel", font=theme.FONT_FEEDBACK,
                                        justify="center", anchor="center")
        self.feedback_label.pack(side="top", pady=(0, px(30)))
        make_button(self.feedback_frame, "Continue", self._show_next_question, "next", "primary",
                    takefocus=False).pack(side="top")

        # Finished
        self.finish_frame = ttk.Frame(self.center, style="Surface.TFrame")
        self.finish_icon = ttk.Label(self.finish_frame, style="Surface.TLabel")
        self.finish_icon.pack(side="top")
        self.finish_title = ttk.Label(self.finish_frame, style="Finish.TLabel")
        self.finish_title.pack(side="top", pady=(px(14), px(6)))
        self.finish_summary = ttk.Label(self.finish_frame, style="PatientHint.TLabel")
        self.finish_summary.pack(side="top", pady=(0, px(28)))
        finish_buttons = ttk.Frame(self.finish_frame, style="Surface.TFrame")
        finish_buttons.pack(side="top")
        make_button(finish_buttons, "Export CSV", lambda: export_csv_dialog(self, self.session.interview), "export",
                    "primary").pack(side="left", padx=px(6))
        make_button(finish_buttons, "Close", self._close, "exitRight").pack(side="left", padx=px(6))

    def _on_center_resize(self, event):
        wrap = max(px(200), event.width - px(120))
        self.text_label.configure(wraplength=wrap)
        self.feedback_label.configure(wraplength=wrap)

    def _show_frame(self, frame):
        for f in (self.question_frame, self.feedback_frame, self.finish_frame):
            if f is not frame:
                f.place_forget()
        frame.place(relx=0.5, rely=0.46, anchor="center")

    # --- flow ---

    def _show_next_question(self):
        iq = self.session.next_question()
        if iq is None:
            self.session.complete()
            self._show_finished("Interview completed", "checkmark", theme.SUCCESS)
            return
        question = self.session.current_question()
        text = question.text if question else iq.question_text
        image = question.image if question else None

        self._render_question_text(text)
        self._render_question_image(image)
        self.progress_label.configure(text=f"Question {iq.position} of {self.session.total}")
        self.progress_bar.set((iq.position - 1) / max(1, self.session.total))
        self._show_frame(self.question_frame)
        self.skip_button.state(["!disabled"])
        self.mode = MODE_QUESTION
        limit = self.session.interview.answer_limit
        self.deadline = time.monotonic() + limit if limit else None
        self._update_timer()

    def _render_question_text(self, text):
        self.text_label.pack_forget()
        if text:
            font = theme.FONT_QUESTION_LONG if len(text) > LONG_QUESTION_CHARS else theme.FONT_QUESTION
            self.text_label.configure(text=text, font=font)
            self.text_label.pack(side="top", pady=(0, px(20)))

    def _render_question_image(self, data):
        self.image_label.pack_forget()
        if not data:
            self._image_photo = None
            self.image_label.configure(image="")
            return
        max_size = (int(self.winfo_screenwidth() * 0.7), int(self.winfo_screenheight() * 0.45))
        with Image.open(io.BytesIO(data)) as img:
            img = img.copy()
        # Scale to fit keeping aspect ratio (up or down).
        ratio = min(max_size[0] / img.width, max_size[1] / img.height)
        img = img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))), Image.LANCZOS)
        self._image_photo = ImageTk.PhotoImage(img)
        self.image_label.configure(image=self._image_photo)
        self.image_label.pack(side="top")

    def _after_answer(self, candidate):
        self.armed = False
        if self.session.interview.give_feedback and candidate.feedback_text:
            self.mode = MODE_FEEDBACK
            self.deadline = None
            self._update_timer()
            self.skip_button.state(["disabled"])
            self.feedback_label.configure(text=candidate.feedback_text)
            self._show_frame(self.feedback_frame)
        else:
            self._show_next_question()

    def skip(self):
        if self.mode != MODE_QUESTION:
            return
        self.session.skip()
        self._show_next_question()

    def _show_finished(self, title, icon_name, color):
        self.mode = MODE_FINISHED
        self.deadline = None
        self.scanner.stop()
        self._preview_photo = None
        self.scan_area.pack_forget()
        self.controls.pack_forget()
        self.progress_label.configure(text="")
        counts = self.session.outcome_counts()
        answered = sum(counts.values())
        self.progress_bar.set(answered / max(1, self.session.total))
        self.finish_icon.configure(image=icon(icon_name, 64, color))
        self.finish_title.configure(text=title)
        parts = [f"{counts.get(Outcome.ANSWERED, 0)} answered", f"{counts.get(Outcome.SKIPPED, 0)} skipped",
                 f"{counts.get(Outcome.TIMED_OUT, 0)} timed out"]
        if answered < self.session.total:
            parts.append(f"{self.session.total - answered} not reached")
        self.finish_summary.configure(text="  ·  ".join(parts))
        self._show_frame(self.finish_frame)

    # --- polling: camera preview, scans, timer ---

    def _poll(self):
        self._poll_job = None
        if self.mode == MODE_FINISHED:
            return
        frame = self.scanner.get_frame()
        if frame is not None:
            # Mirrored like a selfie so the patient can aim the card naturally. Decoding uses the original frame.
            img = Image.fromarray(frame).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            img.thumbnail((px(PREVIEW_SIZE[0]), px(PREVIEW_SIZE[1])))
            self._preview_photo = ImageTk.PhotoImage(img)
            self.preview_label.configure(image=self._preview_photo)

        now = time.monotonic()
        texts = self.scanner.pop_decoded()
        if not self.armed and now - self.scanner.last_seen >= REARM_SECONDS:
            self.armed = True

        if self.mode == MODE_QUESTION:
            if self.armed:
                for text in texts:
                    card_id = CardActiveRecord.parse_qr_payload(text)
                    candidate = self.session.try_answer(card_id) if card_id else None
                    if candidate:
                        self._ignored_until = 0.0
                        self._after_answer(candidate)
                        break
                    self._ignored_until = now + IGNORED_HINT_SECONDS
            if self.mode == MODE_QUESTION and self.deadline is not None:
                if now >= self.deadline:
                    self.session.time_out()
                    self._show_next_question()
                else:
                    self._update_timer()

        if self.mode != MODE_FINISHED:
            self._update_scan_cue(now)
            self._poll_job = self.after(POLL_MS, self._poll)

    def _update_scan_cue(self, now):
        if not self.armed:
            state = SCAN_READ
        elif self.mode != MODE_QUESTION:
            state = None
        elif now < self._ignored_until:
            state = SCAN_IGNORED
        else:
            state = SCAN_READY
        if state is self._scan_state:
            return
        self._scan_state = state
        if state is None:
            self.scan_icon.configure(image="")
            self.scan_label.configure(text="")
            self.preview_border.configure(background=theme.BORDER)
            return
        icon_name, color, text = state
        self.scan_icon.configure(image=icon(icon_name, 24, color))
        self.scan_label.configure(text=text)
        self.preview_border.configure(background=theme.BORDER if state is SCAN_READY else color)

    def _update_timer(self):
        limit = self.session.interview.answer_limit
        if self.mode in (MODE_QUESTION, MODE_DIALOG) and limit:
            remaining = self.remaining if self.mode == MODE_DIALOG else max(0.0, self.deadline - time.monotonic())
            self.timer_bar.set(remaining / limit)
            self.timer_label.configure(text=f"{int(remaining + 0.999)} s")
        else:
            self.timer_bar.set(0)
            self.timer_label.configure(text="")

    # --- pause / stop ---

    def open_stop_dialog(self):
        if self.mode in (MODE_DIALOG, MODE_FINISHED, None):
            return
        previous = self.mode
        self.remaining = max(0.0, self.deadline - time.monotonic()) if self.deadline is not None else None
        self.mode = MODE_DIALOG

        choice = StopDialog(self).choice
        if choice == "pause":
            self.session.pause()
            self._close()
        elif choice == "end":
            self.session.abort()
            self._show_finished("Interview ended", "stop", theme.MUTED)
        else:
            self.mode = previous
            if previous == MODE_QUESTION and self.remaining is not None:
                self.deadline = time.monotonic() + self.remaining
            self.remaining = None
            self.grab_set()
            self.focus_force()

    def _on_window_close(self):
        if self.mode == MODE_FINISHED:
            self._close()
        else:
            self.open_stop_dialog()

    def _close(self):
        if self._poll_job is not None:
            self.after_cancel(self._poll_job)
            self._poll_job = None
        self.scanner.stop()
        self.grab_release()
        self.destroy()
        if self.on_close:
            self.on_close()


class StopDialog(Dialog):
    def __init__(self, parent):
        super().__init__(parent, "Interview paused")
        self.choice = "continue"
        ttk.Label(self.body, text="The timer is stopped. What do you want to do?",
                  style="SurfaceMuted.TLabel").pack(anchor="w", pady=(0, px(14)))
        options = [
            ("Continue", "Back to the current question.", lambda: self._choose("continue"), "next", "primary"),
            ("Pause and resume later", "Leave now and pick up from this question.",
             lambda: self._choose("pause"), "pause", "secondary"),
            ("End interview", "Finish now. Remaining questions stay unanswered.", self._end, "stop", "danger"),
        ]
        first = None
        for text, hint, command, icon_name, kind in options:
            button = make_button(self.body, text, command, icon_name, kind, width=30)
            button.pack(fill="x")
            first = first or button
            ttk.Label(self.body, text=hint, style="SurfaceSmall.TLabel").pack(anchor="w", pady=(px(3), px(12)))
        self.bind("<Escape>", lambda e: self._choose("continue"))
        self.bind("<Return>", lambda e: e.widget.invoke() if isinstance(e.widget, ttk.Button) else None)
        self.protocol("WM_DELETE_WINDOW", lambda: self._choose("continue"))
        self.present(first)

    def _end(self):
        if messagebox.askyesno("End interview", "End the interview now? Remaining questions stay unanswered.",
                               parent=self):
            self._choose("end")

    def _choose(self, choice):
        self.choice = choice
        self.destroy()
