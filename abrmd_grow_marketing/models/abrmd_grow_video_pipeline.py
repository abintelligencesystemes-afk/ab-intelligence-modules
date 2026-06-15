# -*- coding: utf-8 -*-
"""Pipeline vidéo low-cost — TTS + Whisper + FFmpeg.

Orchestrateur AbstractModel :
1. _generate_voiceover     → appel OpenAI TTS, sortie MP3
2. _transcribe_voiceover   → appel OpenAI Whisper, sortie SRT
3. _ffmpeg_assemble        → subprocess ffmpeg, sortie MP4
4. _finalize               → attache MP4 sur abrmd.grow.video

Tout est isolé et stubable pour les tests : chaque étape peut être
patchée individuellement via les méthodes ``_call_*`` qui retournent
toujours (binary_data, ok: bool, log: str).

FFmpeg : on appelle ``ffmpeg`` via subprocess. Si pas installé sur
l'hôte, l'étape échoue proprement, la vidéo passe en state 'failed'
avec un message clair.

OpenAI TTS / Whisper : urllib std-lib. Si pas de clé API, on tombe
sur un mode dev (génère un MP3 silencieux et un SRT vide) — utile pour
tester localement le pipeline FFmpeg sans appel payant.
"""
import base64
import json
import logging
import os
import subprocess
import tempfile

from odoo import _, api, fields, models

try:
    import urllib.request as _urlreq
except Exception:  # pragma: no cover
    _urlreq = None

_logger = logging.getLogger(__name__)

OPENAI_TTS_ENDPOINT = "https://api.openai.com/v1/audio/speech"
OPENAI_WHISPER_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"

FORMAT_TO_DIMS = {
    "9_16": (1080, 1920),
    "16_9": (1920, 1080),
    "1_1": (1080, 1080),
    "4_5": (1080, 1350),
}


class AbrmdGrowVideoPipeline(models.AbstractModel):
    _name = "abrmd.grow.video.pipeline"
    _description = "Pipeline vidéo low-cost (TTS + Whisper + FFmpeg)"

    # ------------------------------------------------------------------
    # Helpers pure-python (testables)
    # ------------------------------------------------------------------
    @staticmethod
    def estimate_cost(script, voice_provider="openai_tts", duration_s=30.0):
        """Estimation coût pure-python pour un script + provider donné."""
        chars = len(script or "")
        duration_min = max(1.0, duration_s) / 60.0
        tts = 0.0
        if voice_provider == "openai_tts":
            tts = (chars / 1000.0) * 0.014
        elif voice_provider == "elevenlabs":
            tts = (chars / 1000.0) * 0.27
        whisper = duration_min * 0.0055
        return round(tts + whisper, 4)

    @staticmethod
    def ffmpeg_available():
        """Retourne True si la commande ffmpeg est trouvée sur l'hôte."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True, timeout=5, check=False,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return False

    @staticmethod
    def build_ffmpeg_cmd(image_paths, audio_path, srt_path, output_path,
                         width=1080, height=1920, max_duration=60,
                         burn_subtitles=True):
        """Construit la commande FFmpeg à exécuter.

        Pure-python : retourne une liste d'arguments, ne lance rien.
        Stratégie : crée un slideshow d'images + audio + sous-titres burnés.
        """
        if not image_paths or not output_path:
            return []
        # Calcule la durée par image pour répartir sur max_duration
        per_image = max(2.0, max_duration / max(len(image_paths), 1))
        cmd = ["ffmpeg", "-y"]
        # Input images en loop
        concat_args = []
        for i, img in enumerate(image_paths):
            cmd.extend(["-loop", "1", "-t", str(per_image), "-i", img])
            concat_args.append(f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                               f"crop={width}:{height}[v{i}];")
        # Audio
        if audio_path and os.path.exists(audio_path):
            cmd.extend(["-i", audio_path])
        # Filter complex : concat des inputs
        filter_complex = "".join(concat_args)
        concat_inputs = "".join(f"[v{i}]" for i in range(len(image_paths)))
        filter_complex += f"{concat_inputs}concat=n={len(image_paths)}:v=1:a=0[vout]"
        if burn_subtitles and srt_path and os.path.exists(srt_path):
            filter_complex = filter_complex.replace(
                "[vout]",
                "[vouttmp];[vouttmp]subtitles=" + srt_path.replace(":", "\\:") + "[vout]"
            )
        cmd.extend(["-filter_complex", filter_complex])
        cmd.extend(["-map", "[vout]"])
        if audio_path and os.path.exists(audio_path):
            cmd.extend(["-map", f"{len(image_paths)}:a"])
        cmd.extend([
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-t", str(max_duration),
            output_path,
        ])
        return cmd

    @staticmethod
    def build_srt_from_text(text, duration_s=30.0):
        """Construit un SRT minimaliste à partir d'un texte plat.

        Découpe en blocs de ~5 mots par sous-titre (heuristique simple).
        Utile en fallback si Whisper n'est pas dispo.
        """
        if not text:
            return ""
        words = text.split()
        if not words:
            return ""
        chunk_size = 5
        chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
        per_chunk = duration_s / max(len(chunks), 1)
        srt_lines = []
        for i, chunk in enumerate(chunks):
            start = i * per_chunk
            end = (i + 1) * per_chunk
            srt_lines.append(str(i + 1))
            srt_lines.append(
                f"{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}"
            )
            srt_lines.append(chunk)
            srt_lines.append("")
        return "\n".join(srt_lines)

    # ------------------------------------------------------------------
    # Appels externes (OpenAI TTS, Whisper, FFmpeg)
    # ------------------------------------------------------------------
    @api.model
    def _call_openai_tts(self, text, voice="nova", timeout=60):
        """Appel OpenAI TTS. Retourne (mp3_bytes, ok, log)."""
        ICP = self.env["ir.config_parameter"].sudo()
        api_key = ICP.get_param("openai.api_key", default="").strip()
        if not api_key:
            return b"", False, "no_openai_key"
        if _urlreq is None:
            return b"", False, "no_urllib"
        payload = {
            "model": "tts-1",
            "input": text[:4000],
            "voice": voice or "nova",
            "response_format": "mp3",
        }
        try:
            body = json.dumps(payload).encode("utf-8")
            req = _urlreq.Request(
                OPENAI_TTS_ENDPOINT,
                data=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with _urlreq.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return raw, True, "ok"
        except Exception as exc:  # noqa: BLE001
            _logger.warning("[abrmd_grow_marketing] TTS échec : %s", exc)
            return b"", False, str(exc)

    @api.model
    def _call_openai_whisper(self, mp3_bytes, filename="voiceover.mp3", timeout=120):
        """Appel OpenAI Whisper transcription, format SRT.

        Retourne (srt_string, ok, log).
        Pour rester en std-lib, on construit une requête multipart manuelle.
        """
        ICP = self.env["ir.config_parameter"].sudo()
        api_key = ICP.get_param("openai.api_key", default="").strip()
        if not api_key:
            return "", False, "no_openai_key"
        if _urlreq is None:
            return "", False, "no_urllib"
        boundary = "----abrmd_grow_marketing_boundary_xy7z"
        body_parts = []
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(
            (f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
             'Content-Type: audio/mpeg\r\n\r\n').encode()
        )
        body_parts.append(mp3_bytes)
        body_parts.append(b"\r\n")
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(b'Content-Disposition: form-data; name="model"\r\n\r\nwhisper-1\r\n')
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(b'Content-Disposition: form-data; name="response_format"\r\n\r\nsrt\r\n')
        body_parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(body_parts)
        try:
            req = _urlreq.Request(
                OPENAI_WHISPER_ENDPOINT,
                data=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
                method="POST",
            )
            with _urlreq.urlopen(req, timeout=timeout) as resp:
                srt = resp.read().decode("utf-8", errors="replace")
            return srt, True, "ok"
        except Exception as exc:  # noqa: BLE001
            _logger.warning("[abrmd_grow_marketing] Whisper échec : %s", exc)
            return "", False, str(exc)

    @api.model
    def _call_ffmpeg(self, cmd, timeout=300):
        """Lance FFmpeg via subprocess. Retourne (ok, log)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            log = (result.stdout or b"").decode("utf-8", errors="replace")[-2000:]
            log += "\n--STDERR--\n"
            log += (result.stderr or b"").decode("utf-8", errors="replace")[-4000:]
            ok = result.returncode == 0
            return ok, log
        except FileNotFoundError:
            return False, "ffmpeg introuvable (PATH). Installe ffmpeg sur l'hôte."
        except subprocess.TimeoutExpired:
            return False, "ffmpeg timeout"
        except Exception as exc:  # noqa: BLE001
            return False, f"ffmpeg erreur : {exc}"

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------
    @api.model
    def _run_pipeline(self, video):
        """Lance le pipeline complet sur un abrmd.grow.video.

        Met à jour video.state + video.output_file + video.error_message.
        """
        log_lines = []

        def _log(msg):
            log_lines.append(msg)
            _logger.info("[abrmd_grow_marketing.video.pipeline] %s", msg)

        try:
            _log(f"Start pipeline for video #{video.id} ({video.name})")
            ICP = self.env["ir.config_parameter"].sudo()
            if ICP.get_param("abrmd_grow_marketing.killed", default="False") == "True":
                raise RuntimeError("Kill switch actif — pipeline interrompu.")

            # 1. Voix off
            mp3_bytes = b""
            if video.voice_provider == "openai_tts" and video.script:
                mp3_bytes, ok, log = self._call_openai_tts(
                    video.script, voice=video.voice_id or "nova"
                )
                _log(f"TTS: ok={ok} log={log[:200]}")
                if ok and mp3_bytes:
                    video.write({
                        "voiceover_file": base64.b64encode(mp3_bytes),
                        "voiceover_filename": "voiceover.mp3",
                    })

            # 2. Transcription Whisper → SRT
            srt = ""
            if mp3_bytes:
                srt, ok, log = self._call_openai_whisper(mp3_bytes)
                _log(f"Whisper: ok={ok} log={log[:200]}")
            if not srt and video.script:
                # Fallback : SRT généré pure-python depuis le script
                srt = self.build_srt_from_text(
                    video.script, duration_s=video.max_duration_s or 30.0
                )
                _log("Whisper indispo — fallback SRT pure-python")
            if srt:
                video.write({"subtitles_srt": srt})

            # 3. FFmpeg assemble
            if not self.ffmpeg_available():
                raise RuntimeError(
                    "ffmpeg introuvable sur l'hôte. "
                    "Sur SaaS : utiliser l'agent local Mac (voir README)."
                )
            with tempfile.TemporaryDirectory() as tmpdir:
                image_paths = self._dump_media_images(video, tmpdir)
                if not image_paths:
                    # Pas de média : génère un fond noir
                    fallback = os.path.join(tmpdir, "fallback.jpg")
                    self._generate_fallback_image(fallback)
                    image_paths = [fallback]
                audio_path = ""
                if mp3_bytes:
                    audio_path = os.path.join(tmpdir, "voiceover.mp3")
                    with open(audio_path, "wb") as f:
                        f.write(mp3_bytes)
                srt_path = ""
                if srt and video.burn_subtitles:
                    srt_path = os.path.join(tmpdir, "subs.srt")
                    with open(srt_path, "w", encoding="utf-8") as f:
                        f.write(srt)
                output_path = os.path.join(tmpdir, "output.mp4")
                width, height = FORMAT_TO_DIMS.get(video.format or "9_16", (1080, 1920))
                cmd = self.build_ffmpeg_cmd(
                    image_paths=image_paths,
                    audio_path=audio_path,
                    srt_path=srt_path,
                    output_path=output_path,
                    width=width,
                    height=height,
                    max_duration=video.max_duration_s or 60,
                    burn_subtitles=bool(srt_path),
                )
                _log(f"FFmpeg cmd: {' '.join(cmd[:8])}…")
                ok, log = self._call_ffmpeg(cmd)
                _log(f"FFmpeg: ok={ok}")
                if not ok or not os.path.exists(output_path):
                    raise RuntimeError(f"FFmpeg failed: {log[:500]}")
                with open(output_path, "rb") as f:
                    mp4_data = f.read()

            video.write({
                "output_file": base64.b64encode(mp4_data),
                "output_filename": f"{video.name[:60]}.mp4",
                "state": "ready",
                "finished_at": fields.Datetime.now(),
                "pipeline_log": "\n".join(log_lines)[-8000:],
            })
            _log("Pipeline done OK.")
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "[abrmd_grow_marketing] pipeline vidéo échec sur #%s : %s",
                video.id, exc,
            )
            video.write({
                "state": "failed",
                "error_message": str(exc),
                "finished_at": fields.Datetime.now(),
                "pipeline_log": "\n".join(log_lines)[-8000:],
            })

    @staticmethod
    def _generate_fallback_image(path):
        """Image noire 1080x1920 minimaliste, sans dépendance Pillow."""
        # Bitmap BMP minimal noir 1x1 (FFmpeg scale fera le reste)
        # On préfère écrire un fichier vide → FFmpeg refuse ; donc PNG 1x1.
        # PNG 1x1 noir hex pre-encodé :
        png_1x1_black = bytes.fromhex(
            "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
            "0000000D4944415478DA63600000000000050001A5F645400000000049454E44AE426082"
        )
        with open(path, "wb") as f:
            f.write(png_1x1_black)

    @staticmethod
    def _dump_media_images(video, tmpdir):
        """Dump les médias rattachés en fichiers temporaires.

        Ne garde que les images (la vidéo from text n'est pas en V0.2).
        """
        paths = []
        for i, media in enumerate(video.media_ids):
            if not media.file:
                continue
            mt = media.mimetype or ""
            if not mt.startswith("image/"):
                continue
            ext = ".jpg"
            if mt == "image/png":
                ext = ".png"
            elif mt == "image/webp":
                ext = ".webp"
            fpath = os.path.join(tmpdir, f"media_{i}{ext}")
            try:
                with open(fpath, "wb") as f:
                    f.write(base64.b64decode(media.file))
                paths.append(fpath)
            except Exception:
                continue
        return paths


def _fmt_srt_time(seconds):
    """Format SRT (HH:MM:SS,mmm)."""
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
