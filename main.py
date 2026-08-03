import os
import subprocess
import threading
import webbrowser
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.switch import Switch
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform
from kivy.clock import mainthread, Clock
from kivy.network.urlrequest import UrlRequest
from kivy.metrics import sp, dp
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
        self.aktualna_verzia = "1.2.0"
        
        # Premenné pre animáciu konverzie
        self.animacia_event = None
        self.konverzia_bodky = 0
        self.posledna_chyba = None
        
        self.github_verzia_url = "https://raw.githubusercontent.com/abnormalTD/moja-appka/master/version.txt"
        self.github_apk_url = "https://github.com/abnormalTD/moja-appka/releases"

        self.stavovy_text = Label(
            text=f"YouTube MP3 Sťahovač v{self.aktualna_verzia}\n(Podporuje playlisty a vlastné priečinky)",
            font_size=sp(22), size_hint=(1, None), halign="center", valign="middle"
        )
        self.stavovy_text.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        self.stavovy_text.bind(texture_size=lambda inst, val: setattr(inst, 'height', max(val[1], sp(60))))
        self.stavovy_text.bind(on_touch_down=self.pri_kliknuti_status)
        self.add_widget(self.stavovy_text)

        # Fixed dp() heights (not proportional to screen height) so inputs/buttons
        # stay a sensible, consistent physical size on any phone instead of
        # stretching to fill whatever space is left after the status label.
        self.folder_input = TextInput(hint_text="Voliteľné: Názov vlastného priečinka...", font_size=sp(20), multiline=False, size_hint=(1, None), height=dp(50))
        self.add_widget(self.folder_input)

        self.link_input = TextInput(hint_text="https://www.youtube.com/...", font_size=sp(20), multiline=False, size_hint=(1, None), height=dp(50))
        self.add_widget(self.link_input)

        self.cislovanie_riadok = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(48))
        self.cislovanie_label = Label(text="Číslovať skladby v playliste", font_size=sp(18), halign="left", valign="middle")
        self.cislovanie_label.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        self.cislovanie_switch = Switch(active=False, size_hint=(0.3, 1))
        self.cislovanie_riadok.add_widget(self.cislovanie_label)
        self.cislovanie_riadok.add_widget(self.cislovanie_switch)
        self.add_widget(self.cislovanie_riadok)

        self.video_riadok = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(48))
        self.video_label = Label(text="Stiahnuť celé video (nie len MP3)", font_size=sp(18), halign="left", valign="middle")
        self.video_label.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        self.video_switch = Switch(active=False, size_hint=(0.3, 1))
        self.video_riadok.add_widget(self.video_label)
        self.video_riadok.add_widget(self.video_switch)
        self.add_widget(self.video_riadok)

        # Quality check button + picker - only relevant/visible in video mode.
        # height=0 alone isn't enough to fully hide a widget in Kivy (it can
        # still render/receive touches outside its box), so opacity+disabled
        # are toggled alongside it.
        self.kvalita_btn = Button(text="Zistiť dostupné kvality", font_size=sp(18), background_color=(0.3, 0.3, 0.3, 1), size_hint=(1, None), height=0, opacity=0, disabled=True)
        self.kvalita_btn.bind(on_press=self.zisti_kvality_vlakno)
        self.add_widget(self.kvalita_btn)

        self.kvalita_spinner = Spinner(text="Vyber kvalitu", values=["Najlepšia dostupná"], font_size=sp(18), size_hint=(1, None), height=0, opacity=0, disabled=True)
        self.add_widget(self.kvalita_spinner)

        self.stiahnut_btn = Button(text="STIAHNUŤ MP3", font_size=sp(28), background_color=(0.1, 0.5, 0.8, 1), size_hint=(1, None), height=dp(64))
        self.stiahnut_btn.bind(on_press=self.spust_stahovanie_vlakno)
        self.add_widget(self.stiahnut_btn)
        self.video_switch.bind(active=self.aktualizuj_text_tlacidla)

        # Fixed height from the start (space always reserved, just hidden via
        # opacity/disabled) - changing height=0 -> dp(N) late at runtime (this
        # gets shown after an async version-check callback) didn't reliably
        # trigger BoxLayout to reposition it, causing it to render on top of
        # stiahnut_btn instead of below it.
        self.update_btn = Button(text="DOSTUPNÁ AKTUALIZÁCIA!", font_size=sp(24), background_color=(0.9, 0.1, 0.1, 1), size_hint=(1, None), height=dp(50), opacity=0, disabled=True)
        self.update_btn.bind(on_press=self.otvor_github)
        self.add_widget(self.update_btn)

        # Absorbs any leftover vertical space on tall screens, keeping the
        # form content grouped near the top instead of stretching to fill it.
        self.add_widget(Widget(size_hint=(1, 1)))

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

    def pri_kliknuti_status(self, instance, touch):
        if instance.collide_point(*touch.pos) and self.posledna_chyba:
            self.zobraz_chybu(self.posledna_chyba)
            return True
        return False

    @mainthread
    def zobraz_chybu(self, text):
        self.posledna_chyba = text
        self.stavovy_text.text = "Nastala chyba (klikni sem pre detail)"

        obsah = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))

        scroll = ScrollView(size_hint=(1, 1))
        chybovy_label = Label(text=text, font_size=sp(16), size_hint=(1, None), halign="left", valign="top")
        chybovy_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        chybovy_label.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
        scroll.add_widget(chybovy_label)
        obsah.add_widget(scroll)

        zavriet_btn = Button(text="Zavrieť", size_hint=(1, None), height=dp(50))
        obsah.add_widget(zavriet_btn)

        popup = Popup(title="Chyba", content=obsah, size_hint=(0.92, 0.8))
        zavriet_btn.bind(on_press=popup.dismiss)
        popup.open()

    @mainthread
    def ukaz_update_tlacidlo(self):
        self.update_btn.opacity = 1
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
        self.stavovy_text.text = f"Sťahovanie dokončené.\nSpracúvam{bodky}"

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

    def aktualizuj_text_tlacidla(self, instance, hodnota):
        self.stiahnut_btn.text = "STIAHNUŤ VIDEO" if hodnota else "STIAHNUŤ MP3"
        for prvok in (self.kvalita_btn, self.kvalita_spinner):
            prvok.height = dp(42) if hodnota else 0
            prvok.opacity = 1 if hodnota else 0
            prvok.disabled = not hodnota

    def zisti_kvality_vlakno(self, instance):
        url = self.link_input.text.strip()
        if not url:
            self.aktualizuj_status("Najprv vlož link!")
            return
        self.kvalita_btn.disabled = True
        self.aktualizuj_status("Zisťujem dostupné kvality...")
        threading.Thread(target=self._zisti_kvality_v_pozadi, args=(url,), daemon=True).start()

    def _zisti_kvality_v_pozadi(self, url):
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True, 'js_runtimes': {'node': {}}, 'logger': MyLogger()}) as ydl:
                info = ydl.extract_info(url, download=False)
            if info and 'entries' in info:
                info = next((e for e in info['entries'] if e), None)
            if not info:
                raise Exception("Nepodarilo sa načítať informácie o videu")
            vysky = sorted(
                {f.get('height') for f in info.get('formats', [])
                 if f.get('vcodec') not in (None, 'none') and f.get('height')},
                reverse=True
            )
            moznosti = ["Najlepšia dostupná"] + [f"{v}p" for v in vysky]
            self.nastav_kvality(moznosti)
            self.aktualizuj_status("Kvality načítané, vyber a stiahni.")
        except Exception as e:
            self.zobraz_chybu(f"Chyba pri zisťovaní kvalít: {str(e)}")
        finally:
            self.odomkni_kvalita_btn()

    @mainthread
    def nastav_kvality(self, moznosti):
        self.kvalita_spinner.values = moznosti
        self.kvalita_spinner.text = "Vyber kvalitu"

    @mainthread
    def odomkni_kvalita_btn(self):
        self.kvalita_btn.disabled = False

    def spust_stahovanie_vlakno(self, instance):
        url = self.link_input.text.strip()
        vlastny_priecinok = self.folder_input.text.strip()
        cislovat = self.cislovanie_switch.active
        chce_video = self.video_switch.active
        vybrata_kvalita = self.kvalita_spinner.text

        if not url:
            self.aktualizuj_status("Najprv vlož link!")
            return

        self.stiahnut_btn.disabled = True
        self.aktualizuj_status("Pripravujem sťahovanie...")

        threading.Thread(target=self._stiahni_mp3_v_pozadi, args=(url, vlastny_priecinok, cislovat, chce_video, vybrata_kvalita), daemon=True).start()

    def _stiahni_mp3_v_pozadi(self, url, vlastny_priecinok, cislovat, chce_video, vybrata_kvalita):
        ffmpeg_debug = ""
        puvodny_ld_path = None
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

            if chce_video:
                # Prefer MP4 (H.264 video + AAC audio) over whatever's
                # technically "best" (often VP9/AV1+Opus in WebM) - much wider
                # device/TV/player compatibility, same reasoning as the MP3
                # codec choice. Falls back to any codec/container if a video
                # has no MP4 option at the requested quality.
                if vybrata_kvalita and vybrata_kvalita != "Najlepšia dostupná" and vybrata_kvalita.endswith("p"):
                    vyska = vybrata_kvalita[:-1]
                    video_format = (
                        f'bestvideo[ext=mp4][height<={vyska}]+bestaudio[ext=m4a]/'
                        f'best[ext=mp4][height<={vyska}]/'
                        f'bestvideo[height<={vyska}]+bestaudio/best[height<={vyska}]'
                    )
                else:
                    video_format = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/bestvideo+bestaudio/best'
                ydl_opts = {
                    'format': video_format,
                    'merge_output_format': 'mp4',
                    'outtmpl': final_path,
                    'noplaylist': False,
                    'logger': MyLogger(),
                    'progress_hooks': [self.my_hook],
                    'js_runtimes': {'node': {}},
                }
            else:
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
                        'preferredquality': '320',
                    }],
                }

            if platform == 'android':
                from jnius import autoclass  # type: ignore
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                native_lib_dir = PythonActivity.mActivity.getApplicationInfo().nativeLibraryDir
                # libffmpegbin.so now has $ORIGIN baked into its rpath at build
                # time (via patchelf in the ffmpeg recipe), so it finds its own
                # sibling libs (libshine.so, libavcodec.so, ...) without needing
                # a process-wide LD_LIBRARY_PATH. That matters because Samsung's
                # linker preloads a huge list of system libraries (including
                # libcrypto.so and libsqlite.so) into every exec'd process - if
                # LD_LIBRARY_PATH included our directory, that preload picked up
                # our libcrypto.so (OpenSSL 3.x, missing a legacy symbol
                # libsqlite.so needs) instead of the system's compatible one.
                # (Copying just ffmpeg's libs to a private cache dir to avoid
                # this doesn't work either - the app's own exec of a file it
                # wrote itself gets PermissionError, confirmed live on-device.)
                ffmpeg_path = os.path.join(native_lib_dir, 'libffmpegbin.so')
                # The Android/python-for-android bootstrap sets LD_LIBRARY_PATH
                # to native_lib_dir automatically at process startup (so Python
                # itself can load its own native modules) - it's already set
                # before this code even runs. Just not re-setting it ourselves
                # does NOT unset it, so we remove it explicitly here (restored
                # after download finishes) to actually test rpath-only resolution.
                puvodny_ld_path = os.environ.pop('LD_LIBRARY_PATH', None)
                ffmpeg_debug = (
                    f"lib_dir={native_lib_dir} | "
                    f"existuje={os.path.exists(ffmpeg_path)} | "
                    f"LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH')}"
                )
                try:
                    test_vysledok = subprocess.run(
                        [ffmpeg_path, '-version'],
                        capture_output=True, text=True, timeout=10
                    )
                    test_vystup = (test_vysledok.stdout or test_vysledok.stderr or "").strip()[:400]
                    ffmpeg_debug += f" || test_kod={test_vysledok.returncode} test_vystup={test_vystup}"
                except Exception as test_e:
                    ffmpeg_debug += f" || test_zlyhal={type(test_e).__name__}: {test_e}"
                # Android ffmpeg build has libshine (MP3 encoder), not libmp3lame which yt-dlp requests by default
                import yt_dlp.postprocessor.ffmpeg as ffmpeg_pp
                ffmpeg_pp.ACODECS['mp3'] = ('mp3', 'libshine', ())
                ydl_opts['ffmpeg_location'] = ffmpeg_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            ukaz_cestu = vlastny_priecinok if vlastny_priecinok else "Download"
            typ_suboru = "Video" if chce_video else "MP3"
            self.zastav_animaciu() # Vypneme bodky
            self.aktualizuj_status(f"Hotovo! {typ_suboru} je v: {ukaz_cestu}")
            
        except Exception as e:
            self.zastav_animaciu() # Pre istotu vypneme bodky aj pri chybe
            sprava = f"Chyba: {str(e)}"
            if ffmpeg_debug:
                sprava += f"\n{ffmpeg_debug}"
            self.zobraz_chybu(sprava)
            if platform == 'android':
                try:
                    from android.storage import primary_external_storage_path  # type: ignore
                    log_path = os.path.join(primary_external_storage_path(), 'Download', 'moja_apka_debug.txt')
                    with open(log_path, 'w', encoding='utf-8') as f:
                        f.write(sprava)
                except Exception:
                    pass
        finally:
            if puvodny_ld_path is not None:
                os.environ['LD_LIBRARY_PATH'] = puvodny_ld_path
            self.odomkni_tlacidlo()

class MP3App(App):
    def build(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission  # type: ignore
            request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
        return StahovacLayout()

if __name__ == '__main__':
    MP3App().run()