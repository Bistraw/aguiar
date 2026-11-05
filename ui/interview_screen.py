"""Full-screen interview shown to both the psychologist and the patient."""

import io
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from active_records import CardActiveRecord, InterviewActiveRecord, ValidationError
from services.csv_export import export_interview_csv, suggested_file_name
from services.interview_service import InterviewSession
from services.qr_scanner import CameraError, QrScanner
from ui.common import run_action, show_error
from ui.settings_view import current_camera_index

POLL_MS = 50
REARM_SECONDS = 1.0  # card must be out of view this long before a new answer is accepted
PREVIEW_SIZE = (200, 150)
BG = "white"

MODE_QUESTION = "question"
MODE_FEEDBACK = "feedback"
MODE_DIALOG = "dialog"
MODE_FINISHED = "finished"


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
        style = ttk.Style(self)
        style.configure("Interview.TFrame", background=BG)
        style.configure("Interview.TLabel", background=BG)
        style.configure("Small.TButton", font=("Segoe UI", 9))

        top = ttk.Frame(self, style="Interview.TFrame", padding=(16, 8))
        top.pack(side="top", fill="x")
        self.progress_label = ttk.Label(top, style="Interview.TLabel", foreground="gray", font=("Segoe UI", 10))
        self.progress_label.pack(side="right")

        bottom = ttk.Frame(self, style="Interview.TFrame", padding=(16, 8))
        bottom.pack(side="bottom", fill="x")
        self.preview_label = ttk.Label(bottom, style="Interview.TLabel")
        self.preview_label.pack(side="left")
        controls = ttk.Frame(bottom, style="Interview.TFrame")
        controls.pack(side="right", anchor="s")
        self.timer_label = ttk.Label(controls, style="Interview.TLabel", foreground="gray", font=("Segoe UI", 9))
        self.timer_label.pack(side="left", padx=(0, 4))
        self.timer_bar = ttk.Progressbar(controls, length=100, maximum=1000, mode="determinate")
        self.timer_bar.pack(side="left", padx=(0, 12))
        self.skip_button = ttk.Button(controls, text="Skip (Space)", style="Small.TButton",
                                      command=self.skip, takefocus=False)
        self.skip_button.pack(side="left", padx=(0, 4))
        ttk.Button(controls, text="Pause / Stop (Esc)", style="Small.TButton",
                   command=self.open_stop_dialog, takefocus=False).pack(side="left")

        self.center = ttk.Frame(self, style="Interview.TFrame", padding=24)
        self.center.pack(side="top", fill="both", expand=True)
        self.center.bind("<Configure>", self._on_center_resize)

        # Question
        self.question_frame = ttk.Frame(self.center, style="Interview.TFrame")
        self.text_label = ttk.Label(self.question_frame, style="Interview.TLabel", font=("Segoe UI", 28),
                                    justify="center", anchor="center")
        self.text_label.pack(side="top", pady=(10, 20))
        self.image_label = ttk.Label(self.question_frame, style="Interview.TLabel", anchor="center")
        self.image_label.pack(side="top")

        # Feedback
        self.feedback_frame = ttk.Frame(self.center, style="Interview.TFrame")
        self.feedback_label = ttk.Label(self.feedback_frame, style="Interview.TLabel", font=("Segoe UI", 24),
                                        justify="center", anchor="center")
        self.feedback_label.pack(side="top", pady=(40, 30))
        ttk.Button(self.feedback_frame, text="Continue", command=self._show_next_question,
                   takefocus=False).pack(side="top")

        # Finished
        self.finish_frame = ttk.Frame(self.center, style="Interview.TFrame")
        self.finish_title = ttk.Label(self.finish_frame, style="Interview.TLabel", font=("Segoe UI", 28))
        self.finish_title.pack(side="top", pady=(60, 30))
        finish_buttons = ttk.Frame(self.finish_frame, style="Interview.TFrame")
        finish_buttons.pack(side="top")
        ttk.Button(finish_buttons, text="Export CSV",
                   command=lambda: export_csv_dialog(self, self.session.interview)).pack(side="left", padx=6)
        ttk.Button(finish_buttons, text="Close", command=self._close).pack(side="left", padx=6)

    def _on_center_resize(self, event):
        wrap = max(200, event.width - 80)
        self.text_label.configure(wraplength=wrap)
        self.feedback_label.configure(wraplength=wrap)

    def _show_frame(self, frame):
        for f in (self.question_frame, self.feedback_frame, self.finish_frame):
            if f is not frame:
                f.pack_forget()
        frame.pack(fill="both", expand=True)

    # --- flow ---

    def _show_next_question(self):
        iq = self.session.next_question()
        if iq is None:
            self.session.complete()
            self._show_finished("Interview completed")
            return
        question = self.session.current_question()
        text = question.text if question else iq.question_text
        image = question.image if question else None

        self.text_label.configure(text=text or "")
        self._render_question_image(image)
        self.progress_label.configure(text=f"Question {iq.position} of {self.session.total}")
        self._show_frame(self.question_frame)
        self.skip_button.state(["!disabled"])
        self.mode = MODE_QUESTION
        limit = self.session.interview.answer_limit
        self.deadline = time.monotonic() + limit if limit else None
        self._update_timer()

    def _render_question_image(self, data):
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

    def _show_finished(self, title):
        self.mode = MODE_FINISHED
        self.deadline = None
        self._update_timer()
        self.skip_button.state(["disabled"])
        self.scanner.stop()
        self._preview_photo = None
        self.preview_label.configure(image="")
        self.finish_title.configure(text=title)
        self._show_frame(self.finish_frame)

    # --- polling: camera preview, scans, timer ---

    def _poll(self):
        self._poll_job = None
        if self.mode == MODE_FINISHED:
            return
        frame = self.scanner.get_frame()
        if frame is not None:
            img = Image.fromarray(frame)
            img.thumbnail(PREVIEW_SIZE)
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
                        self._after_answer(candidate)
                        break
            if self.mode == MODE_QUESTION and self.deadline is not None:
                if now >= self.deadline:
                    self.session.time_out()
                    self._show_next_question()
                else:
                    self._update_timer()

        if self.mode != MODE_FINISHED:
            self._poll_job = self.after(POLL_MS, self._poll)

    def _update_timer(self):
        limit = self.session.interview.answer_limit
        if self.mode in (MODE_QUESTION, MODE_DIALOG) and limit:
            remaining = self.remaining if self.mode == MODE_DIALOG else max(0.0, self.deadline - time.monotonic())
            self.timer_bar["value"] = 1000 * remaining / limit
            self.timer_label.configure(text=f"{int(remaining + 0.999)} s")
        else:
            self.timer_bar["value"] = 0
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
            self._show_finished("Interview ended")
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


class StopDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Interview paused")
        self.transient(parent)
        self.resizable(False, False)
        self.choice = "continue"
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="The interview is paused. What do you want to do?").pack(anchor="w", pady=(0, 12))
        buttons = ttk.Frame(body)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Continue", command=lambda: self._choose("continue")).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Pause (resume later)", command=lambda: self._choose("pause")).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="End interview", command=self._end).pack(side="left")
        self.bind("<Escape>", lambda e: self._choose("continue"))
        self.protocol("WM_DELETE_WINDOW", lambda: self._choose("continue"))
        self.grab_set()
        self.focus_force()
        self.wait_window()

    def _end(self):
        if messagebox.askyesno("End interview", "End the interview now? Remaining questions stay unanswered.",
                               parent=self):
            self._choose("end")

    def _choose(self, choice):
        self.choice = choice
        self.destroy()
