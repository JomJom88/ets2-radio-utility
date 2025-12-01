
import tkinter as tk
from tkinter import filedialog, messagebox
import requests
import threading
from urllib.parse import urlparse

class StreamManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stream Manager")
        self.streams = []
        self.file_path = ""

        # Create GUI elements
        self.create_widgets()

    def create_widgets(self):
        '''Setup the layout and widgets'''
        tk.Button(self.root, text="Load .sii File", command=self.load_file).pack(pady=10)
        self.listbox = tk.Listbox(self.root, width=100, height=10)
        self.listbox.pack(pady=10)

        tk.Button(self.root, text="Check Stream", command=self.check_selected_stream).pack(pady=5)
        tk.Button(self.root, text="Add New Stream", command=self.add_stream).pack(pady=5)
        tk.Button(self.root, text="Edit Selected Stream", command=self.edit_stream).pack(pady=5)  # New button to edit stream
        tk.Button(self.root, text="Delete Selected Stream", command=self.delete_stream).pack(pady=5)
        tk.Button(self.root, text="Save Changes", command=self.save_file).pack(pady=10)

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
        self.file_path = filedialog.askopenfilename(filetypes=[("SII Files", "*.sii")])
        if not self.file_path:
            return
        
        with open(self.file_path, 'r') as f:
            lines = f.readlines()

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
        
        self.update_listbox()

    def update_listbox(self):
        '''Refresh the listbox with the current streams'''
        self.listbox.delete(0, tk.END)
        for i, stream in enumerate(self.streams):
            # Show stream name, URL, and genre
            self.listbox.insert(tk.END, f"{i+1}. {stream['name']} - {stream['url']} [{stream['genre']}]")

    def check_selected_stream(self):
        '''Check if the selected stream URL is functional'''
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a stream to check.")
            return

        index = selected[0]
        url = self.streams[index]['url']

        # Use threading to avoid blocking the UI
        threading.Thread(target=self.check_stream_thread, args=(url,), daemon=True).start()

    def check_stream_thread(self, url):
        '''Threaded function to check if the stream URL is functional'''
        is_working = self.check_stream(url)
        self.root.after(0, lambda: self.show_stream_check_result(is_working))

    def show_stream_check_result(self, is_working):
        '''Display the result of a stream check on the main UI thread.'''
        if is_working:
            messagebox.showinfo("Stream Check", "The stream is working!")
        else:
            messagebox.showwarning("Stream Check", "The stream is not responding.")

    def check_stream(self, url):
        '''Check if the stream URL is functional'''
        try:
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def add_stream(self):
        '''Open a dialog to add a new stream'''
        self.open_stream_dialog("Add New Stream")

    def edit_stream(self):
        '''Open a dialog to edit the selected stream'''
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a stream to edit.")
            return

        index = selected[0]
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

            self.update_listbox()
            dialog.destroy()

        tk.Button(dialog, text="Save", command=save_stream).pack(pady=10)

    def delete_stream(self):
        '''Delete the selected stream'''
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a stream to delete.")
            return

        index = selected[0]
        del self.streams[index]
        self.update_listbox()

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

        save_path = filedialog.asksaveasfilename(defaultextension=".sii", filetypes=[("SII Files", "*.sii")])
        if not save_path:
            return

        with open(save_path, 'w') as f:
            # Write the header and update the stream_data count
            f.write('SiiNunit\n{\n')
            f.write(f'live_stream_def : _nameless.23f.d60f.8a20 {{\n stream_data: {len(self.streams)}\n')

            # Write the actual stream data
            for i, stream in enumerate(self.streams):
                f.write(f'stream_data[{i}]: "{stream["url"]}|{stream["name"]}|{stream["genre"]}|{stream["language"]}|{stream["bitrate"]}|{stream["extra"]}"\n')
            
            f.write('}\n')
            f.write('}\n')

        messagebox.showinfo("Save Successful", "Streams have been saved successfully.")

if __name__ == "__main__":
    root = tk.Tk()
    app = StreamManagerApp(root)
    root.mainloop()
