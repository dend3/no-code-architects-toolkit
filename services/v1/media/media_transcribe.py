import os
import warnings
from faster_whisper import WhisperModel
import srt
from datetime import timedelta
from services.file_management import download_file
import logging

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Set the default local storage directory
STORAGE_PATH = "/tmp/"

# Filter out warnings
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

def process_transcribe_media(media_url, task, include_text, include_srt, include_segments, word_timestamps, response_type, language, job_id):
    """Transcribe or translate media using faster-whisper."""
    logger.info(f"Starting {task} for media URL: {media_url}")
    input_filename = download_file(media_url, os.path.join(STORAGE_PATH, 'input_media'))
    logger.info(f"Downloaded media to local file: {input_filename}")

    try:
        # Load model with optimized settings for Neoverse-N1
        model_size = "base"
        # Use 2 threads (leaving 1 core free), compute_type=int8 for better performance
        model = WhisperModel(model_size, device="cpu", compute_type="int8", num_workers=2)
        logger.info(f"Loaded faster-whisper {model_size} model")

        # Configure transcription options
        beam_size = 3  # Reduced beam size for faster processing
        language = language if language else None
        
        # Transcribe with optimized settings
        segments, info = model.transcribe(
            input_filename,
            beam_size=beam_size,
            language=language,
            word_timestamps=word_timestamps,
            condition_on_previous_text=False,  # Disable for faster processing
            vad_filter=True  # Enable voice activity detection for better accuracy
        )
        
        logger.info(f"Generated {task} output with language: {info.language}")

        # Process results
        text = None
        srt_text = None
        segments_json = []

        # Convert segments to list for processing
        segments_list = list(segments)

        if include_text:
            text = " ".join([seg.text for seg in segments_list])

        if include_srt:
            # Create SRT subtitles
            subtitles = []
            for i, segment in enumerate(segments_list, start=1):
                start = timedelta(seconds=segment.start)
                end = timedelta(seconds=segment.end)
                subtitle = srt.Subtitle(
                    index=i,
                    start=start,
                    end=end,
                    content=segment.text.strip()
                )
                subtitles.append(subtitle)
            srt_text = srt.compose(subtitles)

        if include_segments:
            segments_json = [{
                'start': seg.start,
                'end': seg.end,
                'text': seg.text,
                'words': seg.words if word_timestamps else None
            } for seg in segments_list]

        # Clean up
        try:
            os.remove(input_filename)
            logger.info(f"Cleaned up temporary file: {input_filename}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file {input_filename}: {e}")

        if response_type == "direct":
            return text, srt_text, segments_json
        else:
            if include_text:
                text_filename = os.path.join(STORAGE_PATH, f"{job_id}.txt")
                with open(text_filename, 'w') as f:
                    f.write(text)
            else:
                text_filename = None
            
            if include_srt:
                srt_filename = os.path.join(STORAGE_PATH, f"{job_id}.srt")
                with open(srt_filename, 'w') as f:
                    f.write(srt_text)
            else:
                srt_filename = None

            if include_segments:
                segments_filename = os.path.join(STORAGE_PATH, f"{job_id}.json")
                with open(segments_filename, 'w') as f:
                    f.write(str(segments_json))
            else:
                segments_filename = None

            return text_filename, srt_filename, segments_filename 

    except Exception as e:
        logger.error(f"{task.capitalize()} failed: {str(e)}")
        # Clean up in case of error
        try:
            os.remove(input_filename)
        except:
            pass
        raise