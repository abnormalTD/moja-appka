import os
import threading
import webbrowser
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.switch import Switch
from kivy.utils import platform
from kivy.clock import mainthread, Clock
from kivy.network.urlrequest import UrlRequest
from kivy.metrics import sp
import yt_dlp

class MyLogger:
    def debug(self, msg): pass
    def warning(self, msg): print(f"YT-DLP WARNING: {msg}")
    def error(self, msg): print(f"YT-DLP ERROR: {msg}")
    def write(self, msg): pass

class StahovacLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 20
        self.spacing = 15
        self.aktualna_verzia = "1.1.0"
        
        # Premenné pre animáciu konverzie
        self.animacia_event = None
        self.konverzia_bodky = 0
        
        self.github_verzia_url = "https://raw.githubusercontent.com/abnormalTD/moja-appka/master/version.txt"
        self.github_apk_url = "https://github.com/abnormalTD/moja-appka/releases"

        self.stavovy_text = Label(
            text=f"YouTube MP3 Sťahovač v{self.aktualna_verzia}\n(Podporuje playlisty a vlastné priečinky)",
            font_size=sp(22), size_hint=(1, 0.2), halign="center"
        )
        self.add_widget(self.stavovy_text)

        self.folder_input = TextInput(hint_text="Voliteľné: Názov vlastného priečinka...", font_size=sp(20), multiline=False, size_hint=(1, 0.15))
        self.add_widget(self.folder_input)

        self.link_input = TextInput(hint_text="https://www.youtube.com/...", font_size=sp(20), multiline=False, size_hint=(1, 0.15))
        self.add_widget(self.link_input)

        self.cislovanie_riadok = BoxLayout(orientation='horizontal', size_hint=(1, 0.12))
        self.cislovanie_label = Label(text="Číslovať skladby v playliste", font_size=sp(18), halign="left", valign="middle")
        self.cislovanie_label.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        self.cislovanie_switch = Switch(active=False, size_hint=(0.3, 1))
        self.cislovanie_riadok.add_widget(self.cislovanie_label)
        self.cislovanie_riadok.add_widget(self.cislovanie_switch)
        self.add_widget(self.cislovanie_riadok)

        self.stiahnut_btn = Button(text="STIAHNUŤ MP3", font_size=sp(28), background_color=(0.1, 0.5, 0.8, 1), size_hint=(1, 0.2))
        self.stiahnut_btn.bind(on_press=self.spust_stahovanie_vlakno)
        self.add_widget(self.stiahnut_btn)

        self.update_btn = Button(text="DOSTUPNÁ AKTUALIZÁCIA!", font_size=sp(24), background_color=(0.9, 0.1, 0.1, 1), size_hint=(1, 0), disabled=True)
        self.update_btn.bind(on_press=self.otvor_github)
        self.add_widget(self.update_btn)

        self.skontroluj_aktualizaciu()

    def skontroluj_aktualizaciu(self):
        UrlRequest(self.github_verzia_url, on_success=self.porovnaj_verzie, on_error=self.ignoruj_chybu, on_failure=self.ignoruj_chybu)

    def porovnaj_verzie(self, req, result):
        try:
            if result.strip() != self.aktualna_verzia:
                self.aktualizuj_status(f"Nájdená nová verzia!\nKlikni na červené tlačidlo.")
                self.ukaz_update_tlacidlo()
        except Exception:
            pass

    def ignoruj_chybu(self, req, error): pass

    def otvor_github(self, instance):
        if platform == 'android':
            from jnius import autoclass, cast  # type: ignore
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            intent = Intent(Intent.ACTION_VIEW, Uri.parse(self.github_apk_url))
            current_activity = cast('android.app.Activity', PythonActivity.mActivity)
            current_activity.startActivity(intent)
        else:
            webbrowser.open(self.github_apk_url)

    @mainthread
    def aktualizuj_status(self, text):
        self.stavovy_text.text = text

    @mainthread
    def ukaz_update_tlacidlo(self):
        self.update_btn.size_hint = (1, 0.15)
        self.update_btn.disabled = False

    @mainthread
    def odomkni_tlacidlo(self):
        self.stiahnut_btn.disabled = False
        self.link_input.text = "" 

    # --- LOGIKA ANIMÁCIE ---
    @mainthread
    def spust_animaciu(self):
        self.konverzia_bodky = 0
        if self.animacia_event:
            self.animacia_event.cancel()
        # Spustí funkciu animuj_bodky každú pol sekundu
        self.animacia_event = Clock.schedule_interval(self.animuj_bodky, 0.5)

    def animuj_bodky(self, dt):
        self.konverzia_bodky = (self.konverzia_bodky + 1) % 4
        bodky = "." * self.konverzia_bodky
        self.stavovy_text.text = f"Sťahovanie dokončené.\nKonvertujem na MP3{bodky}"

    @mainthread
    def zastav_animaciu(self):
        if self.animacia_event:
            self.animacia_event.cancel()
            self.animacia_event = None
    # -----------------------

    @mainthread
    def aktualizuj_progress(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total and total > 0:
                percenta = (downloaded / total) * 100
                self.stavovy_text.text = f"Sťahujem: {percenta:.1f}%"
            else:
                self.stavovy_text.text = "Sťahujem..."
        elif d['status'] == 'finished':
            # Tu sa stiahlo video a ide sa konvertovať -> Spustíme animáciu bodiek
            self.spust_animaciu()

    def my_hook(self, d):
        self.aktualizuj_progress(d)

    def spust_stahovanie_vlakno(self, instance):
        url = self.link_input.text.strip()
        vlastny_priecinok = self.folder_input.text.strip()
        cislovat = self.cislovanie_switch.active

        if not url:
            self.aktualizuj_status("Najprv vlož link!")
            return

        self.stiahnut_btn.disabled = True
        self.aktualizuj_status("Pripravujem sťahovanie...")

        threading.Thread(target=self._stiahni_mp3_v_pozadi, args=(url, vlastny_priecinok, cislovat), daemon=True).start()

    def _stiahni_mp3_v_pozadi(self, url, vlastny_priecinok, cislovat):
        try:
            if "&" in url and "list=" not in url:
                url = url.split("&")[0]

            if platform == 'android':
                from android.storage import primary_external_storage_path  # type: ignore
                dir_path = os.path.join(primary_external_storage_path(), 'Download')
            else:
                dir_path = "."

            je_playlist = "list=" in url
            if je_playlist and cislovat:
                nazov_suboru = '%(playlist_index)02d - %(title)s.%(ext)s'
            else:
                nazov_suboru = '%(title)s.%(ext)s'

            if vlastny_priecinok:
                final_path = os.path.join(dir_path, vlastny_priecinok, nazov_suboru)
            else:
                if je_playlist:
                    final_path = os.path.join(dir_path, '%(playlist_title)s', nazov_suboru)
                else:
                    final_path = os.path.join(dir_path, nazov_suboru)

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': final_path,
                'noplaylist': False,
                'logger': MyLogger(),
                'progress_hooks': [self.my_hook],
                'js_runtimes': {'node': {}},
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }

            if platform == 'android':
                from jnius import autoclass  # type: ignore
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                native_lib_dir = PythonActivity.mActivity.getApplicationInfo().nativeLibraryDir
                # Android ffmpeg build has libshine (MP3 encoder), not libmp3lame which yt-dlp requests by default
                import yt_dlp.postprocessor.ffmpeg as ffmpeg_pp
                ffmpeg_pp.ACODECS['mp3'] = ('mp3', 'libshine', ())
                ydl_opts['ffmpeg_location'] = os.path.join(native_lib_dir, 'libffmpegbin.so')

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            ukaz_cestu = vlastny_priecinok if vlastny_priecinok else "Download"
            self.zastav_animaciu() # Vypneme bodky
            self.aktualizuj_status(f"Hotovo! MP3 sú v: {ukaz_cestu}")
            
        except Exception as e:
            self.zastav_animaciu() # Pre istotu vypneme bodky aj pri chybe
            self.aktualizuj_status(f"Chyba: {str(e)}")
        finally:
            self.odomkni_tlacidlo()

class MP3App(App):
    def build(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission  # type: ignore
            request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
        return StahovacLayout()

if __name__ == '__main__':
    MP3App().run()