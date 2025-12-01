
import importlib
import json
import os
import shutil
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
import requests
import threading
import vlc
from urllib.parse import urlparse

class StreamManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stream Manager")
        self.streams = []
        self.file_path = ""
        self.statuses = {}
        self.sort_by = None
        self.sort_reverse = False
        self.is_testing_all = False
        self.settings_path = os.path.join(os.path.expanduser("~"), ".ets2_radio_utility_config.json")
        self.vlc_module = None
        self.vlc_instance = None
        self.player = None
        self.playback_thread = None
        self.currently_playing_index = None
        self.playback_generation = 0

        self.load_settings()

        # Create GUI elements
        self.create_widgets()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        '''Setup the layout and widgets'''
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, pady=5)

        tk.Button(top_frame, text="Load .sii File", command=self.load_file).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Save Changes", command=self.save_file).pack(side=tk.LEFT, padx=5)

        filter_frame = tk.LabelFrame(self.root, text="Filter Streams")
        filter_frame.pack(fill=tk.X, padx=5, pady=5)

        self.name_filter = tk.StringVar()
        self.genre_filter = tk.StringVar()
        self.language_filter = tk.StringVar()

        tk.Label(filter_frame, text="Name:").grid(row=0, column=0, padx=5, pady=2, sticky="e")
        tk.Entry(filter_frame, textvariable=self.name_filter, width=20).grid(row=0, column=1, padx=5, pady=2)
        tk.Label(filter_frame, text="Genre:").grid(row=0, column=2, padx=5, pady=2, sticky="e")
        tk.Entry(filter_frame, textvariable=self.genre_filter, width=20).grid(row=0, column=3, padx=5, pady=2)
        tk.Label(filter_frame, text="Language:").grid(row=0, column=4, padx=5, pady=2, sticky="e")
        tk.Entry(filter_frame, textvariable=self.language_filter, width=20).grid(row=0, column=5, padx=5, pady=2)
        tk.Button(filter_frame, text="Apply", command=self.update_treeview).grid(row=0, column=6, padx=5, pady=2)

        tree_frame = tk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("name", "url", "genre", "language", "bitrate", "extra", "status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for col in columns:
            self.tree.heading(col, text=col.title(), command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=120, anchor="w")
        self.tree.column("url", width=220)
        self.tree.column("status", width=120)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, pady=5)

        tk.Button(button_frame, text="Check Stream", command=self.check_selected_stream).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Play", command=self.play_selected_stream).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Stop", command=self.stop_playback).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Test All", command=self.test_all_streams).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Add New Stream", command=self.add_stream).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Edit Selected Stream", command=self.edit_stream).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Delete Selected Stream", command=self.delete_stream).pack(side=tk.LEFT, padx=5)

        progress_frame = tk.Frame(self.root)
        progress_frame.pack(fill=tk.X, padx=5, pady=5)
        self.progress = ttk.Progressbar(progress_frame, mode="determinate")
        self.progress.pack(fill=tk.X, expand=True)
        self.status_label = tk.Label(progress_frame, text="Ready")
        self.status_label.pack(anchor="w", pady=2)

    def ensure_vlc_available(self):
        """Load python-vlc dynamically and alert the user if it's missing."""
        if self.vlc_module:
            return True

        spec = importlib.util.find_spec("vlc")
        if spec is None:
            messagebox.showerror(
                "VLC Not Installed",
                "python-vlc is required for playback. Please install VLC and the python-vlc package, then try again.",
            )
            return False

        loader = spec.loader
        if loader is None:
            messagebox.showerror(
                "VLC Not Installed",
                "python-vlc is required for playback. Please install VLC and the python-vlc package, then try again.",
            )
            return False

        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        self.vlc_module = module
        return True

    def play_selected_stream(self):
        '''Start playback for the selected stream using VLC'''
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a stream to play.")
            return

        index = int(selected[0])
        url = self.streams[index]['url']

        if not url.strip():
            messagebox.showwarning("Missing URL", "The selected stream does not have a URL to play.")
            return

        if not self.ensure_vlc_available():
            return

        # Stop any existing playback before starting a new stream
        self.stop_playback()
        self.playback_generation += 1
        generation = self.playback_generation
        self.status_label.config(text="Starting playback...")

        self.playback_thread = threading.Thread(
            target=self._start_playback, args=(index, url, generation), daemon=True
        )
        self.playback_thread.start()

    def _start_playback(self, index, url, generation):
        try:
            instance = self.vlc_module.Instance()
            player = instance.media_player_new()
            media = instance.media_new(url)
            player.set_media(media)
            player.play()
        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror("Playback Error", f"Could not start playback:\n{exc}"))
            return

        def update_state():
            if generation != self.playback_generation:
                try:
                    player.stop()
                except Exception:
                    pass
                try:
                    instance.release()
                except Exception:
                    pass
                return

            self.vlc_instance = instance
            self.player = player
            self.currently_playing_index = index
            self.statuses[index] = "Playing"
            self.status_label.config(text=f"Playing: {self.streams[index]['name']}")
            self.update_treeview()

        self.root.after(0, update_state)

    def stop_playback(self, update_status=True, increment_generation=True):
        '''Stop current playback and release VLC resources'''
        if increment_generation:
            self.playback_generation += 1

        if self.player:
            try:
                self.player.stop()
            except Exception:
                pass
        if self.vlc_instance:
            try:
                self.vlc_instance.release()
            except Exception:
                pass

        if update_status and self.currently_playing_index is not None:
            self.statuses[self.currently_playing_index] = "Stopped"
        self.currently_playing_index = None
        self.player = None
        self.vlc_instance = None

        if update_status:
            self.status_label.config(text="Playback stopped")
            self.update_treeview()

    def is_valid_url(self, url):
        '''Basic validation to check if a URL looks valid.'''
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    def validate_stream(self, stream):
        '''Validate a stream's required fields and format.'''
        if not stream['url'].strip():
            return "Stream URL is required."
        if not self.is_valid_url(stream['url'].strip()):
            return "Stream URL is not valid."
        if not stream['name'].strip():
            return "Stream name is required."
        if not str(stream['bitrate']).strip():
            return "Bitrate is required."
        try:
            int(stream['bitrate'])
        except ValueError:
            return "Bitrate must be a number."
        return None

    def load_file(self):
        '''Load .sii file and display streams in the listbox'''
        initial_dir = os.path.dirname(self.file_path) if self.file_path else None
        dialog_options = {"filetypes": [("SII Files", "*.sii")]}
        if initial_dir:
            dialog_options["initialdir"] = initial_dir
        self.file_path = filedialog.askopenfilename(**dialog_options)
        if not self.file_path:
            return
        
        try:
            with open(self.file_path, 'r') as f:
                lines = f.readlines()
        except OSError as exc:
            messagebox.showerror("File Error", f"Could not read file:\n{exc}")
            self.file_path = ""
            return

        self.streams = []
        for line in lines:
            if 'stream_data[' in line:  # Check if the line contains stream data
                try:
                    parts = line.split('"')[1].split('|')
                    # Ensure that we have all the expected parts before adding the stream
                    if len(parts) >= 5:
                        self.streams.append({
                            'url': parts[0],
                            'name': parts[1],
                            'genre': parts[2],
                            'language': parts[3],
                            'bitrate': parts[4],
                            'extra': parts[5] if len(parts) > 5 else "0"  # Default 'extra' to 0 if missing
                        })
                    else:
                        print(f"Warning: Line does not have enough parts - {line}")
                except IndexError:
                    print(f"Error parsing line: {line}")
        
        self.statuses = {}
        self.update_treeview()
        self.save_settings()

    def filtered_streams(self):
        '''Apply filters to streams'''
        name_filter = self.name_filter.get().lower()
        genre_filter = self.genre_filter.get().lower()
        language_filter = self.language_filter.get().lower()

        results = []
        for idx, stream in enumerate(self.streams):
            if name_filter and name_filter not in stream['name'].lower():
                continue
            if genre_filter and genre_filter not in stream['genre'].lower():
                continue
            if language_filter and language_filter not in stream['language'].lower():
                continue
            results.append((idx, stream))
        return results

    def sort_by_column(self, column):
        '''Toggle sorting for a column'''
        if self.sort_by == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_by = column
            self.sort_reverse = False
        self.update_treeview()

    def update_treeview(self):
        '''Refresh the treeview with the current streams'''
        for item in self.tree.get_children():
            self.tree.delete(item)

        streams = self.filtered_streams()
        if self.sort_by:
            key_func = lambda s: s[1].get(self.sort_by, "").lower()
            streams.sort(key=key_func, reverse=self.sort_reverse)

        for idx, stream in streams:
            status_text = self.statuses.get(idx, "")
            values = (
                stream['name'],
                stream['url'],
                stream['genre'],
                stream['language'],
                stream['bitrate'],
                stream['extra'],
                status_text,
            )
            self.tree.insert("", tk.END, iid=str(idx), values=values)

    def check_selected_stream(self):
        '''Check if the selected stream URL is functional'''
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a stream to check.")
            return

        index = int(selected[0])
        url = self.streams[index]['url']

        # Use threading to avoid blocking the UI
        threading.Thread(target=self.check_stream_thread, args=(index, url), daemon=True).start()

    def check_stream_thread(self, index, url):
        '''Threaded function to check if the stream URL is functional'''
        is_working = self.check_stream(url)
        self.root.after(0, lambda: self.show_stream_check_result(index, is_working))

    def show_stream_check_result(self, index, is_working):
        '''Display the result of a stream check on the main UI thread.'''
        self.statuses[index] = "Working" if is_working else "Not Responding"
        self.update_treeview()
        if is_working:
            messagebox.showinfo("Stream Check", "The stream is working!")
        else:
            messagebox.showwarning("Stream Check", "The stream is not responding.")

    def check_stream(self, url):
        '''Check if the stream URL is functional'''
        try:
            with requests.get(url, timeout=(5, 5), stream=True) as response:
                if response.status_code != 200:
                    return False

                try:
                    next(response.iter_content(chunk_size=1024))
                except StopIteration:
                    return False

                return True
        except requests.exceptions.RequestException:
            return False

    def add_stream(self):
        '''Open a dialog to add a new stream'''
        self.open_stream_dialog("Add New Stream")

    def edit_stream(self):
        '''Open a dialog to edit the selected stream'''
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a stream to edit.")
            return

        index = int(selected[0])
        stream = self.streams[index]
        self.open_stream_dialog("Edit Stream", stream, index)

    def open_stream_dialog(self, title, stream=None, index=None):
        '''Open a dialog to add or edit a stream'''
        dialog = tk.Toplevel(self.root)
        dialog.title(title)

        tk.Label(dialog, text="Stream URL").pack()
        url_entry = tk.Entry(dialog, width=50)
        url_entry.pack()
        if stream:
            url_entry.insert(0, stream['url'])

        tk.Label(dialog, text="Stream Name").pack()
        name_entry = tk.Entry(dialog, width=50)
        name_entry.pack()
        if stream:
            name_entry.insert(0, stream['name'])

        tk.Label(dialog, text="Stream Genre").pack()
        genre_entry = tk.Entry(dialog, width=50)
        genre_entry.pack()
        if stream:
            genre_entry.insert(0, stream['genre'])

        tk.Label(dialog, text="Stream Language").pack()
        language_entry = tk.Entry(dialog, width=50)
        language_entry.pack()
        if stream:
            language_entry.insert(0, stream['language'])

        tk.Label(dialog, text="Bitrate").pack()
        bitrate_entry = tk.Entry(dialog, width=50)
        bitrate_entry.pack()
        if stream:
            bitrate_entry.insert(0, stream['bitrate'])

        tk.Label(dialog, text="Extra").pack()
        extra_entry = tk.Entry(dialog, width=50)
        extra_entry.pack()
        if stream:
            extra_entry.insert(0, stream['extra'])

        def save_stream():
            '''Save the new or edited stream'''
            new_stream = {
                'url': url_entry.get(),
                'name': name_entry.get(),
                'genre': genre_entry.get(),
                'language': language_entry.get(),
                'bitrate': bitrate_entry.get(),
                'extra': extra_entry.get()
            }
            error = self.validate_stream(new_stream)
            if error:
                messagebox.showerror("Invalid Input", error)
                return
            if index is not None:
                self.streams[index] = new_stream  # Update existing stream
            else:
                self.streams.append(new_stream)  # Add new stream

            self.update_treeview()
            dialog.destroy()

        tk.Button(dialog, text="Save", command=save_stream).pack(pady=10)

    def delete_stream(self):
        '''Delete the selected stream'''
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a stream to delete.")
            return

        index = int(selected[0])
        del self.streams[index]
        self.statuses.pop(index, None)
        self.statuses = {i if i < index else i - 1: status for i, status in self.statuses.items() if i != index}
        self.update_treeview()

    def save_file(self):
        '''Save the updated streams to a new file'''
        if not self.streams:
            messagebox.showwarning("No Data", "No streams to save.")
            return

        for i, stream in enumerate(self.streams, start=1):
            error = self.validate_stream(stream)
            if error:
                messagebox.showerror("Invalid Stream", f"Error in stream {i}: {error}")
                return

        save_dialog_options = {"defaultextension": ".sii", "filetypes": [("SII Files", "*.sii")]}  # Default options

        if self.file_path:
            save_dialog_options["initialdir"] = os.path.dirname(self.file_path)
            save_dialog_options["initialfile"] = os.path.basename(self.file_path)

        save_path = filedialog.asksaveasfilename(**save_dialog_options)
        if not save_path:
            return

        save_path = os.path.abspath(save_path)

        if os.path.exists(save_path):
            overwrite = messagebox.askyesno("Overwrite File?", f"{save_path} already exists. Do you want to overwrite it?")
            if not overwrite:
                return

            create_backup = messagebox.askyesno(
                "Create Backup?",
                "Do you want to create a timestamped backup of the existing file before overwriting?",
            )
            if create_backup:
                backup_path = f"{save_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                try:
                    shutil.copy2(save_path, backup_path)
                except OSError as exc:
                    messagebox.showerror("Backup Error", f"Could not create backup file:\n{exc}")
                    return

        try:
            with open(save_path, 'w') as f:
                # Write the header and update the stream_data count
                f.write('SiiNunit\n{\n')
                f.write(f'live_stream_def : _nameless.23f.d60f.8a20 {{\n stream_data: {len(self.streams)}\n')

                # Write the actual stream data
                for i, stream in enumerate(self.streams):
                    f.write(f'stream_data[{i}]: "{stream["url"]}|{stream["name"]}|{stream["genre"]}|{stream["language"]}|{stream["bitrate"]}|{stream["extra"]}"\n')

                f.write('}\n')
                f.write('}\n')
        except OSError as exc:
            messagebox.showerror("Save Error", f"Could not save file:\n{exc}")
            return

        self.file_path = save_path
        messagebox.showinfo("Save Successful", "Streams have been saved successfully.")
        self.save_settings()

    def test_all_streams(self):
        '''Check all streams with progress updates'''
        if self.is_testing_all:
            return
        if not self.streams:
            messagebox.showwarning("No Data", "No streams to test.")
            return

        self.is_testing_all = True
        self.progress.config(maximum=len(self.streams), value=0)
        self.status_label.config(text="Testing all streams...")
        threading.Thread(target=self.test_all_thread, daemon=True).start()

    def test_all_thread(self):
        try:
            for idx, stream in enumerate(self.streams):
                try:
                    is_working = self.check_stream(stream['url'])
                except Exception:
                    is_working = False

                status_text = "Working" if is_working else "Not Responding"
                self.statuses[idx] = status_text
                self.root.after(0, lambda i=idx, status=status_text: self.update_status(i, status))
                self.root.after(0, lambda val=idx + 1: self.progress.config(value=val))
        finally:
            self.root.after(0, self.finish_testing)

    def update_status(self, index, status):
        '''Update status label and treeview row'''
        self.status_label.config(text=f"Stream {index + 1}: {status}")
        self.update_treeview()

    def finish_testing(self):
        self.is_testing_all = False
        self.status_label.config(text="Testing complete")

    def load_settings(self):
        '''Restore last used file path and window geometry'''
        try:
            with open(self.settings_path, "r") as f:
                settings = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        geometry = settings.get("geometry")
        if geometry:
            self.root.geometry(geometry)
        self.file_path = settings.get("last_file", "")

    def save_settings(self):
        '''Persist last used file path and window geometry'''
        settings = {
            "last_file": self.file_path,
            "geometry": self.root.winfo_geometry(),
        }
        try:
            with open(self.settings_path, "w") as f:
                json.dump(settings, f)
        except OSError:
            pass

    def on_close(self):
        self.stop_playback()
        self.save_settings()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = StreamManagerApp(root)
    root.mainloop()
